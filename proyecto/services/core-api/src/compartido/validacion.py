"""Tipos validados compartidos."""
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator


def _correo(valor: str) -> str:
    try:
        # test_environment admite dominios reservados (.test) que usa la demostración sintética.
        return validate_email(valor, check_deliverability=False, test_environment=True).normalized.lower()
    except EmailNotValidError as e:
        raise ValueError("Correo electrónico inválido") from e


Correo = Annotated[str, AfterValidator(_correo)]


_CURP_ALFABETO = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
_CURP_RE = r"^[A-Z][AEIOUX][A-Z]{2}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]$"


def digito_curp(curp17: str) -> int:
    suma = sum(_CURP_ALFABETO.index(c) * (18 - i) for i, c in enumerate(curp17))
    return (10 - suma % 10) % 10


def _curp(valor: str) -> str:
    import re
    v = valor.strip().upper()
    if not re.match(_CURP_RE, v) or int(v[17]) != digito_curp(v[:17]):
        raise ValueError("CURP inválida")
    return v


def _password(valor: str) -> str:
    if len(valor) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres")
    if valor.isalpha() or valor.isdigit():
        raise ValueError("Combina letras con números o símbolos")
    return valor


Curp = Annotated[str, AfterValidator(_curp)]
Contrasena = Annotated[str, AfterValidator(_password)]
