"""P7: demanda asistida. El borrador es editable y solo se presenta con confirmación expresa (RF5.3, RF5.4)."""
from uuid import UUID

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.errores import NoEncontrado, ReglaNegocio
from modulos.identidad.autorizacion import Principal
from modulos.judicial.demandas import plantillas


def generador_borrador(datos: dict) -> dict:
    """RF5.1: borrador con ia-service; si no responde, plantilla procesal. Siempre editable y con confirmación."""
    from modulos import ia_cliente
    r = ia_cliente.borrador_demanda(datos)
    if r and r.get("texto"):
        return {**r, "modelo": "qwen2.5:7b"}
    return {"texto": plantillas.redactar(datos), "origen": "PLANTILLA", "interaccion_ia_id": None}


def _demanda(c, demanda_id: UUID) -> dict:
    d = c.execute("SELECT d.*, c.folio, c.solicitante_id FROM schema_judicial.demanda d"
                  " JOIN nucleo_comun.conflicto c ON c.id = d.conflicto_id WHERE d.id=%s", (demanda_id,)).fetchone()
    if not d:
        raise NoEncontrado("Demanda no encontrada")
    return d


def _partes(c, d: dict) -> dict:
    filas = c.execute("SELECT id, rol, nombre, correo, domicilio_notificaciones FROM nucleo_comun.parte WHERE id IN (%s,%s)",
                      (d["demandante_id"], d["demandado_id"])).fetchall()
    return {f["rol"].lower(): {**f, "id": str(f["id"])} for f in filas}


def obtener(p: Principal, demanda_id: UUID) -> dict:
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        d = _demanda(c, demanda_id)
        partes = _partes(c, d)
        exp = c.execute("SELECT id, numero, estado FROM schema_judicial.expediente WHERE demanda_id=%s", (demanda_id,)).fetchone()
    return {"id": str(d["id"]), "folio": d["folio"], "estado": d["estado"], "origen": d["origen"], "materia": d["materia"],
            "narrativa_inicial": d["narrativa_inicial"], "puntos_pendientes": d["puntos_pendientes"] or [],
            "texto_final": d["texto_final"], "partes": partes, "soy_solicitante": d["solicitante_id"] == p.usuario_id,
            "expediente": exp and {**exp, "id": str(exp["id"])}}


def por_conflicto(p: Principal, conflicto_id: UUID) -> dict:
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        f = c.execute("SELECT id FROM schema_judicial.demanda WHERE conflicto_id=%s", (conflicto_id,)).fetchone()
    if not f:
        raise NoEncontrado("Este asunto no tiene demanda")
    return obtener(p, f["id"])


def borrador(p: Principal, demanda_id: UUID, pretension: str, tipo_juicio: str) -> dict:
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        d = _demanda(c, demanda_id)
        if d["solicitante_id"] != p.usuario_id or d["estado"] != "BORRADOR":
            raise ReglaNegocio("Solo el solicitante edita la demanda en borrador")
        partes = _partes(c, d)
    datos = {"materia": d["materia"], "origen": d["origen"], "narrativa": d["narrativa_inicial"],
             "puntos_pendientes": d["puntos_pendientes"] or [], "pretension": pretension, "tipo_juicio": tipo_juicio,
             "demandante": partes["demandante"], "demandado": partes["demandado"]}
    return generador_borrador(datos)


def guardar(p: Principal, demanda_id: UUID, texto: str) -> None:
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        d = _demanda(c, demanda_id)
        if d["estado"] != "BORRADOR":
            raise ReglaNegocio("La demanda ya fue presentada")
        c.execute("UPDATE schema_judicial.demanda SET texto_final=%s WHERE id=%s", (texto, demanda_id))


def confirmar(p: Principal, demanda_id: UUID, texto: str) -> dict:
    """RF5.4 + RF6.1: confirma y crea el expediente único EN_TURNO en la misma transacción."""
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        d = _demanda(c, demanda_id)
        if d["solicitante_id"] != p.usuario_id:
            raise ReglaNegocio("Solo el solicitante puede presentar la demanda")
        if d["estado"] != "BORRADOR":
            raise ReglaNegocio("La demanda ya fue presentada")
        partes = _partes(c, d)
        faltan = [r for r, x in partes.items() if not x["domicilio_notificaciones"] and not x["correo"]]
        if faltan:
            raise ReglaNegocio("Faltan datos de contacto del " + " y ".join(faltan))
        if len(texto.strip()) < 100:
            raise ReglaNegocio("El texto de la demanda está incompleto")
        c.execute("UPDATE schema_judicial.demanda SET texto_final=%s, estado='CONFIRMADA' WHERE id=%s", (texto, demanda_id))
        exp = c.execute("INSERT INTO schema_judicial.expediente (demanda_id) VALUES (%s) RETURNING id, numero",
                        (demanda_id,)).fetchone()
        registrar(c, usuario_id=p.usuario_id, entidad="demanda", entidad_id=demanda_id, accion="DEMANDA_CONFIRMADA",
                  estado_anterior="BORRADOR", estado_nuevo="CONFIRMADA")
        registrar(c, usuario_id=p.usuario_id, entidad="expediente", entidad_id=exp["id"], accion="EXPEDIENTE_CREADO",
                  estado_nuevo="EN_TURNO")
        despues_de_expediente(c, exp["id"], p.usuario_id)
    return {"expediente_id": str(exp["id"]), "numero": exp["numero"]}


def despues_de_expediente(c, expediente_id: UUID, actor: UUID) -> None:
    from modulos.documentos.indexacion import encolar_demanda
    from modulos.notificaciones.servicio import notificar
    encolar_demanda(c, expediente_id)
    conf = c.execute("SELECT d.conflicto_id FROM schema_judicial.expediente e JOIN schema_judicial.demanda d ON d.id=e.demanda_id"
                     " WHERE e.id=%s", (expediente_id,)).fetchone()
    notificar(c, conf["conflicto_id"], "EXPEDIENTE_CREADO", "expediente", expediente_id, incluir_mediador=False)
