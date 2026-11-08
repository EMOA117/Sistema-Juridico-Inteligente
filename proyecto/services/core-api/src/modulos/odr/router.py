from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from compartido.seguridad.dependencias import Sesion
from modulos.odr import servicio

router = APIRouter(prefix="/mediaciones", tags=["odr"])


class Texto(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)


class Respuesta(BaseModel):
    estado: Literal["ACEPTADA", "RECHAZADA"]


class Terminar(BaseModel):
    resultado: Literal["SIN_ACUERDO", "DESISTIMIENTO"]


@router.get("")
def listar(p: Sesion):
    return servicio.listar(p)


@router.get("/{mediacion_id}")
def detalle(mediacion_id: UUID, p: Sesion):
    return servicio.detalle(p, mediacion_id)


@router.post("/{mediacion_id}/mensajes", status_code=201)
def mensaje(mediacion_id: UUID, datos: Texto, p: Sesion):
    servicio.enviar_mensaje(p, mediacion_id, datos.texto)
    return {"ok": True}


@router.post("/{mediacion_id}/propuestas", status_code=201)
def propuesta(mediacion_id: UUID, datos: Texto, p: Sesion):
    servicio.enviar_propuesta(p, mediacion_id, datos.texto)
    return {"ok": True}


@router.post("/propuestas/{propuesta_id}/responder")
def responder(propuesta_id: UUID, datos: Respuesta, p: Sesion):
    servicio.responder_propuesta(p, propuesta_id, datos.estado)
    return {"ok": True}


@router.post("/{mediacion_id}/terminar")
def terminar(mediacion_id: UUID, datos: Terminar, p: Sesion):
    servicio.terminar_por_parte(p, mediacion_id, datos.resultado)
    return {"ok": True}
