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


# --- Firma y formalización (RF4.3, RF4.4) --------------------------------------------------------

def firmar(p: Principal, mediacion_id: UUID, password: str, codigo_mfa: str | None) -> dict:
    from compartido.documentos import almacen, pdf as generar
    from compartido.firma import proveedor
    from modulos.identidad.autorizacion import Rol
    from modulos.identidad.servicio import confirmar_identidad

    confirmar_identidad(p.usuario_id, password, codigo_mfa, exigir_mfa=p.rol != Rol.CIUDADANO)
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        m = _mediacion(c, mediacion_id, bloquear=True)
        v = c.execute("SELECT * FROM schema_odr.convenio WHERE mediacion_id=%s FOR UPDATE", (mediacion_id,)).fetchone()
        if not v:
            raise NoEncontrado("Aún no hay convenio")
        if v["formalizado_en"]:
            raise ReglaNegocio("El convenio ya fue formalizado")
        partes = c.execute("SELECT usuario_id, nombre FROM nucleo_comun.parte WHERE conflicto_id=%s ORDER BY rol DESC",
                           (m["conflicto_id"],)).fetchall()
        if any(x["usuario_id"] is None for x in partes):
            raise ReglaNegocio("Ambas partes deben estar registradas para firmar")
        aprobados = {r["usuario_id"] for r in c.execute("SELECT usuario_id FROM schema_odr.aprobacion_convenio WHERE convenio_id=%s", (v["id"],))}
        if any(x["usuario_id"] not in aprobados for x in partes):
            raise ReglaNegocio("Ambas partes deben aprobar el texto antes de firmar")
        mediador = c.execute("SELECT * FROM schema_odr.mediador_publico(%s)", (mediacion_id,)).fetchone() if m["mediador_id"] else None
        firmantes = {x["usuario_id"]: x["nombre"] for x in partes}
        if m["mediador_id"]:
            firmantes[m["mediador_id"]] = mediador["nombre"]
        if p.usuario_id not in firmantes:
            raise ReglaNegocio("No eres firmante de este convenio")
        firmadas = {r["usuario_id"] for r in c.execute("SELECT usuario_id FROM schema_odr.firma_convenio WHERE convenio_id=%s", (v["id"],))}
        if p.usuario_id in firmadas:
            raise ReglaNegocio("Ya firmaste este convenio")

        if v["clave_borrador"]:
            documento = almacen.leer(v["clave_borrador"], trabajo=True)
        else:
            documento = generar.convenio(m["folio"], v["tipo"], [x["nombre"] for x in partes], mediador and mediador["nombre"],
                                         descifrar(v["terminos_acordados_cifrados"], f"convenio:{mediacion_id}"), v["puntos_pendientes"])
        r = proveedor().firmar_pdf(c, p.usuario_id, firmantes[p.usuario_id], documento, f"Firma_{len(firmadas) + 1}")
        clave = f"convenios/{v['id']}/firma-{len(firmadas) + 1}.pdf"
        almacen.guardar_trabajo(clave, r.pdf)
        c.execute("UPDATE schema_odr.convenio SET clave_borrador=%s WHERE id=%s", (clave, v["id"]))
        c.execute("INSERT INTO schema_odr.firma_convenio (convenio_id, usuario_id, num_serie, sello_tiempo) VALUES (%s,%s,%s,%s)",
                  (v["id"], p.usuario_id, r.num_serie, r.sello_tiempo))
        registrar(c, usuario_id=p.usuario_id, entidad="convenio", entidad_id=v["id"], accion="CONVENIO_FIRMADO")

        if set(firmantes) - firmadas - {p.usuario_id}:
            notificar(c, m["conflicto_id"], "CONVENIO_FIRMADO", "mediacion", mediacion_id, excluir=p.usuario_id)
            return {"formalizado": False, "faltan": len(set(firmantes) - firmadas) - 1}
        return _formalizar(c, p, m, v, r.pdf, r.sello_tiempo)


def _formalizar(c, p: Principal, m: dict, v: dict, pdf_final: bytes, sello) -> dict:
    from compartido.documentos import almacen

    huella = almacen.sha256(pdf_final)
    clave = f"convenios/{m['folio']}/{huella}.pdf"
    version = almacen.guardar_inmutable(clave, pdf_final)
    doc_id = uuid4()
    c.execute("INSERT INTO nucleo_comun.documento (id, dominio, conflicto_id, tipo, nombre, clave_objeto, version_objeto, hash_sha256, subido_por)"
              " VALUES (%s,'ODR',%s,'CONVENIO',%s,%s,%s,%s,%s)",
              (doc_id, m["conflicto_id"], f"Convenio {m['folio']}.pdf", clave, version, huella, p.usuario_id))
    series = ";".join(r["num_serie"] for r in c.execute(
        "SELECT num_serie FROM schema_odr.firma_convenio WHERE convenio_id=%s ORDER BY sello_tiempo", (v["id"],)))
    c.execute("UPDATE schema_odr.convenio SET formalizado_en=now(), documento_id=%s, hash_sha256=%s, num_serie_firma=%s,"
              " sello_tiempo=%s WHERE id=%s", (doc_id, huella, series, sello, v["id"]))
    resultado = "ACUERDO_TOTAL" if v["tipo"] == "TOTAL" else "ACUERDO_PARCIAL"
    c.execute("UPDATE schema_odr.mediacion SET estado='CONCLUIDA', resultado=%s, concluida_en=now() WHERE id=%s", (resultado, m["id"]))
    nuevo = "CONCLUIDO" if v["tipo"] == "TOTAL" else "EN_ESPERA_DECISION"
    c.execute("UPDATE nucleo_comun.conflicto SET estado=%s WHERE id=%s", (nuevo, m["conflicto_id"]))
    registrar(c, usuario_id=p.usuario_id, entidad="convenio", entidad_id=v["id"], accion="CONVENIO_FORMALIZADO",
              estado_anterior="EN_MEDIACION", estado_nuevo=nuevo)
    notificar(c, m["conflicto_id"], "CONVENIO_FORMALIZADO", "mediacion", m["id"])
    return {"formalizado": True, "hash_sha256": huella, "documento_id": str(doc_id)}


def estado_firmas(p: Principal, mediacion_id: UUID) -> list[dict]:
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        m = _mediacion(c, mediacion_id)
        v = c.execute("SELECT id FROM schema_odr.convenio WHERE mediacion_id=%s", (mediacion_id,)).fetchone()
        if not v:
            return []
        firmas = {r["usuario_id"]: r for r in c.execute("SELECT * FROM schema_odr.firma_convenio WHERE convenio_id=%s", (v["id"],))}
        filas = [(x["usuario_id"], x["nombre"]) for x in c.execute(
            "SELECT usuario_id, nombre FROM nucleo_comun.parte WHERE conflicto_id=%s ORDER BY rol DESC", (m["conflicto_id"],))]
        if m["mediador_id"]:
            filas.append((m["mediador_id"], c.execute("SELECT nombre FROM schema_odr.mediador_publico(%s)", (mediacion_id,)).fetchone()["nombre"]))
    return [{"nombre": n, "soy_yo": u == p.usuario_id, "firmo": u in firmas,
             "num_serie": firmas[u]["num_serie"] if u in firmas else None,
             "sello_tiempo": firmas[u]["sello_tiempo"] if u in firmas else None} for u, n in filas]
