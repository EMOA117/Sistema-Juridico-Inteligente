"""Bitácora de solo adición (RF1.4). Nunca guarda contenido: solo entidad, acción y estados."""
from uuid import UUID, uuid4

from psycopg import Connection


def registrar(conn: Connection, *, usuario_id: UUID | None, entidad: str, entidad_id: UUID, accion: str,
              estado_anterior: str | None = None, estado_nuevo: str | None = None,
              operacion_id: UUID | None = None) -> None:
    conn.execute(
        "INSERT INTO nucleo_comun.bitacora (usuario_id, entidad, entidad_id, accion, estado_anterior, estado_nuevo, operacion_id)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (usuario_id, entidad, entidad_id, accion, estado_anterior, estado_nuevo, operacion_id or uuid4()),
    )
