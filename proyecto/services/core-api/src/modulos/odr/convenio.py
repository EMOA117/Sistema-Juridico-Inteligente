"""RF4.1–RF4.2: borrador del convenio con los términos pactados y revisión de las partes antes de firmar."""
from uuid import UUID, uuid4

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.cifrado import cifrar, descifrar
from compartido.errores import NoEncontrado, ReglaNegocio
from modulos.identidad.autorizacion import Principal
from modulos.notificaciones.servicio import notificar
from modulos.odr.servicio import _mediacion

EDITABLE = ("EN_NEGOCIACION", "CON_MEDIADOR", "PENDIENTE_FORMALIZACION")


def obtener(p: Principal, mediacion_id: UUID) -> dict | None:
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        m = _mediacion(c, mediacion_id)
        v = c.execute("SELECT * FROM schema_odr.convenio WHERE mediacion_id=%s", (mediacion_id,)).fetchone()
        if not v:
            return None
        aprobaciones = {r["usuario_id"] for r in c.execute(
            "SELECT usuario_id FROM schema_odr.aprobacion_convenio WHERE convenio_id=%s", (v["id"],))}
        partes = c.execute("SELECT usuario_id, nombre, rol FROM nucleo_comun.parte WHERE conflicto_id=%s ORDER BY rol DESC",
                           (m["conflicto_id"],)).fetchall()
        mediador = c.execute("SELECT * FROM schema_odr.mediador_publico(%s)", (mediacion_id,)).fetchone()
    return {"id": str(v["id"]), "tipo": v["tipo"], "puntos_pendientes": v["puntos_pendientes"],
            "terminos": descifrar(v["terminos_acordados_cifrados"], f"convenio:{mediacion_id}"),
            "formalizado_en": v["formalizado_en"], "hash_sha256": v["hash_sha256"], "documento_id": v["documento_id"] and str(v["documento_id"]),
            "folio": m["folio"], "materia": m["materia"], "estado_mediacion": m["estado"], "mediador": mediador,
            "partes": [{"nombre": x["nombre"], "rol": x["rol"], "aprobo": x["usuario_id"] in aprobaciones,
                        "soy_yo": x["usuario_id"] == p.usuario_id} for x in partes],
            "aprobado_por_todas": all(x["usuario_id"] in aprobaciones for x in partes if x["usuario_id"])}


def redactar(p: Principal, mediacion_id: UUID, tipo: str, terminos: str, pendientes: list[str]) -> None:
    pendientes = [x.strip() for x in pendientes if x.strip()]
    if tipo == "PARCIAL" and not pendientes:
        raise ReglaNegocio("Un convenio parcial debe registrar los puntos que siguen pendientes")
    if tipo == "TOTAL" and pendientes:
        raise ReglaNegocio("Un convenio total no tiene puntos pendientes")
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        m = _mediacion(c, mediacion_id, bloquear=True)
        if m["estado"] not in EDITABLE:
            raise ReglaNegocio("La mediación ya no admite convenio")
        if m["mediador_id"] is not None and m["mediador_id"] != p.usuario_id:
            raise ReglaNegocio("Con mediador asignado, el convenio lo redacta el mediador")
        if m["mediador_id"] is None and not c.execute(
                "SELECT 1 FROM schema_odr.propuesta WHERE mediacion_id=%s AND estado='ACEPTADA'", (mediacion_id,)).fetchone():
            raise ReglaNegocio("Para redactar el convenio sin mediador debe existir una propuesta aceptada")
        v = c.execute("SELECT id FROM schema_odr.convenio WHERE mediacion_id=%s", (mediacion_id,)).fetchone()
        datos = (tipo, pendientes, cifrar(terminos, f"convenio:{mediacion_id}"), p.usuario_id)
        if v:
            c.execute("UPDATE schema_odr.convenio SET tipo=%s, puntos_pendientes=%s, terminos_acordados_cifrados=%s,"
                      " redactado_por=%s, actualizado_en=now() WHERE id=%s", (*datos, v["id"]))
            c.execute("DELETE FROM schema_odr.aprobacion_convenio WHERE convenio_id=%s", (v["id"],))
            vid = v["id"]
        else:
            vid = uuid4()
            c.execute("INSERT INTO schema_odr.convenio (id, mediacion_id, tipo, puntos_pendientes, terminos_acordados_cifrados, redactado_por)"
                      " VALUES (%s,%s,%s,%s,%s,%s)", (vid, mediacion_id, *datos))
        if m["estado"] != "PENDIENTE_FORMALIZACION":
            c.execute("UPDATE schema_odr.mediacion SET estado='PENDIENTE_FORMALIZACION' WHERE id=%s", (mediacion_id,))
        registrar(c, usuario_id=p.usuario_id, entidad="convenio", entidad_id=vid, accion="CONVENIO_REDACTADO",
                  estado_anterior=m["estado"], estado_nuevo="PENDIENTE_FORMALIZACION")
        notificar(c, m["conflicto_id"], "CONVENIO_LISTO", "mediacion", mediacion_id, excluir=p.usuario_id)


def aprobar(p: Principal, mediacion_id: UUID) -> None:
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        m = _mediacion(c, mediacion_id)
        if m["mediador_id"] == p.usuario_id:
            raise ReglaNegocio("La aprobación corresponde a las partes")
        v = c.execute("SELECT id, formalizado_en FROM schema_odr.convenio WHERE mediacion_id=%s", (mediacion_id,)).fetchone()
        if not v:
            raise NoEncontrado("Aún no hay convenio")
        if v["formalizado_en"]:
            raise ReglaNegocio("El convenio ya fue formalizado")
        c.execute("INSERT INTO schema_odr.aprobacion_convenio (convenio_id, usuario_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                  (v["id"], p.usuario_id))
        registrar(c, usuario_id=p.usuario_id, entidad="convenio", entidad_id=v["id"], accion="CONVENIO_APROBADO")
        notificar(c, m["conflicto_id"], "CONVENIO_APROBADO", "mediacion", mediacion_id, excluir=p.usuario_id)
