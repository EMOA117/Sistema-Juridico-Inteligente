"""P10–P12 (RF6.5, RF6.6, RF9.1–RF9.5): emplazamiento, paso a trámite, resolución firmada, firmeza y cierre."""
from datetime import date
from uuid import UUID, uuid4

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.documentos import almacen, pdf as generar
from compartido.errores import NoEncontrado, ReglaNegocio
from compartido.firma import proveedor
from modulos.identidad.autorizacion import Principal, exigir_acceso
from modulos.identidad.servicio import confirmar_identidad
from modulos.notificaciones.servicio import notificar


def _expediente(c, p: Principal, expediente_id: UUID) -> dict:
    e = c.execute("SELECT e.*, d.conflicto_id, j.nombre AS juzgado,"
                  " (SELECT string_agg(x.nombre, ' vs. ' ORDER BY x.rol DESC) FROM nucleo_comun.parte x WHERE x.conflicto_id=d.conflicto_id) partes"
                  " FROM schema_judicial.expediente e JOIN schema_judicial.demanda d ON d.id=e.demanda_id"
                  " LEFT JOIN schema_judicial.juzgado j ON j.id=e.juzgado_id WHERE e.id=%s FOR UPDATE OF e", (expediente_id,)).fetchone()
    if not e:
        raise NoEncontrado("Expediente no encontrado")
    exigir_acceso(p, "resolver", juez_id=e["juez_id"])
    return e


def emplazar(p: Principal, expediente_id: UUID, fecha: date) -> dict:
    if fecha > date.today():
        raise ReglaNegocio("La fecha de emplazamiento no puede ser futura")
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        e = _expediente(c, p, expediente_id)
        if e["estado"] != "ADMITIDO":
            raise ReglaNegocio("Solo un expediente admitido registra emplazamiento")
        fila = c.execute("UPDATE schema_judicial.expediente SET fecha_emplazamiento_validado=%s WHERE id=%s"
                         " RETURNING fecha_limite_contestacion", (fecha, expediente_id)).fetchone()
        registrar(c, usuario_id=p.usuario_id, entidad="expediente", entidad_id=expediente_id, accion="EMPLAZAMIENTO_VALIDADO")
        notificar(c, e["conflicto_id"], "EMPLAZAMIENTO", "expediente", expediente_id, incluir_mediador=False)
    return {"fecha_limite_contestacion": fila["fecha_limite_contestacion"].isoformat()}


def pasar_a_tramite(p: Principal, expediente_id: UUID) -> None:
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        _expediente(c, p, expediente_id)
        # El trigger exige emplazamiento y contestación registrada o plazo de 15 días vencido.
        c.execute("UPDATE schema_judicial.expediente SET estado='EN_TRAMITE' WHERE id=%s", (expediente_id,))
        registrar(c, usuario_id=p.usuario_id, entidad="expediente", entidad_id=expediente_id, accion="EN_TRAMITE",
                  estado_anterior="ADMITIDO", estado_nuevo="EN_TRAMITE")


