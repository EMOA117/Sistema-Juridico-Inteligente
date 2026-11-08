"""Bases de MongoDB del asistente (documento §11.3.7): conocimiento, uso judicial y uso ODR aislado."""
from datetime import datetime, timezone
from functools import lru_cache

from bson import ObjectId
from pymongo import MongoClient

from compartido.config import config


@lru_cache
def cliente() -> MongoClient:
    return MongoClient(config().mongo_uri, serverSelectionTimeoutMS=3000, tz_aware=True)


def conocimiento():
    return cliente()["ia_conocimiento"]


def registrar_interaccion(*, odr: bool, tipo: str, entrada: dict, salida: dict, fuentes: list | None = None,
                          latencia_ms: int, contexto: dict | None = None) -> str:
    """Traza de cada uso del asistente. Las sugerencias de mediación van SOLO a ia_uso_odr (decisión 002)."""
    base = cliente()["ia_uso_odr" if odr else "ia_uso"]
    doc = {"_id": ObjectId(), "tipo": tipo, "fecha": datetime.now(timezone.utc), "contexto": contexto or {},
           "entrada": entrada, "salida": salida, "fuentes": fuentes or [],
           "modelo": {"chat": config().modelo_chat, "embeddings": config().modelo_embeddings},
           "metricas": {"latencia_ms": latencia_ms}}
    base["interacciones_ia"].insert_one(doc)
    return str(doc["_id"])
