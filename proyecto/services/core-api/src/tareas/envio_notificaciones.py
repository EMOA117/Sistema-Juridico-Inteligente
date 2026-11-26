"""P13: despacho asíncrono de avisos por correo (RF10.4). Reintentos con retroceso e idempotencia por fila.

El correo nunca incluye contenido de mensajes, propuestas ni resoluciones (decisión 002): solo folio, tipo y enlace.
"""
import logging
import smtplib
from datetime import timedelta
from email.message import EmailMessage
from html import escape

from compartido.bd import RolBD, transaccion
from compartido.cifrado import descifrar
from compartido.config import config
from modulos.notificaciones.servicio import texto

log = logging.getLogger("tareas.notificaciones")
MAX_INTENTOS = 5


def _cuerpo(saludo: str, mensaje: str, folio: str | None, enlace: str) -> tuple[str, str]:
    plano = (f"{saludo}\n\n{mensaje}{f' ({folio})' if folio else ''}.\n\nEntra a la plataforma para consultarlo: {enlace}\n\n"
             "Por tu privacidad, este correo no incluye el contenido de mensajes, propuestas ni resoluciones.\n"
             "Nunca te pediremos tu contraseña por correo. Datos de demostración sintéticos.")
    html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;color:#1A2333">
<div style="background:#101C2E;color:#F3F1EC;padding:16px 24px;border-bottom:3px solid #C9922E;font-family:Georgia,serif;font-size:18px">Plataforma Jurídica Inteligente</div>
<div style="padding:24px;border:1px solid #DDD8CE;border-top:0">
{f'<p style="font-family:monospace;color:#1F6B5C;font-weight:bold">{escape(folio)}</p>' if folio else ''}
<h2 style="font-family:Georgia,serif;font-weight:500">{escape(saludo)}</h2>
<p>{escape(mensaje)}.</p>
<p><a href="{escape(enlace)}" style="display:inline-block;background:#101C2E;color:#fff;padding:12px 20px;border-radius:4px;text-decoration:none;font-weight:bold">Ir a la plataforma</a></p>
<p style="font-size:13px;color:#4A5568">Por tu privacidad, este correo no incluye el contenido de mensajes, propuestas ni resoluciones. Si no reconoces este asunto, ignora este correo. Nunca te pediremos tu contraseña por correo.</p>
</div></div>"""
    return plano, html


def despachar_lote(limite: int = 20) -> int:
    cfg = config()
    enviados = 0
    with transaccion(RolBD.TAREAS, None) as c:
        filas = c.execute(
            "SELECT n.id, n.tipo, n.folio, n.entidad_id, n.enlace, n.enlace_cifrado, n.intentos, coalesce(u.correo, n.correo) AS correo,"
            " u.nombre FROM nucleo_comun.notificacion n LEFT JOIN nucleo_comun.usuario u ON u.id = n.destinatario_id"
            " WHERE n.estado_envio = 'PENDIENTE' AND n.proximo_intento <= now()"
            " ORDER BY n.proximo_intento LIMIT %s FOR UPDATE OF n SKIP LOCKED", (limite,)).fetchall()
        for n in filas:
            if not n["correo"]:
                c.execute("UPDATE nucleo_comun.notificacion SET estado_envio='SIN_CORREO' WHERE id=%s", (n["id"],))
                continue
            ruta = descifrar(n["enlace_cifrado"], f"enlace:{n['entidad_id']}") if n["enlace_cifrado"] else (n["enlace"] or "/")
            saludo = f"Hola, {n['nombre'].split(' ')[0]}." if n["nombre"] else "Hola."
            plano, html = _cuerpo(saludo, texto(n["tipo"]), n["folio"], cfg.url_web.rstrip("/") + ruta)
            msg = EmailMessage()
            msg["From"], msg["To"] = cfg.remitente, n["correo"]
            msg["Subject"] = f"{texto(n['tipo'])}{f' · {n['folio']}' if n['folio'] else ''}"
            msg["Message-ID"] = f"<{n['id']}@plataforma-juridica.test>"  # idempotencia del lado del receptor
            msg.set_content(plano)
            msg.add_alternative(html, subtype="html")
            try:
                with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=10) as s:
                    s.send_message(msg)
                c.execute("UPDATE nucleo_comun.notificacion SET estado_envio='ENVIADA', enviado_en=now(), intentos=intentos+1,"
                          " ultimo_error=NULL WHERE id=%s", (n["id"],))
                enviados += 1
            except (OSError, smtplib.SMTPException) as e:
                intentos = n["intentos"] + 1
                c.execute("UPDATE nucleo_comun.notificacion SET intentos=%s, ultimo_error=%s, estado_envio=%s,"
                          " proximo_intento = now() + %s WHERE id=%s",
                          (intentos, type(e).__name__, "FALLIDA" if intentos >= MAX_INTENTOS else "PENDIENTE",
                           timedelta(minutes=2 ** intentos), n["id"]))
                log.warning("Fallo al enviar aviso %s (intento %s): %s", n["id"], intentos, type(e).__name__)
    return enviados

