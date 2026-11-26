from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from compartido.seguridad.dependencias import Sesion
from modulos.judicial.demandas import servicio as demandas
from modulos.judicial.expedientes import servicio as expedientes

router = APIRouter(tags=["judicial"])


class Borrador(BaseModel):
    pretension: str = Field(min_length=5, max_length=500)
    tipo_juicio: str = Field(min_length=3, max_length=80)


class TextoDemanda(BaseModel):
    texto: str = Field(min_length=1, max_length=40000)


class Dictamen(BaseModel):
    decision: Literal["ADMITIR", "PREVENIR"]
    texto: str | None = Field(default=None, max_length=4000)


@router.get("/demandas/{demanda_id}")
def demanda(demanda_id: UUID, p: Sesion):
    return demandas.obtener(p, demanda_id)


@router.get("/conflictos/{conflicto_id}/demanda")
def demanda_de_conflicto(conflicto_id: UUID, p: Sesion):
    return demandas.por_conflicto(p, conflicto_id)


@router.post("/demandas/{demanda_id}/borrador")
def borrador(demanda_id: UUID, datos: Borrador, p: Sesion):
    return demandas.borrador(p, demanda_id, datos.pretension, datos.tipo_juicio)


@router.put("/demandas/{demanda_id}")
def guardar(demanda_id: UUID, datos: TextoDemanda, p: Sesion):
    demandas.guardar(p, demanda_id, datos.texto)
    return {"ok": True}


@router.post("/demandas/{demanda_id}/confirmar", status_code=201)
def confirmar(demanda_id: UUID, datos: TextoDemanda, p: Sesion):
    return demandas.confirmar(p, demanda_id, datos.texto)


@router.get("/expedientes")
def bandeja(p: Sesion):
    return expedientes.bandeja(p)


@router.get("/expedientes/{expediente_id}")
def expediente(expediente_id: UUID, p: Sesion):
    return expedientes.detalle(p, expediente_id)


@router.post("/expedientes/{expediente_id}/dictamen")
def dictamen(expediente_id: UUID, datos: Dictamen, p: Sesion):
    return expedientes.dictaminar(p, expediente_id, datos.decision, datos.texto)


@router.post("/expedientes/{expediente_id}/correccion")
def correccion(expediente_id: UUID, datos: TextoDemanda, p: Sesion):
    expedientes.corregir(p, expediente_id, datos.texto)
    return {"ok": True}
