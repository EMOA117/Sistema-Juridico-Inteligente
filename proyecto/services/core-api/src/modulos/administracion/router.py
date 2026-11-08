from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from compartido.seguridad.dependencias import Sesion
from modulos.administracion import servicio

router = APIRouter(prefix="/admin", tags=["administracion"])


class Asignacion(BaseModel):
    juez_id: UUID


class Juzgado(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    materia: Literal["CIVIL", "FAMILIAR"]


class Adscripcion(BaseModel):
    juez_id: UUID
    juzgado_id: UUID
    especialidad: Literal["CIVIL", "FAMILIAR"]


@router.get("/turno")
def turno(p: Sesion):
    return servicio.en_turno(p)


@router.get("/carga-jueces")
def carga(p: Sesion):
    return servicio.carga(p)


@router.post("/expedientes/{expediente_id}/asignar")
def asignar(expediente_id: UUID, datos: Asignacion, p: Sesion):
    return servicio.asignar(p, expediente_id, datos.juez_id)


@router.get("/juzgados")
def juzgados(p: Sesion):
    return servicio.juzgados(p)


@router.post("/juzgados", status_code=201)
def crear_juzgado(datos: Juzgado, p: Sesion):
    return servicio.crear_juzgado(p, datos.nombre, datos.materia)


@router.post("/adscripciones")
def adscribir(datos: Adscripcion, p: Sesion):
    servicio.adscribir(p, datos.juez_id, datos.juzgado_id, datos.especialidad)
    return {"ok": True}


@router.get("/indicadores")
def indicadores(p: Sesion):
    return servicio.indicadores(p)
