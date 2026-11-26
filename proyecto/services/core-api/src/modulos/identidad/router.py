from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from compartido.seguridad.dependencias import Sesion, SesionSinMfa
from compartido.validacion import Contrasena, Correo, Curp
from modulos.identidad import cuentas, servicio

router = APIRouter(prefix="/auth", tags=["identidad"])
admin = APIRouter(prefix="/admin/usuarios", tags=["identidad"])


class Login(BaseModel):
    correo: Correo
    contrasena: str
    codigo_mfa: str | None = None


class Registro(BaseModel):
    nombre: str = Field(min_length=5, max_length=200)
    correo: Correo
    curp: Curp
    contrasena: Contrasena


class Codigo(BaseModel):
    codigo: str = Field(pattern=r"^\d{6}$")


class CambioPassword(BaseModel):
    actual: str
    nueva: Contrasena


class AltaPersonal(BaseModel):
    nombre: str = Field(min_length=5, max_length=200)
    correo: Correo
    rol: Literal["MEDIADOR", "JUEZ", "ADMINISTRADOR"]
    cargo: str | None = Field(default=None, max_length=200)


class EstadoPersonal(BaseModel):
    activo: bool


@router.post("/login")
def login(datos: Login):
    return servicio.iniciar_sesion(datos.correo, datos.contrasena, datos.codigo_mfa)


@router.post("/registro", status_code=201)
def registro(datos: Registro):
    return cuentas.registrar_ciudadano(datos.nombre, datos.correo, datos.curp, datos.contrasena)


@router.get("/yo")
def yo(_: SesionSinMfa, authorization: Annotated[str, Header()]):
    return servicio.perfil(authorization[7:])


@router.post("/renovar")
def renovar(p: SesionSinMfa):
    return cuentas.renovar(p)


@router.post("/mfa/alta")
def mfa_alta(p: SesionSinMfa):
    return cuentas.iniciar_alta_mfa(p)


@router.post("/mfa/confirmar")
def mfa_confirmar(datos: Codigo, p: SesionSinMfa):
    return cuentas.confirmar_alta_mfa(p, datos.codigo)


@router.post("/cambiar-contrasena")
def cambiar_contrasena(datos: CambioPassword, p: SesionSinMfa):
    cuentas.cambiar_password(p, datos.actual, datos.nueva)
    return {"ok": True}


@admin.get("")
def personal(p: Sesion):
    return cuentas.listar_personal(p)


@admin.post("", status_code=201)
def alta(datos: AltaPersonal, p: Sesion):
    return cuentas.alta_personal(p, datos.nombre, datos.correo, datos.rol, datos.cargo)


@admin.patch("/{usuario_id}")
def estado(usuario_id: UUID, datos: EstadoPersonal, p: Sesion):
    cuentas.cambiar_estado_personal(p, usuario_id, datos.activo)
    return {"ok": True}
