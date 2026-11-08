from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
Correo = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=254,
                                        pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')]


class Contrato(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Registro(Contrato):
    nombre: Annotated[str, StringConstraints(min_length=2, max_length=150)]
    correo: Correo
    contrasena: str = Field(min_length=12, max_length=128)


class Login(Contrato):
    correo: Correo
    contrasena: str = Field(min_length=1, max_length=128)
    codigo_mfa: str | None = Field(default=None, max_length=6)


class Parte(Contrato):
    nombre: Annotated[str, StringConstraints(min_length=2, max_length=150)]
    correo: Correo
    domicilio_notificaciones: Annotated[str, StringConstraints(min_length=5, max_length=500)]


class Captura(Contrato):
    titulo: Annotated[str, StringConstraints(min_length=5, max_length=160)]
    demandante: Parte
    demandado: Parte


class Orientar(Contrato):
    narrativa: Annotated[str, StringConstraints(min_length=30, max_length=10000)]
    materia: Literal['CIVIL', 'FAMILIAR']
    mediable: bool
    confirmacion: Literal[True]


class Invitar(Contrato):
    plazo_dias: int = Field(default=7, ge=1, le=30)


class RespuestaInvitacion(Contrato):
    aceptar: bool


class Mensaje(Contrato):
    texto: Texto


class Propuesta(Mensaje):
    monto: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    responde_a_id: UUID | None = None


class RespuestaPropuesta(Contrato):
    estado: Literal['ACEPTADA', 'RECHAZADA']


class Sesion(Contrato):
    fecha_hora: datetime
    enlace: str = Field(pattern=r'^https://[^\s]+$', max_length=500)

    @field_validator('fecha_hora')
    @classmethod
    def zona_requerida(cls, valor):
        if valor.tzinfo is None:
            raise ValueError('Incluye zona horaria')
        return valor


class Convenio(Contrato):
    tipo: Literal['TOTAL', 'PARCIAL']
    terminos: Texto
    puntos_pendientes: list[Annotated[str, StringConstraints(min_length=1, max_length=1000)]] = Field(default_factory=list, max_length=30)
    pendientes_revisados: Literal[True]

    @model_validator(mode='after')
    def pendientes(self):
        if (self.tipo == 'PARCIAL') != bool(self.puntos_pendientes):
            raise ValueError('Solo un convenio parcial debe tener puntos pendientes')
        return self


class Firma(Contrato):
    hash_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    confirmacion: Literal[True]


class Conclusion(Contrato):
    resultado: Literal['SIN_ACUERDO', 'DESISTIMIENTO']
    confirmacion: Literal[True]


class Canalizar(Contrato):
    confirmacion: Literal[True]
