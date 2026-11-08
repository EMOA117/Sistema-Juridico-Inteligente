"""P6: único puente ODR → judicial. Usa exclusivamente rol_canalizador y la función transaccional de la BD."""
import json
from pathlib import Path
from uuid import UUID

from compartido.bd import RolBD, transaccion
from modulos.identidad.autorizacion import Principal, exigir_acceso

_ESQUEMA = Path(__file__).resolve().parents[5] / "contracts" / "canalizacion" / "canalizacion.v1.schema.json"


def canalizar(p: Principal, conflicto_id: UUID) -> dict:
    exigir_acceso(p, "canalizar", solicitante_id=p.usuario_id)  # la función vuelve a verificar al solicitante real
    with transaccion(RolBD.CANALIZADOR, p.usuario_id) as c:
        demanda_id = c.execute("SELECT nucleo_comun.canalizar_conflicto(%s, %s) AS id",
                               (conflicto_id, p.usuario_id)).fetchone()["id"]
    return {"demanda_id": str(demanda_id)}


def esquema_contrato() -> dict:
    return json.loads(_ESQUEMA.read_text(encoding="utf-8"))
