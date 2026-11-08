from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from compartido.seguridad.dependencias import Sesion
from compartido.validacion import Correo
from datetime import datetime

from modulos.odr import convenio, invitaciones, mediadores, servicio

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


class NuevaSesion(BaseModel):
    inicio: datetime
    duracion_min: int = Field(default=60, ge=15, le=240)
    modalidad: Literal["VIDEOLLAMADA_CONJUNTA", "SESION_PRIVADA", "TELEFONICA"]
    enlace: str | None = Field(default=None, max_length=300)


class EstadoSesion(BaseModel):
    estado: Literal["CANCELADA", "REALIZADA"]


class Conclusion(BaseModel):
    resultado: Literal["SIN_ACUERDO", "DESISTIMIENTO", "NO_ACEPTADA"]


class Convenio(BaseModel):
    tipo: Literal["TOTAL", "PARCIAL"]
    terminos: str = Field(min_length=20, max_length=8000)
    puntos_pendientes: list[str] = Field(default_factory=list, max_length=20)


class Mediador(BaseModel):
    num_certificacion: str = Field(min_length=3, max_length=40)
    especialidades: list[Literal["CIVIL", "FAMILIAR"]] = Field(min_length=1)
    max_casos: int = Field(default=10, ge=1, le=50)
    activo: bool = True


class Reasignacion(BaseModel):
    mediador_id: UUID


@router.post("/{mediacion_id}/solicitar-mediador")
def solicitar_mediador(mediacion_id: UUID, p: Sesion):
    return mediadores.solicitar(p, mediacion_id)


@router.get("/{mediacion_id}/sesiones")
def sesiones(mediacion_id: UUID, p: Sesion):
    return mediadores.sesiones(p, mediacion_id)


@router.post("/{mediacion_id}/sesiones", status_code=201)
def programar(mediacion_id: UUID, datos: NuevaSesion, p: Sesion):
    return mediadores.programar_sesion(p, mediacion_id, datos.inicio, datos.duracion_min, datos.modalidad, datos.enlace)


@router.post("/sesiones/{sesion_id}/estado")
def estado_sesion(sesion_id: UUID, datos: EstadoSesion, p: Sesion):
    mediadores.cambiar_sesion(p, sesion_id, datos.estado)
    return {"ok": True}


@router.get("/{mediacion_id}/notas")
def notas(mediacion_id: UUID, p: Sesion):
    return mediadores.notas(p, mediacion_id)


@router.post("/{mediacion_id}/notas", status_code=201)
def nota(mediacion_id: UUID, datos: Texto, p: Sesion):
    mediadores.agregar_nota(p, mediacion_id, datos.texto)
    return {"ok": True}


@router.post("/{mediacion_id}/concluir")
def concluir(mediacion_id: UUID, datos: Conclusion, p: Sesion):
    mediadores.concluir_por_mediador(p, mediacion_id, datos.resultado)
    return {"ok": True}


@router.get("/{mediacion_id}/convenio")
def ver_convenio(mediacion_id: UUID, p: Sesion):
    return convenio.obtener(p, mediacion_id)


@router.put("/{mediacion_id}/convenio")
def redactar_convenio(mediacion_id: UUID, datos: Convenio, p: Sesion):
    convenio.redactar(p, mediacion_id, datos.tipo, datos.terminos, datos.puntos_pendientes)
    return {"ok": True}


@router.post("/{mediacion_id}/convenio/aprobar")
def aprobar_convenio(mediacion_id: UUID, p: Sesion):
    convenio.aprobar(p, mediacion_id)
    return {"ok": True}


@publico.get("/mediador/agenda")
def agenda(p: Sesion):
    return mediadores.agenda(p)


@publico.get("/admin/mediadores")
def padron(p: Sesion):
    return mediadores.padron(p)


@publico.put("/admin/mediadores/{usuario_id}")
def registrar_mediador(usuario_id: UUID, datos: Mediador, p: Sesion):
    mediadores.registrar_mediador(p, usuario_id, datos.num_certificacion, list(datos.especialidades), datos.max_casos, datos.activo)
    return {"ok": True}


@publico.post("/admin/asignaciones/{mediacion_id}")
def reasignar(mediacion_id: UUID, datos: Reasignacion, p: Sesion):
    mediadores.reasignar(p, mediacion_id, datos.mediador_id)
    return {"ok": True}
