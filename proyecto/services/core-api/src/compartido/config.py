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
    url_web: str = "http://localhost:5173"          # base de los enlaces en correos
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    remitente: str = "Plataforma Jurídica Inteligente <avisos@plataforma-juridica.test>"
    plazo_invitacion_dias: int = 10
    intervalo_tareas_s: int = 15

    def dsn(self, login: str) -> str:
        return (f"host={self.pg_host} port={self.pg_port} dbname={self.pg_db} "
                f"user={login} password={self.pg_password} application_name=core-api-{login}")


@lru_cache
def config() -> Config:
    return Config()  # type: ignore[call-arg]
