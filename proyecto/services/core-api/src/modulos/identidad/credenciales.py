"""Primitivas de identidad. Los roles vigentes se consultan en BD tras validar el JWT."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pwdlib import PasswordHash


_password_hash = PasswordHash.recommended()
_ISSUER = "sistema-juridico-core"
_AUDIENCE = "sistema-juridico-web"


class TokenInvalido(ValueError):
    pass


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres")
    return _password_hash.hash(password)


def verificar_password(password: str, hash_guardado: str) -> bool:
    return _password_hash.verify(password, hash_guardado)


def emitir_token(usuario_id: UUID, *, clave: str, mfa_verificado: bool,
                 duracion_minutos: int = 30) -> str:
    if len(clave.encode("utf-8")) < 32 or duracion_minutos <= 0:
        raise ValueError("Configuración de token inválida")
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id), "iss": _ISSUER, "aud": _AUDIENCE,
        "iat": ahora, "exp": ahora + timedelta(minutes=duracion_minutos),
        "mfa": mfa_verificado,
    }
    return jwt.encode(payload, clave, algorithm="HS256")


def leer_token(token: str, *, clave: str) -> tuple[UUID, bool]:
    try:
        payload = jwt.decode(token, clave, algorithms=["HS256"], issuer=_ISSUER,
                             audience=_AUDIENCE, options={"require": ["sub", "iat", "exp", "iss", "aud"]})
        return UUID(payload["sub"]), payload.get("mfa") is True
    except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
        raise TokenInvalido("Token inválido o expirado") from exc
