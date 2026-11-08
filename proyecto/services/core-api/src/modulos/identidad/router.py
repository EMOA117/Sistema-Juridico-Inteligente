from typing import Annotated

from fastapi import APIRouter, Header
from pydantic import BaseModel

from compartido.validacion import Correo
from compartido.seguridad.dependencias import Sesion
from modulos.identidad import servicio

router = APIRouter(prefix="/auth", tags=["identidad"])


class Login(BaseModel):
    correo: Correo
    contrasena: str
    codigo_mfa: str | None = None


@router.post("/login")
def login(datos: Login):
    return servicio.iniciar_sesion(datos.correo, datos.contrasena, datos.codigo_mfa)


@router.get("/yo")
def yo(_: Sesion, authorization: Annotated[str, Header()]):
    return servicio.perfil(authorization[7:])