def emitir_resolucion(p: Principal, expediente_id: UUID, tipo: str, resultado: str, texto: str,
                      password: str, codigo_mfa: str | None) -> dict:
    """RF9.1–RF9.5: el juez redacta, firma con sello de tiempo y el documento se guarda inmutable."""
    confirmar_identidad(p.usuario_id, password, codigo_mfa, exigir_mfa=True)
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        e = _expediente(c, p, expediente_id)
        destinos = {"DESECHAMIENTO": ("EN_REVISION", "PREVENIDO"), "SENTENCIA": ("EN_TRAMITE",)}
        if e["estado"] not in destinos[tipo]:
            raise ReglaNegocio("El expediente no admite ese tipo de resolución en su estado actual")
        if c.execute("SELECT 1 FROM schema_judicial.resolucion WHERE expediente_id=%s", (expediente_id,)).fetchone():
            raise ReglaNegocio("El expediente ya tiene resolución")
        nombre_juez = _nombre_juez(p)
        documento = generar.resolucion(e["numero"], e["juzgado"] or "Juzgado", e["partes"], resultado, texto, nombre_juez)
        firma = proveedor().firmar_pdf(c, p.usuario_id, nombre_juez, documento, "Firma_juez")
        huella = almacen.sha256(firma.pdf)
        clave = f"expedientes/{e['numero'].replace('/', '-')}/resolucion-{huella}.pdf"
        version = almacen.guardar_inmutable(clave, firma.pdf)
        doc_id = uuid4()
        c.execute("INSERT INTO nucleo_comun.documento (id, dominio, conflicto_id, expediente_id, tipo, nombre, clave_objeto,"
                  " version_objeto, hash_sha256, subido_por) VALUES (%s,'JUDICIAL',%s,%s,'RESOLUCION',%s,%s,%s,%s,%s)",
                  (doc_id, e["conflicto_id"], expediente_id, f"Resolución EXP {e['numero']}.pdf", clave, version, huella, p.usuario_id))
        c.execute("INSERT INTO schema_judicial.resolucion (expediente_id, resultado, documento_id, hash_sha256, num_serie_firma,"
                  " firmada_en, sello_tiempo) VALUES (%s,%s,%s,%s,%s,now(),%s)",
                  (expediente_id, resultado, doc_id, huella, firma.num_serie, firma.sello_tiempo))
        nuevo = "DESECHADO" if tipo == "DESECHAMIENTO" else "RESUELTO"
        c.execute("UPDATE schema_judicial.expediente SET estado=%s WHERE id=%s", (nuevo, expediente_id))
        registrar(c, usuario_id=p.usuario_id, entidad="expediente", entidad_id=expediente_id, accion="RESOLUCION_FIRMADA",
                  estado_anterior=e["estado"], estado_nuevo=nuevo)
        notificar(c, e["conflicto_id"], "RESOLUCION_EMITIDA", "expediente", expediente_id, excluir=p.usuario_id, incluir_mediador=False)
    return {"estado": nuevo, "hash_sha256": huella, "documento_id": str(doc_id)}


def _nombre_juez(p: Principal) -> str:
    with transaccion(RolBD.AUTH, None) as c:
        return c.execute("SELECT nombre FROM nucleo_comun.usuario WHERE id=%s", (p.usuario_id,)).fetchone()["nombre"]


def registrar_firmeza(p: Principal, expediente_id: UUID, fecha: date) -> None:
    """RF6.5: solo con resolución firmada, resultado explícito, sello de tiempo y firmeza se cierra."""
    if fecha > date.today():
        raise ReglaNegocio("La fecha de firmeza no puede ser futura")
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        e = _expediente(c, p, expediente_id)
        if e["estado"] not in ("RESUELTO", "DESECHADO"):
            raise ReglaNegocio("Solo un expediente resuelto o desechado puede quedar firme")
        firmada = c.execute("SELECT firmada_en::date AS f FROM schema_judicial.resolucion WHERE expediente_id=%s",
                            (expediente_id,)).fetchone()["f"]
        if fecha < firmada:
            raise ReglaNegocio("La firmeza no puede ser anterior a la firma de la resolución")
        c.execute("UPDATE schema_judicial.resolucion SET fecha_firmeza=%s WHERE expediente_id=%s", (fecha, expediente_id))
        c.execute("UPDATE schema_judicial.expediente SET fecha_firmeza=%s, estado='CERRADO' WHERE id=%s", (fecha, expediente_id))
        registrar(c, usuario_id=p.usuario_id, entidad="expediente", entidad_id=expediente_id, accion="FIRMEZA_Y_CIERRE",
                  estado_anterior=e["estado"], estado_nuevo="CERRADO")
        c.execute("SELECT nucleo_comun.concluir_por_expediente(%s)", (expediente_id,))
