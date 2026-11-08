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
