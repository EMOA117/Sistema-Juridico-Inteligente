"""P3: vence las invitaciones sin respuesta tras su fecha límite (la lógica vive en la función de BD)."""
from compartido.bd import RolBD, transaccion


def ejecutar() -> int:
    with transaccion(RolBD.TAREAS, None) as c:
        return c.execute("SELECT schema_odr.vencer_invitaciones() AS n").fetchone()["n"]
