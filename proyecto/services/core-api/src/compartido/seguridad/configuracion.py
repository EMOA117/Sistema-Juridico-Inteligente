"""Configuración explícita: no hay claves, contraseñas ni roles desde el cliente."""
import base64
import os
from contextlib import contextmanager
from dataclasses import dataclass

import psycopg
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from psycopg.rows import dict_row
from psycopg import sql


@dataclass(frozen=True)
class Configuracion:
    database_url: str
    jwt_secret: str
    encryption_key: str
    firma_demo: bool = False

    @classmethod
    def entorno(cls):
        return cls(os.environ['DATABASE_URL'], os.environ['JWT_SECRET'],
                   os.environ['ODR_ENCRYPTION_KEY'], os.getenv('ODR_FIRMA_DEMO') == 'true')

    def validar(self):
        if len(self.jwt_secret.encode()) < 32:
            raise ValueError('JWT_SECRET requiere al menos 32 bytes')
        if len(base64.urlsafe_b64decode(self.encryption_key)) != 32:
            raise ValueError('ODR_ENCRYPTION_KEY requiere 32 bytes en base64url')


ROLES = {'rol_auth', 'rol_app_nucleo', 'rol_app_odr', 'rol_app_judicial', 'rol_canalizador', 'rol_tarea_odr'}


@contextmanager
def transaccion(config, rol, actor=None):
    if rol not in ROLES:
        raise ValueError('Rol de conexión no permitido')
    # DSN por módulo opcional; en local se usa un login NOINHERIT miembro de los roles.
    dsn = os.getenv(f'DATABASE_URL_{rol.upper()}', config.database_url)
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(rol)))
        conn.execute("SET LOCAL TIME ZONE 'America/Mexico_City'")
        conn.execute("SELECT set_config('app.usuario_id', %s, true)", (str(actor or ''),))
        yield conn


class Cifrado:
    def __init__(self, clave):
        self.aes = AESGCM(base64.urlsafe_b64decode(clave))

    def cifrar(self, texto: str | bytes, contexto: str) -> bytes:
        nonce = os.urandom(12)
        datos = texto.encode() if isinstance(texto, str) else texto
        return nonce + self.aes.encrypt(nonce, datos, contexto.encode())

    def abrir(self, datos, contexto: str) -> bytes:
        datos = bytes(datos)
        return self.aes.decrypt(datos[:12], datos[12:], contexto.encode())
