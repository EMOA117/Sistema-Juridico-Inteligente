from uuid import UUID

from fastapi import APIRouter, Header
from pydantic import BaseModel, ConfigDict

from compartido.seguridad.dependencias import Sesion
from modulos.canalizacion import servicio

router = APIRouter(tags=["canalizacion"])


class SolicitudCanalizacion(BaseModel):
    # Rechaza campos extra (mensajes, notas, propuestas…): decisión 002.
    model_config = ConfigDict(extra="forbid")


@router.post("/conflictos/{conflicto_id}/canalizar", status_code=201)
def canalizar(conflicto_id: UUID, p: Sesion, _: SolicitudCanalizacion | None = None,
              clave: UUID | None = Header(default=None, alias="Idempotency-Key")):
    return servicio.canalizar(p, conflicto_id, clave)
