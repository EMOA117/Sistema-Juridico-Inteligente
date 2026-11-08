"""Configuración por variables de entorno (prefijo SJI_)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SJI_", env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore")

    pg_host: str = "localhost"
    pg_port: int = 5433
    pg_db: str = "sji"
    pg_password: str
    jwt_clave: str
    llave_cifrado: str
    duracion_sesion_min: int = 15
    origen_web: str = "http://localhost:5173"

    def dsn(self, login: str) -> str:
        return (f"host={self.pg_host} port={self.pg_port} dbname={self.pg_db} "
                f"user={login} password={self.pg_password} application_name=core-api-{login}")


@lru_cache
def config() -> Config:
    return Config()  # type: ignore[call-arg]
