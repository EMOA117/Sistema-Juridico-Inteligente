"""Consume la cola nucleo_comun.evento_pendiente (solo identificadores) y genera los avisos correspondientes."""
from compartido.bd import RolBD, transaccion


def procesar() -> int:
    with transaccion(RolBD.TAREAS, None) as c:
        return c.execute("SELECT nucleo_comun.procesar_eventos_pendientes() AS n").fetchone()["n"]
