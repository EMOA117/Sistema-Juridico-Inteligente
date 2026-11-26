"""Siembra la demostración si la base está vacía o le faltan datos (idempotente):

    uv run --project .. python -m herramientas.semilla

Crea la PKI local, las cuentas de prueba (herramientas.sembrar) y los expedientes y asuntos de demostración
(herramientas.poblar_demo). core-api lo lanza al arrancar cuando SJI_SEMBRAR_DEMO=true, e init-db.sh al final.
"""
import sys

from compartido.bd import cerrar_pools
from compartido.firma.pki_local import inicializar as pki
from herramientas import poblar_demo, sembrar

CANDADO = 734_0021   # pg_advisory_lock: evita dos siembras simultáneas (p. ej. init-db.sh y core-api)


def _falta(c) -> str | None:
    if not c.execute("SELECT 1 FROM nucleo_comun.usuario WHERE correo='admin@demo.test'").fetchone():
        return "cuentas"
    ultimo_caso = poblar_demo.CASOS[-1]["actor"]
    if not c.execute("SELECT 1 FROM nucleo_comun.parte WHERE nombre=%s AND rol='DEMANDANTE'", (ultimo_caso,)).fetchone():
        return "expedientes"
    for e in poblar_demo.ESCENARIOS:
        if not c.execute("SELECT 1 FROM nucleo_comun.conflicto WHERE narrativa_inicial=%s", (e["narrativa"],)).fetchone():
            return "escenarios"
    return None


def asegurar() -> None:
    with sembrar.conectar() as conn:
        conn.autocommit = True
        c = conn.cursor()
        if not c.execute("SELECT pg_try_advisory_lock(%s) ok", (CANDADO,)).fetchone()["ok"]:
            print("Otra siembra está en curso; se omite.")
            return
        falta = _falta(c)
        if not falta:
            print("La base ya tiene los datos de demostración.")
            return
        if falta != "cuentas" and not poblar_demo.CREDENCIALES.exists():
            print(f"La base tiene cuentas demo pero no existe {poblar_demo.CREDENCIALES}; usa init-db.sh --reiniciar.")
            return
        print(f"Sembrando datos de demostración (faltan {falta})…")
        pki()
        if falta == "cuentas":
            sembrar.main()
        try:
            poblar_demo.main()
        finally:
            cerrar_pools()


if __name__ == "__main__":
    sys.exit(asegurar())
