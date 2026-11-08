"""Sesión: valida el JWT y carga los roles vigentes desde la BD en cada petición (nunca del token)."""
from typing import Annotated

from fastapi import Depends, Header

from compartido.bd import RolBD, transaccion
from compartido.config import config
from modulos.identidad.autorizacion import AccesoDenegado, Principal, Rol
from modulos.identidad.credenciales import TokenInvalido, leer_token

# Si una persona tiene varios roles, se usa el de mayor responsabilidad.
_PRIORIDAD = [Rol.ADMINISTRADOR, Rol.JUEZ, Rol.MEDIADOR, Rol.CIUDADANO]


def cargar_principal(token: str) -> Principal:
    usuario_id, mfa = leer_token(token, clave=config().jwt_clave)
    with transaccion(RolBD.AUTH, None) as c:
        fila = c.execute("SELECT activo FROM nucleo_comun.usuario WHERE id = %s", (usuario_id,)).fetchone()
        roles = {r["rol"] for r in c.execute(
            "SELECT rol FROM nucleo_comun.usuario_rol WHERE usuario_id = %s", (usuario_id,))}
    if not fila or not roles:
        raise TokenInvalido("Usuario inexistente")
    rol = next(r for r in _PRIORIDAD if r.value in roles)
    return Principal(usuario_id=usuario_id, rol=rol, activo=fila["activo"], mfa_verificado=mfa)


def principal_actual(authorization: Annotated[str | None, Header()] = None) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise TokenInvalido("Falta token")
    p = cargar_principal(authorization[7:])
    if not p.activo:
        raise AccesoDenegado("Usuario inactivo")
    if p.rol != Rol.CIUDADANO and not p.mfa_verificado:
        raise AccesoDenegado("MFA requerido para personal")
    return p


Sesion = Annotated[Principal, Depends(principal_actual)]


def exigir_rol(p: Principal, *roles: Rol) -> None:
    if p.rol not in roles:
        raise AccesoDenegado("Tu perfil no puede realizar esta acción")
