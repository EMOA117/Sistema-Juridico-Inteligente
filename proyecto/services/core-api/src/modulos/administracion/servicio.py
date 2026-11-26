"""Portal administrativo: turno de expedientes (RF7.1), juzgados (RF7.7) e indicadores agregados (RF11)."""
from uuid import UUID

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.errores import NoEncontrado, ReglaNegocio
from compartido.seguridad.dependencias import exigir_rol
from modulos.identidad.autorizacion import Principal, Rol


def _admin(p: Principal) -> None:
    exigir_rol(p, Rol.ADMINISTRADOR)


def en_turno(p: Principal) -> list[dict]:
    _admin(p)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        filas = c.execute("SELECT e.id, e.numero, e.estado, e.creado_en, d.materia, d.origen"
                          " FROM schema_judicial.expediente e JOIN schema_judicial.demanda d ON d.id=e.demanda_id"
                          " WHERE e.estado='EN_TURNO' ORDER BY e.creado_en").fetchall()
    return [{**f, "id": str(f["id"])} for f in filas]


def carga(p: Principal) -> list[dict]:
    _admin(p)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        filas = c.execute("SELECT v.*, u.nombre FROM schema_judicial.v_carga_jueces v JOIN nucleo_comun.usuario u ON u.id=v.juez_id"
                          " ORDER BY v.especialidad, v.expedientes_activos").fetchall()
    return [{**f, "juez_id": str(f["juez_id"]), "juzgado_id": str(f["juzgado_id"])} for f in filas]


def asignar(p: Principal, expediente_id: UUID, juez_id: UUID) -> dict:
    """La asignación siempre la confirma una persona; la sugerencia de IA es solo apoyo (RF7.2)."""
    _admin(p)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        e = c.execute("SELECT e.id, e.estado, d.materia FROM schema_judicial.expediente e"
                      " JOIN schema_judicial.demanda d ON d.id=e.demanda_id WHERE e.id=%s FOR UPDATE OF e",
                      (expediente_id,)).fetchone()
        if not e:
            raise NoEncontrado("Expediente no encontrado")
        if e["estado"] != "EN_TURNO":
            raise ReglaNegocio("El expediente ya fue asignado")
        a = c.execute("SELECT juzgado_id, especialidad FROM schema_judicial.juez_adscripcion WHERE juez_id=%s",
                      (juez_id,)).fetchone()
        if not a:
            raise ReglaNegocio("La persona elegida no está adscrita a un juzgado")
        if a["especialidad"] != e["materia"]:
            raise ReglaNegocio("La especialidad del juez no corresponde a la materia")
        c.execute("UPDATE schema_judicial.expediente SET juez_id=%s, juzgado_id=%s, estado='EN_REVISION' WHERE id=%s",
                  (juez_id, a["juzgado_id"], expediente_id))
        registrar(c, usuario_id=p.usuario_id, entidad="expediente", entidad_id=expediente_id, accion="TURNO_CONFIRMADO",
                  estado_anterior="EN_TURNO", estado_nuevo="EN_REVISION")
        despues_de_asignar(c, expediente_id, p.usuario_id)
    return {"estado": "EN_REVISION"}


def despues_de_asignar(c, expediente_id: UUID, actor: UUID) -> None:
    from modulos.notificaciones.servicio import notificar_usuario
    e = c.execute("SELECT juez_id, numero FROM schema_judicial.expediente WHERE id=%s", (expediente_id,)).fetchone()
    # Administración no ve partes ni conflicto: avisa al juez; las partes reciben aviso por función definida.
    notificar_usuario(c, e["juez_id"], "EXPEDIENTE_TURNADO", f"EXP {e['numero']}", "expediente", expediente_id)
    c.execute("SELECT nucleo_comun.notificar(d.conflicto_id, 'EXPEDIENTE_ASIGNADO', 'expediente', %s, NULL, false)"
              " FROM schema_judicial.expediente x JOIN schema_judicial.demanda d ON d.id = x.demanda_id WHERE x.id = %s",
              (expediente_id, expediente_id))


def juzgados(p: Principal) -> list[dict]:
    _admin(p)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        filas = c.execute("SELECT j.*, (SELECT count(*) FROM schema_judicial.juez_adscripcion a WHERE a.juzgado_id=j.id) jueces"
                          " FROM schema_judicial.juzgado j ORDER BY j.nombre").fetchall()
    return [{**f, "id": str(f["id"])} for f in filas]


def crear_juzgado(p: Principal, nombre: str, materia: str) -> dict:
    _admin(p)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        j = c.execute("INSERT INTO schema_judicial.juzgado (nombre, materia) VALUES (%s,%s) RETURNING id", (nombre, materia)).fetchone()
        registrar(c, usuario_id=p.usuario_id, entidad="juzgado", entidad_id=j["id"], accion="JUZGADO_ALTA")
    return {"id": str(j["id"])}


def adscribir(p: Principal, juez_id: UUID, juzgado_id: UUID, especialidad: str) -> None:
    _admin(p)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        if not c.execute("SELECT 1 FROM nucleo_comun.usuario_rol WHERE usuario_id=%s AND rol='JUEZ'", (juez_id,)).fetchone():
            raise ReglaNegocio("La persona no tiene rol de juez")
        c.execute("INSERT INTO schema_judicial.juez_adscripcion (juez_id, juzgado_id, especialidad) VALUES (%s,%s,%s)"
                  " ON CONFLICT (juez_id) DO UPDATE SET juzgado_id=EXCLUDED.juzgado_id, especialidad=EXCLUDED.especialidad",
                  (juez_id, juzgado_id, especialidad))
        registrar(c, usuario_id=p.usuario_id, entidad="usuario", entidad_id=juez_id, accion="ADSCRIPCION")


def indicadores(p: Principal) -> dict:
    _admin(p)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        general = c.execute("SELECT * FROM analitica.v_indicadores").fetchone()
        materia = c.execute("SELECT * FROM analitica.v_conflictos_por_materia ORDER BY total DESC").fetchall()
        estados = c.execute("SELECT * FROM analitica.v_expedientes_por_estado ORDER BY total DESC").fetchall()
    concluidas = general["mediaciones_concluidas"] or 0
    return {**general, "tasa_acuerdo": round(100 * general["acuerdos"] / concluidas) if concluidas else None,
            "por_materia": materia, "expedientes_por_estado": estados}
