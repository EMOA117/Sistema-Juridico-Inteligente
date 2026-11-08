"""P2: partes primero, después el relato; la clasificación es una sugerencia que la persona confirma."""
from uuid import UUID, uuid4

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.errores import NoEncontrado, ReglaNegocio
from modulos.identidad.autorizacion import Principal, exigir_acceso
from modulos.orientacion import reglas

_CAMPOS = ("c.id, c.folio, c.estado, c.materia, c.mediable, c.complejidad, c.confianza_clasificacion,"
           " c.narrativa_inicial, c.creado_en, c.solicitante_id")


def clasificador(narrativa: str) -> dict:
    """Punto de extensión: la fase de IA lo reemplaza por el cliente de ia-service con respaldo en reglas."""
    return reglas.clasificar(narrativa)


def crear(p: Principal, solicitante: dict, contraparte: dict) -> dict:
    exigir_acceso(p, "capturar_conflicto", solicitante_id=p.usuario_id)
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        # Sin RETURNING: la política de lectura (es_parte) aún no ve la fila en la misma instrucción.
        nuevo_id = uuid4()
        c.execute("INSERT INTO nucleo_comun.conflicto (id, solicitante_id) VALUES (%s,%s)", (nuevo_id, p.usuario_id))
        conf = c.execute("SELECT id, folio FROM nucleo_comun.conflicto WHERE id=%s", (nuevo_id,)).fetchone()
        c.execute("INSERT INTO nucleo_comun.parte (conflicto_id, usuario_id, rol, nombre, correo, domicilio_notificaciones)"
                  " VALUES (%s,%s,'DEMANDANTE',%s,%s,%s)",
                  (conf["id"], p.usuario_id, solicitante["nombre"], solicitante.get("correo"), solicitante.get("domicilio")))
        c.execute("INSERT INTO nucleo_comun.parte (conflicto_id, rol, nombre, correo, domicilio_notificaciones)"
                  " VALUES (%s,'DEMANDADO',%s,%s,%s)",
                  (conf["id"], contraparte["nombre"], contraparte.get("correo"), contraparte.get("domicilio")))
        registrar(c, usuario_id=p.usuario_id, entidad="conflicto", entidad_id=conf["id"], accion="CAPTURA_PARTES",
                  estado_nuevo="CAPTURA")
    return {"id": str(conf["id"]), "folio": conf["folio"]}


def _obtener(c, conflicto_id: UUID) -> dict:
    fila = c.execute(f"SELECT {_CAMPOS} FROM nucleo_comun.conflicto c WHERE c.id = %s", (conflicto_id,)).fetchone()
    if not fila:  # RLS: tampoco existe para quien no es parte
        raise NoEncontrado("Conflicto no encontrado")
    return fila


def registrar_narrativa(p: Principal, conflicto_id: UUID, narrativa: str) -> dict:
    if len(narrativa.strip()) < 20:
        raise ReglaNegocio("Describe tu conflicto con un poco más de detalle")
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        conf = _obtener(c, conflicto_id)
        if conf["solicitante_id"] != p.usuario_id or conf["estado"] != "CAPTURA":
            raise ReglaNegocio("El relato solo se captura al iniciar el asunto")
        if c.execute("SELECT count(*) n FROM nucleo_comun.parte WHERE conflicto_id=%s", (conflicto_id,)).fetchone()["n"] != 2:
            raise ReglaNegocio("Primero registra los datos de ambas partes")
    resultado = clasificador(narrativa)  # fuera de la transacción: no retiene la BD mientras responde la IA
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        c.execute("UPDATE nucleo_comun.conflicto SET narrativa_inicial=%s, materia=%s, mediable=%s, complejidad=%s,"
                  " confianza_clasificacion=%s, interaccion_ia_id=%s WHERE id=%s",
                  (narrativa.strip(), resultado["materia"], resultado["mediable"], resultado["complejidad"],
                   resultado["confianza"], resultado.get("interaccion_ia_id"), conflicto_id))
        registrar(c, usuario_id=p.usuario_id, entidad="conflicto", entidad_id=conflicto_id, accion="CLASIFICACION_SUGERIDA")
    return resultado


def confirmar(p: Principal, conflicto_id: UUID, materia: str) -> dict:
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        conf = _obtener(c, conflicto_id)
        if conf["solicitante_id"] != p.usuario_id:
            raise ReglaNegocio("Solo quien inició el asunto puede confirmarlo")
        if conf["narrativa_inicial"] is None:
            raise ReglaNegocio("Falta el relato")
        if materia != conf["materia"]:
            registrar(c, usuario_id=p.usuario_id, entidad="conflicto", entidad_id=conflicto_id, accion="CLASIFICACION_CORREGIDA")
        c.execute("UPDATE nucleo_comun.conflicto SET materia=%s, estado='ORIENTADO' WHERE id=%s", (materia, conflicto_id))
        registrar(c, usuario_id=p.usuario_id, entidad="conflicto", entidad_id=conflicto_id, accion="ORIENTACION_CONFIRMADA",
                  estado_anterior="CAPTURA", estado_nuevo="ORIENTADO")
    return {"estado": "ORIENTADO"}


def mis_conflictos(p: Principal) -> list[dict]:
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        filas = c.execute(f"SELECT {_CAMPOS}, (SELECT nombre FROM nucleo_comun.parte x WHERE x.conflicto_id=c.id AND x.rol='DEMANDADO') contraparte,"
                          " (SELECT nombre FROM nucleo_comun.parte x WHERE x.conflicto_id=c.id AND x.rol='DEMANDANTE') solicitante,"
                          " (c.solicitante_id = nucleo_comun.actor_id()) AS soy_solicitante"
                          " FROM nucleo_comun.conflicto c ORDER BY c.creado_en DESC").fetchall()
    return [{**f, "id": str(f["id"]), "solicitante_id": str(f["solicitante_id"])} for f in filas]


def detalle(p: Principal, conflicto_id: UUID) -> dict:
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        conf = _obtener(c, conflicto_id)
        partes = c.execute("SELECT id, rol, nombre, correo, domicilio_notificaciones, usuario_id IS NOT NULL registrada"
                           " FROM nucleo_comun.parte WHERE conflicto_id=%s ORDER BY rol DESC", (conflicto_id,)).fetchall()
    return {**conf, "id": str(conf["id"]), "solicitante_id": str(conf["solicitante_id"]),
            "partes": [{**x, "id": str(x["id"])} for x in partes]}


def actualizar_parte(p: Principal, parte_id: UUID, domicilio: str | None, correo: str | None) -> None:
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        n = c.execute("UPDATE nucleo_comun.parte SET domicilio_notificaciones=coalesce(%s, domicilio_notificaciones),"
                      " correo=coalesce(%s, correo) WHERE id=%s", (domicilio, correo, parte_id)).rowcount
        if n == 0:
            raise NoEncontrado("Parte no encontrada")
