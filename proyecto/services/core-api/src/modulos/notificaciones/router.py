from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from compartido.seguridad.dependencias import Sesion
from modulos.notificaciones import servicio

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


class Lectura(BaseModel):
    ids: list[UUID] | None = None


@router.get("")
def bandeja(p: Sesion):
    return servicio.bandeja(p)


@router.post("/leidas")
def leidas(datos: Lectura, p: Sesion):
    servicio.marcar_leidas(p, datos.ids)
    return {"ok": True}
