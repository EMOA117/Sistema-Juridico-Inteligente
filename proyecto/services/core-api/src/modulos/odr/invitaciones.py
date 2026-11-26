"""P3 / RF3.7: invitación a la contraparte con enlace de un solo uso y plazo configurable."""
import hashlib
import secrets
from datetime import date, timedelta
from uuid import UUID, uuid4

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.cifrado import cifrar
from compartido.config import config
from compartido.errores import NoEncontrado, ReglaNegocio
from modulos.identidad.autorizacion import Principal, exigir_acceso


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def invitar(p: Principal, conflicto_id: UUID, correo: str | None, plazo_dias: int | None) -> dict:
    exigir_acceso(p, "capturar_conflicto", solicitante_id=p.usuario_id)
    plazo = plazo_dias or config().plazo_invitacion_dias
    if not 3 <= plazo <= 30:
        raise ReglaNegocio("El plazo de respuesta debe estar entre 3 y 30 días")
    if correo:  # el solicitante puede corregir el correo de la contraparte antes de invitar
        with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
            c.execute("UPDATE nucleo_comun.parte SET correo=%s WHERE conflicto_id=%s AND rol='DEMANDADO'", (correo, conflicto_id))
    token = secrets.token_urlsafe(32)  # 43 caracteres
    mediacion_id, invitacion_id = uuid4(), uuid4()
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        conf = c.execute("SELECT id, folio, estado, mediable, solicitante_id FROM nucleo_comun.conflicto WHERE id=%s FOR UPDATE",
                         (conflicto_id,)).fetchone()
        if not conf:
            raise NoEncontrado("Conflicto no encontrado")
        if conf["solicitante_id"] != p.usuario_id:
            raise ReglaNegocio("Solo quien inició el asunto puede invitar")
        if conf["estado"] != "ORIENTADO" or not conf["mediable"]:
            raise ReglaNegocio("El asunto debe estar orientado y ser mediable para invitar")
        otra = c.execute("SELECT id, correo, nombre FROM nucleo_comun.parte WHERE conflicto_id=%s AND rol='DEMANDADO'",
                         (conflicto_id,)).fetchone()
        if not otra["correo"]:
            raise ReglaNegocio("Falta el correo de la otra parte")
        c.execute("INSERT INTO schema_odr.mediacion (id, conflicto_id) VALUES (%s,%s)", (mediacion_id, conflicto_id))
        c.execute("INSERT INTO schema_odr.invitacion (id, mediacion_id, contraparte_id, fecha_limite, token_hash, correo_destino)"
                  " VALUES (%s,%s,%s,%s,%s,%s)",
                  (invitacion_id, mediacion_id, otra["id"], date.today() + timedelta(days=plazo), hash_token(token), otra["correo"]))
        c.execute("UPDATE nucleo_comun.conflicto SET estado='EN_MEDIACION' WHERE id=%s", (conflicto_id,))
        c.execute("INSERT INTO nucleo_comun.notificacion (correo, tipo, folio, entidad, entidad_id, enlace_cifrado)"
                  " VALUES (%s,'INVITACION',%s,'invitacion',%s,%s)",
                  (otra["correo"], conf["folio"], invitacion_id, cifrar(f"/invitacion/{token}", f"enlace:{invitacion_id}")))
        registrar(c, usuario_id=p.usuario_id, entidad="invitacion", entidad_id=invitacion_id, accion="INVITACION_ENVIADA",
                  estado_anterior="ORIENTADO", estado_nuevo="EN_MEDIACION")
    return {"mediacion_id": str(mediacion_id), "fecha_limite": (date.today() + timedelta(days=plazo)).isoformat()}


def ver(token: str) -> dict:
    with transaccion(RolBD.AUTH, None) as c:
        f = c.execute("SELECT * FROM schema_odr.ver_invitacion(%s)", (hash_token(token),)).fetchone()
    if not f:
        raise NoEncontrado("La invitación no existe")
    return f


def responder(p: Principal, token: str, acepta: bool) -> dict:
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        mid = c.execute("SELECT schema_odr.responder_invitacion(%s, %s) AS id", (hash_token(token), acepta)).fetchone()["id"]
    return {"mediacion_id": str(mid)}
