"""AES-256-GCM para contenido confidencial ODR (mensajes, propuestas, notas). Formato: nonce(12) || texto."""
import base64
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from compartido.config import config


@lru_cache
def _aes() -> AESGCM:
    llave = base64.b64decode(config().llave_cifrado)
    if len(llave) != 32:
        raise ValueError("SJI_LLAVE_CIFRADO debe ser de 32 bytes en base64")
    return AESGCM(llave)


def cifrar(texto: str, contexto: str) -> bytes:
    nonce = os.urandom(12)
    return nonce + _aes().encrypt(nonce, texto.encode("utf-8"), contexto.encode())


def descifrar(dato: bytes, contexto: str) -> str:
    dato = bytes(dato)
    return _aes().decrypt(dato[:12], dato[12:], contexto.encode()).decode("utf-8")
