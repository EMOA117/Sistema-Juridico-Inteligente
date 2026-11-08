"""ia-service solo atiende a core-api (red interna): secreto de servicio comparado en tiempo constante."""
import hmac
from typing import Annotated

from fastapi import Header, HTTPException

from compartido.config import config


def exigir_servicio(x_servicio_token: Annotated[str | None, Header()] = None) -> None:
    if not x_servicio_token or not hmac.compare_digest(x_servicio_token, config().servicio_token):
        raise HTTPException(status_code=401, detail="Servicio no autorizado")
