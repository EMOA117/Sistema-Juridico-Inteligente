"""Una transacción por operación; GUC local tras autenticar al usuario."""

from contextlib import contextmanager
from typing import Iterator, Protocol
from uuid import UUID


class Conexion(Protocol):
    def transaction(self): ...
    def execute(self, sql: str, params: tuple[str, ...]): ...


@contextmanager
def transaccion_usuario(conexion: Conexion, usuario_id: UUID) -> Iterator[Conexion]:
    with conexion.transaction():
        conexion.execute("SELECT set_config('app.usuario_id', %s, true)", (str(usuario_id),))
        yield conexion
