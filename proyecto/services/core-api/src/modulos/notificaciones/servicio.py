"""P13 / RF10: bandeja en plataforma. El envío por correo lo hace la tarea `tareas.envio_notificaciones`."""
from uuid import UUID

from psycopg import Connection

from compartido.bd import RolBD, transaccion
from modulos.identidad.autorizacion import Principal

TEXTOS = {
    "INVITACION": "Te invitaron a resolver un conflicto en línea",
    "INVITACION_ACEPTADA": "La otra parte aceptó la invitación: la negociación está abierta",
    "INVITACION_RECHAZADA": "La otra parte no aceptó la invitación",
    "INVITACION_VENCIDA": "La invitación venció sin respuesta",
    "MENSAJE_NUEVO": "Hay un mensaje nuevo en tu sala de negociación",
    "PROPUESTA_NUEVA": "Recibiste una propuesta formal",
    "PROPUESTA_ACEPTADA": "Aceptaron tu propuesta",
    "PROPUESTA_RECHAZADA": "Rechazaron tu propuesta",
    "MEDIACION_CONCLUIDA": "La mediación concluyó",
    "EXPEDIENTE_CREADO": "Tu demanda fue presentada y se creó el expediente",
    "EXPEDIENTE_ASIGNADO": "El expediente fue asignado a un juzgado",
    "EXPEDIENTE_TURNADO": "Se te asignó un expediente nuevo",
    "DICTAMEN_ADMITIDO": "La demanda fue admitida",
    "DICTAMEN_PREVENIDO": "El juzgado pidió corregir la demanda",
    "CORRECCION_PRESENTADA": "Se presentó la corrección de una demanda",
    "MEDIACION_ASIGNADA": "Se te asignó una mediación",
    "MEDIADOR_ASIGNADO": "Un mediador certificado se integró a tu mediación",
    "SESION_PROGRAMADA": "El mediador programó una sesión",
    "SESION_CANCELADA": "El mediador canceló una sesión",
    "CONVENIO_LISTO": "El convenio está listo para tu revisión",
    "CONVENIO_APROBADO": "La otra parte aprobó el convenio",
}


def texto(tipo: str) -> str:
    return TEXTOS.get(tipo, "Hay una actualización en tu asunto")


def notificar(c: Connection, conflicto_id: UUID, tipo: str, entidad: str, entidad_id: UUID,
              excluir: UUID | None = None, incluir_mediador: bool = True) -> None:
    c.execute("SELECT nucleo_comun.notificar(%s,%s,%s,%s,%s,%s)",
              (conflicto_id, tipo, entidad, entidad_id, excluir, incluir_mediador))


def notificar_usuario(c: Connection, usuario_id: UUID, tipo: str, folio: str | None, entidad: str, entidad_id: UUID) -> None:
    c.execute("SELECT nucleo_comun.notificar_usuario(%s,%s,%s,%s,%s)", (usuario_id, tipo, folio, entidad, entidad_id))


def bandeja(p: Principal) -> dict:
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        filas = c.execute("SELECT id, tipo, folio, entidad, entidad_id, creado_en, leida_en, estado_envio"
                          " FROM nucleo_comun.notificacion ORDER BY creado_en DESC LIMIT 50").fetchall()
    return {"sin_leer": sum(1 for f in filas if f["leida_en"] is None),
            "avisos": [{**f, "id": str(f["id"]), "entidad_id": str(f["entidad_id"]), "texto": texto(f["tipo"])} for f in filas]}


def marcar_leidas(p: Principal, ids: list[UUID] | None) -> None:
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        if ids:
            c.execute("UPDATE nucleo_comun.notificacion SET leida_en=now() WHERE leida_en IS NULL AND id = ANY(%s)", (ids,))
        else:
            c.execute("UPDATE nucleo_comun.notificacion SET leida_en=now() WHERE leida_en IS NULL")
