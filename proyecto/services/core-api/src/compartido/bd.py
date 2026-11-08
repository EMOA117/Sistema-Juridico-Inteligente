"""Un pool de conexiones por rol de base de datos. Cada módulo usa solo el suyo (documento §11.1.1)."""
from contextlib import contextmanager
from enum import StrEnum
from typing import Iterator
from uuid import UUID

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from compartido.config import config
from compartido.seguridad.contexto_bd import transaccion_usuario


class RolBD(StrEnum):
    NUCLEO = "app_nucleo"
    AUTH = "app_auth"
    ODR = "app_odr"
    JUDICIAL = "app_judicial"
    ADMIN = "app_admin"
    CANALIZADOR = "app_canalizador"
    TAREAS = "app_tareas"


_pools: dict[RolBD, ConnectionPool] = {}


def _pool(rol: RolBD) -> ConnectionPool:
    if rol not in _pools:
        _pools[rol] = ConnectionPool(config().dsn(rol.value), min_size=1, max_size=8, open=True,
                                     kwargs={"row_factory": dict_row, "autocommit": True})
    return _pools[rol]


@contextmanager
def transaccion(rol: RolBD, usuario_id: UUID | None) -> Iterator[Connection]:
    """Abre una transacción con el rol indicado; fija app.usuario_id (SET LOCAL) si hay actor."""
    with _pool(rol).connection() as conn:
        if usuario_id is None:
            with conn.transaction():
                yield conn
        else:
            with transaccion_usuario(conn, usuario_id) as c:
                yield c


def cerrar_pools() -> None:
    for p in _pools.values():
        p.close()
    _pools.clear()
