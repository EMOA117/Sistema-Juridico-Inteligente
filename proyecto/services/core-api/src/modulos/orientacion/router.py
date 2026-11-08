from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from compartido.validacion import Correo
from compartido.seguridad.dependencias import Sesion
from modulos.orientacion import servicio

router = APIRouter(prefix="/conflictos", tags=["orientacion"])


class DatosParte(BaseModel):
    nombre: str = Field(min_length=3, max_length=200)
    correo: Correo | None = None
    domicilio: str | None = Field(default=None, max_length=300)


class NuevoConflicto(BaseModel):
    solicitante: DatosParte
    contraparte: DatosParte


class Narrativa(BaseModel):
    narrativa: str = Field(min_length=20, max_length=2000)


class Confirmacion(BaseModel):
    materia: Literal["CIVIL", "FAMILIAR"]


class CambioParte(BaseModel):
    domicilio: str | None = Field(default=None, max_length=300)
    correo: Correo | None = None


@router.post("", status_code=201)
def crear(datos: NuevoConflicto, p: Sesion):
    return servicio.crear(p, datos.solicitante.model_dump(), datos.contraparte.model_dump())


@router.get("")
def listar(p: Sesion):
    return servicio.mis_conflictos(p)


@router.get("/{conflicto_id}")
def detalle(conflicto_id: UUID, p: Sesion):
    return servicio.detalle(p, conflicto_id)


@router.put("/{conflicto_id}/narrativa")
def narrativa(conflicto_id: UUID, datos: Narrativa, p: Sesion):
    return servicio.registrar_narrativa(p, conflicto_id, datos.narrativa)


@router.post("/{conflicto_id}/confirmar")
def confirmar(conflicto_id: UUID, datos: Confirmacion, p: Sesion):
    return servicio.confirmar(p, conflicto_id, datos.materia)


@router.patch("/partes/{parte_id}")
def parte(parte_id: UUID, datos: CambioParte, p: Sesion):
    servicio.actualizar_parte(p, parte_id, datos.domicilio, datos.correo)
    return {"ok": True}
