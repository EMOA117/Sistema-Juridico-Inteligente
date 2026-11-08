from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from compartido.seguridad.dependencias import Sesion
from compartido.validacion import Correo
from modulos.odr import invitaciones, servicio

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


class Invitacion(BaseModel):
    correo: Correo | None = None
    plazo_dias: int | None = Field(default=None, ge=3, le=30)


class RespuestaInvitacion(BaseModel):
    acepta: bool


publico = APIRouter(tags=["odr"])


@publico.post("/conflictos/{conflicto_id}/mediacion", status_code=201)
def invitar(conflicto_id: UUID, datos: Invitacion, p: Sesion):
    return invitaciones.invitar(p, conflicto_id, datos.correo, datos.plazo_dias)


@publico.get("/invitaciones/{token}")
def ver_invitacion(token: str):
    return invitaciones.ver(token)


@publico.post("/invitaciones/{token}/responder")
def responder_invitacion(token: str, datos: RespuestaInvitacion, p: Sesion):
    return invitaciones.responder(p, token, datos.acepta)
