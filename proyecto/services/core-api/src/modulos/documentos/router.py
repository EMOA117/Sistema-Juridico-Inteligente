from datetime import date
from typing import Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from compartido.seguridad.dependencias import Sesion
from modulos.documentos import servicio
from modulos.judicial.resolucion import servicio as resolucion
from modulos.odr import convenio

router = APIRouter(tags=["firma"])


class Credenciales(BaseModel):
    contrasena: str
    codigo_mfa: str | None = Field(default=None, pattern=r"^\d{6}$")


class Resolucion(Credenciales):
    tipo: Literal["DESECHAMIENTO", "SENTENCIA"]
    resultado: str = Field(min_length=5, max_length=300)
    texto: str = Field(min_length=50, max_length=30000)


class Fecha(BaseModel):
    fecha: date


@router.get("/documentos/{documento_id}")
def descargar(documento_id: UUID, p: Sesion):
    nombre, datos = servicio.descargar(p, documento_id)
    return Response(datos, media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(nombre)}"})


@router.get("/verificar/{huella}")
def verificar(huella: str):
    return servicio.verificar(huella)


@router.get("/mediaciones/{mediacion_id}/convenio/firmas")
def firmas(mediacion_id: UUID, p: Sesion):
    return convenio.estado_firmas(p, mediacion_id)


@router.post("/mediaciones/{mediacion_id}/convenio/firmar")
def firmar_convenio(mediacion_id: UUID, datos: Credenciales, p: Sesion):
    return convenio.firmar(p, mediacion_id, datos.contrasena, datos.codigo_mfa)


@router.post("/expedientes/{expediente_id}/emplazamiento")
def emplazamiento(expediente_id: UUID, datos: Fecha, p: Sesion):
    return resolucion.emplazar(p, expediente_id, datos.fecha)


@router.post("/expedientes/{expediente_id}/tramite")
def tramite(expediente_id: UUID, p: Sesion):
    resolucion.pasar_a_tramite(p, expediente_id)
    return {"ok": True}


@router.post("/expedientes/{expediente_id}/resolucion", status_code=201)
def emitir(expediente_id: UUID, datos: Resolucion, p: Sesion):
    return resolucion.emitir_resolucion(p, expediente_id, datos.tipo, datos.resultado, datos.texto, datos.contrasena, datos.codigo_mfa)


@router.post("/expedientes/{expediente_id}/firmeza")
def firmeza(expediente_id: UUID, datos: Fecha, p: Sesion):
    resolucion.registrar_firmeza(p, expediente_id, datos.fecha)
    return {"ok": True}
