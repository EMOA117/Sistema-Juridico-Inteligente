"""Autorización de aplicación: rol y relación con el recurso."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Rol(StrEnum):
    CIUDADANO = "CIUDADANO"
    MEDIADOR = "MEDIADOR"
    JUEZ = "JUEZ"
    ADMINISTRADOR = "ADMINISTRADOR"


class AccesoDenegado(PermissionError):
    pass


@dataclass(frozen=True)
class Principal:
    usuario_id: UUID
    rol: Rol
    activo: bool = True
    mfa_verificado: bool = False


def exigir_acceso(principal: Principal, accion: str, *, solicitante_id: UUID | None = None,
                  contraparte_id: UUID | None = None, mediador_id: UUID | None = None,
                  juez_id: UUID | None = None) -> None:
    if not principal.activo:
        raise AccesoDenegado("Usuario inactivo")
    if principal.rol != Rol.CIUDADANO and not principal.mfa_verificado:
        raise AccesoDenegado("MFA requerido para personal")
    permitido = {
        "capturar_conflicto": principal.rol == Rol.CIUDADANO and principal.usuario_id == solicitante_id,
        "canalizar": principal.rol == Rol.CIUDADANO and principal.usuario_id == solicitante_id,
        "responder_invitacion": principal.rol == Rol.CIUDADANO and principal.usuario_id == contraparte_id,
        "mediar": principal.rol == Rol.MEDIADOR and principal.usuario_id == mediador_id,
        "ver_expediente": (principal.rol == Rol.JUEZ and principal.usuario_id == juez_id)
                         or (principal.rol == Rol.CIUDADANO and principal.usuario_id in (solicitante_id, contraparte_id)),
        "resolver": principal.rol == Rol.JUEZ and principal.usuario_id == juez_id,
        "confirmar_turno": principal.rol == Rol.ADMINISTRADOR,
    }.get(accion, False)
    if not permitido:
        raise AccesoDenegado("Acceso no autorizado al recurso")
