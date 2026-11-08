"""RF3.4–RF3.8: solicitud y asignación de mediador, agenda de sesiones, notas confidenciales y conclusión."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.cifrado import cifrar, descifrar
from compartido.errores import NoEncontrado, ReglaNegocio
from compartido.seguridad.dependencias import exigir_rol
from modulos.identidad.autorizacion import Principal, Rol, exigir_acceso
from modulos.notificaciones.servicio import notificar
from modulos.odr.servicio import _mediacion, concluir

MODALIDADES = {"VIDEOLLAMADA_CONJUNTA", "SESION_PRIVADA", "TELEFONICA"}


def solicitar(p: Principal, mediacion_id: UUID) -> dict:
    exigir_rol(p, Rol.CIUDADANO)
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        c.execute("SELECT schema_odr.asignar_mediador(%s)", (mediacion_id,))
        info = c.execute("SELECT * FROM schema_odr.mediador_publico(%s)", (mediacion_id,)).fetchone()
    return info


def _como_mediador(c, p: Principal, mediacion_id: UUID) -> dict:
    m = _mediacion(c, mediacion_id, bloquear=True)
    exigir_acceso(p, "mediar", mediador_id=m["mediador_id"])
    return m


def programar_sesion(p: Principal, mediacion_id: UUID, inicio: datetime, duracion: int, modalidad: str, enlace: str | None) -> dict:
    if modalidad not in MODALIDADES:
        raise ReglaNegocio("Modalidad no válida")
    if inicio <= datetime.now(timezone.utc):
        raise ReglaNegocio("La sesión debe programarse en el futuro")
    sid = uuid4()
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        m = _como_mediador(c, p, mediacion_id)
        if m["estado"] not in ("CON_MEDIADOR", "PENDIENTE_FORMALIZACION"):
            raise ReglaNegocio("La mediación no admite sesiones en su estado actual")
        c.execute("INSERT INTO schema_odr.sesion_mediacion (id, mediacion_id, mediador_id, inicio, duracion_min, modalidad, enlace)"
                  " VALUES (%s,%s,%s,%s,%s,%s,%s)", (sid, mediacion_id, p.usuario_id, inicio, duracion, modalidad, enlace))
        registrar(c, usuario_id=p.usuario_id, entidad="sesion_mediacion", entidad_id=sid, accion="SESION_PROGRAMADA")
        notificar(c, m["conflicto_id"], "SESION_PROGRAMADA", "mediacion", mediacion_id, excluir=p.usuario_id)
    return {"id": str(sid)}


def cambiar_sesion(p: Principal, sesion_id: UUID, estado: str) -> None:
    if estado not in ("CANCELADA", "REALIZADA"):
        raise ReglaNegocio("Estado de sesión no válido")
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        s = c.execute("SELECT * FROM schema_odr.sesion_mediacion WHERE id=%s AND mediador_id=%s FOR UPDATE",
                      (sesion_id, p.usuario_id)).fetchone()
        if not s:
            raise NoEncontrado("Sesión no encontrada")
        if s["estado"] != "PROGRAMADA":
            raise ReglaNegocio("La sesión ya fue cerrada")
        c.execute("UPDATE schema_odr.sesion_mediacion SET estado=%s WHERE id=%s", (estado, sesion_id))
        registrar(c, usuario_id=p.usuario_id, entidad="sesion_mediacion", entidad_id=sesion_id, accion=f"SESION_{estado}")
        if estado == "CANCELADA":
            m = _mediacion(c, s["mediacion_id"])
            notificar(c, m["conflicto_id"], "SESION_CANCELADA", "mediacion", m["id"], excluir=p.usuario_id)


def sesiones(p: Principal, mediacion_id: UUID) -> list[dict]:
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        _mediacion(c, mediacion_id)
        filas = c.execute("SELECT id, inicio, duracion_min, modalidad, enlace, estado FROM schema_odr.sesion_mediacion"
                          " WHERE mediacion_id=%s ORDER BY inicio", (mediacion_id,)).fetchall()
    return [{**f, "id": str(f["id"])} for f in filas]


def agenda(p: Principal) -> list[dict]:
    exigir_rol(p, Rol.MEDIADOR)
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        filas = c.execute("SELECT s.id, s.mediacion_id, s.inicio, s.duracion_min, s.modalidad, s.enlace, s.estado, c.folio"
                          " FROM schema_odr.sesion_mediacion s JOIN schema_odr.mediacion m ON m.id=s.mediacion_id"
                          " JOIN nucleo_comun.conflicto c ON c.id=m.conflicto_id"
                          " WHERE s.mediador_id = nucleo_comun.actor_id() AND s.estado='PROGRAMADA' AND s.inicio > now() - interval '1 day'"
                          " ORDER BY s.inicio").fetchall()
    return [{**f, "id": str(f["id"]), "mediacion_id": str(f["mediacion_id"])} for f in filas]


def notas(p: Principal, mediacion_id: UUID) -> list[dict]:
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        _como_mediador(c, p, mediacion_id)
        filas = c.execute("SELECT id, contenido_cifrado, creado_en FROM schema_odr.nota_mediador"
                          " WHERE mediacion_id=%s ORDER BY creado_en DESC", (mediacion_id,)).fetchall()
    return [{"id": str(f["id"]), "texto": descifrar(f["contenido_cifrado"], f"nota:{mediacion_id}"), "creado_en": f["creado_en"]}
            for f in filas]


def agregar_nota(p: Principal, mediacion_id: UUID, texto: str) -> None:
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        _como_mediador(c, p, mediacion_id)
        c.execute("INSERT INTO schema_odr.nota_mediador (mediacion_id, mediador_id, contenido_cifrado) VALUES (%s,%s,%s)",
                  (mediacion_id, p.usuario_id, cifrar(texto, f"nota:{mediacion_id}")))


def concluir_por_mediador(p: Principal, mediacion_id: UUID, resultado: str) -> None:
    """Sin acuerdo, desistimiento o invitación no aceptada se registran aquí; los acuerdos se cierran al firmar el convenio."""
    if resultado not in ("SIN_ACUERDO", "DESISTIMIENTO", "NO_ACEPTADA"):
        raise ReglaNegocio("Los acuerdos se concluyen al formalizar y firmar el convenio")
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        m = _como_mediador(c, p, mediacion_id)
        if m["estado"] == "CONCLUIDA":
            raise ReglaNegocio("La mediación ya concluyó")
        concluir(c, p.usuario_id, m, resultado)


# --- Administración del padrón (RF3.4) -----------------------------------------------------------

def padron(p: Principal) -> dict:
    exigir_rol(p, Rol.ADMINISTRADOR)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        registrados = c.execute("SELECT * FROM schema_odr.v_carga_mediadores ORDER BY nombre").fetchall()
        pendientes = c.execute("SELECT u.id, u.nombre, u.correo FROM nucleo_comun.usuario u"
                               " JOIN nucleo_comun.usuario_rol r ON r.usuario_id=u.id AND r.rol='MEDIADOR'"
                               " WHERE NOT EXISTS (SELECT 1 FROM schema_odr.mediador m WHERE m.usuario_id=u.id)").fetchall()
        asignaciones = c.execute("SELECT * FROM schema_odr.v_asignaciones ORDER BY solicitado_en DESC NULLS LAST").fetchall()
    return {"mediadores": [{**f, "usuario_id": str(f["usuario_id"])} for f in registrados],
            "sin_registro": [{**f, "id": str(f["id"])} for f in pendientes],
            "asignaciones": [{**f, "mediacion_id": str(f["mediacion_id"]), "mediador_id": f["mediador_id"] and str(f["mediador_id"])}
                             for f in asignaciones]}


def registrar_mediador(p: Principal, usuario_id: UUID, num_certificacion: str, especialidades: list[str],
                       max_casos: int, activo: bool) -> None:
    exigir_rol(p, Rol.ADMINISTRADOR)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        if not c.execute("SELECT 1 FROM nucleo_comun.usuario_rol WHERE usuario_id=%s AND rol='MEDIADOR'", (usuario_id,)).fetchone():
            raise ReglaNegocio("La persona no tiene perfil de mediador")
        c.execute("INSERT INTO schema_odr.mediador (usuario_id, num_certificacion, especialidades, max_casos, activo)"
                  " VALUES (%s,%s,%s,%s,%s) ON CONFLICT (usuario_id) DO UPDATE SET num_certificacion=EXCLUDED.num_certificacion,"
                  " especialidades=EXCLUDED.especialidades, max_casos=EXCLUDED.max_casos, activo=EXCLUDED.activo",
                  (usuario_id, num_certificacion, especialidades, max_casos, activo))
        registrar(c, usuario_id=p.usuario_id, entidad="mediador", entidad_id=usuario_id, accion="PADRON_MEDIADOR")


def reasignar(p: Principal, mediacion_id: UUID, mediador_id: UUID) -> None:
    exigir_rol(p, Rol.ADMINISTRADOR)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        c.execute("SELECT schema_odr.asignar_mediador(%s, %s)", (mediacion_id, mediador_id))
