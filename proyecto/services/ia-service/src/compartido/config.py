from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IA_", env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore")

    servicio_token: str
    ollama_url: str = "http://localhost:11434"
    modelo_chat: str = "qwen2.5:7b"
    modelo_embeddings: str = "bge-m3"
    mantener_cargado: str = "60m"            # evita recargar el modelo (la carga en frío tarda minutos)
    timeout_chat_s: float = 60.0
    contexto_tokens: int = 4096              # 8192 duplica la memoria (9 GB) y la latencia en equipos de 16 GB
    mongo_uri: str = "mongodb://localhost:27018/?directConnection=true"
    umbral_casos: float = 0.72               # similitud mínima para sugerir un acuerdo
    umbral_fragmentos: float = 0.55          # similitud mínima para usar un fragmento en RAG


@lru_cache
def config() -> Config:
    return Config()  # type: ignore[call-arg]
