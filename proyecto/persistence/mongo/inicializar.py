"""Crea las bases de MongoDB del asistente (§11.3.7), sus validadores $jsonSchema, los índices vectoriales y el
corpus SINTÉTICO de demostración (decisión 003). Ejecutar desde services/ia-service:

    uv run python ../../persistence/mongo/inicializar.py [--reiniciar]
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "ia-service" / "src"))

from pymongo.errors import CollectionInvalid, OperationFailure  # noqa: E402
from pymongo.operations import SearchIndexModel  # noqa: E402

from compartido.mongo import cliente  # noqa: E402
from compartido.ollama import embeddings  # noqa: E402
from ingesta_conocimiento.servicio import ingerir  # noqa: E402

CORPUS = Path(__file__).parent / "corpus"
MATERIAS = {"enum": ["CIVIL", "FAMILIAR"]}
VECTOR = {"bsonType": "array", "minItems": 1024, "maxItems": 1024, "items": {"bsonType": "double"}}

ESQUEMAS = {
    ("ia_conocimiento", "casos_anonimizados"): {"bsonType": "object", "required": ["materia", "resumen", "formula_arreglo", "resultado", "embedding", "sintetico"],
        "properties": {"materia": MATERIAS, "resumen": {"bsonType": "string"}, "formula_arreglo": {"bsonType": "string"},
                       "resultado": {"bsonType": "string"}, "embedding": VECTOR, "sintetico": {"bsonType": "bool"}}},
    ("ia_conocimiento", "fuentes_juridicas"): {"bsonType": "object", "required": ["titulo", "materia", "texto", "sintetico"],
        "properties": {"titulo": {"bsonType": "string"}, "materia": MATERIAS, "texto": {"bsonType": "string"}, "sintetico": {"bsonType": "bool"}}},
    ("ia_conocimiento", "fragmentos"): {"bsonType": "object", "required": ["texto", "documento", "acceso", "materia", "origen", "embedding"],
        "properties": {"texto": {"bsonType": "string"}, "documento": {"bsonType": "string"}, "acceso": {"enum": ["PUBLICO", "EXPEDIENTE"]},
                       "materia": MATERIAS, "embedding": VECTOR,
                       "origen": {"bsonType": "object", "properties": {"expediente_id": {"bsonType": ["string", "null"]}}}}},
    ("ia_uso", "interacciones_ia"): {"bsonType": "object", "required": ["tipo", "fecha", "modelo", "metricas"],
        "properties": {"tipo": {"enum": ["CLASIFICACION", "GENERACION_DEMANDA", "SUGERENCIA_TURNO", "CONSULTA_RAG"]},
                       "fecha": {"bsonType": "date"}},
        "oneOf": [{"properties": {"tipo": {"enum": ["CONSULTA_RAG"]}, "contexto": {"bsonType": "object", "required": ["expediente_id"]}}},
                  {"properties": {"tipo": {"enum": ["CLASIFICACION", "GENERACION_DEMANDA", "SUGERENCIA_TURNO"]}}}]},
    ("ia_uso_odr", "interacciones_ia"): {"bsonType": "object", "required": ["tipo", "fecha", "modelo", "metricas"],
        "properties": {"tipo": {"enum": ["RECOMENDACION_ODR"]}, "fecha": {"bsonType": "date"}}},
}
INDICES = {
    "casos_anonimizados": ("vector_casos", ["materia"]),
    "fragmentos": ("vector_fragmentos", ["acceso", "materia", "origen.expediente_id"]),
}


def crear_colecciones() -> None:
    for (base, nombre), esquema in ESQUEMAS.items():
        db = cliente()[base]
        try:
            db.create_collection(nombre, validator={"$jsonSchema": esquema}, validationLevel="strict")
        except CollectionInvalid:
            db.command("collMod", nombre, validator={"$jsonSchema": esquema}, validationLevel="strict")
    for nombre, (indice, filtros) in INDICES.items():
        col = cliente()["ia_conocimiento"][nombre]
        if any(i["name"] == indice for i in col.list_search_indexes()):
            continue
        campos = [{"type": "vector", "path": "embedding", "numDimensions": 1024, "similarity": "cosine"}] + \
                 [{"type": "filter", "path": f} for f in filtros]
        col.create_search_index(SearchIndexModel(definition={"fields": campos}, name=indice, type="vectorSearch"))


def esperar_indices() -> None:
    for nombre, (indice, _) in INDICES.items():
        col = cliente()["ia_conocimiento"][nombre]
        for _ in range(120):
            info = next((i for i in col.list_search_indexes(indice)), {})
            if info.get("queryable"):
                break
            time.sleep(2)
        print(f"  índice {indice}: {'listo' if info.get('queryable') else 'pendiente'}")


def sembrar() -> None:
    db = cliente()["ia_conocimiento"]
    if db["casos_anonimizados"].count_documents({}) == 0:
        casos = json.loads((CORPUS / "casos_sinteticos.json").read_text(encoding="utf-8"))
        vectores = embeddings([f"{c['resumen']} {c['formula_arreglo']}" for c in casos])
        db["casos_anonimizados"].insert_many([{**c, "embedding": v, "sintetico": True,
                                               "creado_en": datetime.now(timezone.utc)} for c, v in zip(casos, vectores)])
        print(f"  casos sintéticos: {len(casos)}")
    if db["fuentes_juridicas"].count_documents({}) == 0:
        fuentes = json.loads((CORPUS / "fuentes_sinteticas.json").read_text(encoding="utf-8"))
        db["fuentes_juridicas"].insert_many([{**f, "sintetico": True} for f in fuentes])
        n = sum(ingerir(f["titulo"], "PUBLICO", f["materia"], [{"numero": 1, "texto": f["texto"]}]) for f in fuentes)
        print(f"  fuentes sintéticas: {len(fuentes)} ({n} fragmentos públicos)")


if __name__ == "__main__":
    if "--reiniciar" in sys.argv:
        for base in ("ia_conocimiento", "ia_uso", "ia_uso_odr"):
            cliente().drop_database(base)
    print("Creando colecciones e índices…")
    crear_colecciones()
    print("Sembrando corpus sintético (requiere Ollama con bge-m3)…")
    sembrar()
    esperar_indices()
    print("MongoDB listo.")
