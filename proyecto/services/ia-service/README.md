# Servicio de IA (ia-service)

Servicio **interno**: solo lo llama `core-api`, con el encabezado `X-Servicio-Token`. No tiene acceso a PostgreSQL. Usa Ollama local (`qwen2.5:7b` para generar texto y `bge-m3` para embeddings de 1024 dimensiones) y MongoDB con búsqueda vectorial. Toda salida es **apoyo**: la persona revisa y decide (RF8.6).

| Endpoint | Requisito | Qué hace |
| --- | --- | --- |
| `POST /interno/clasificar` | RF2.2–RF2.3 | Materia civil o familiar, confianza, complejidad y si es mediable (detecta violencia). |
| `POST /interno/acuerdos/sugerir` | RF3.3 | `$vectorSearch` sobre `casos_anonimizados` sintéticos, con umbral. Si no hay casos similares responde sin sugerencia. Registra en `ia_uso_odr`. |
| `POST /interno/demanda/borrador` | RF5.1 | Prestaciones, hechos y derecho sobre una plantilla procesal, sin inventar datos. |
| `POST /interno/turnos/sugerir` | RF7.2 | Puntaje determinista por carga y especialidad, con justificación del modelo. No recibe hechos ni nombres. |
| `POST /interno/rag/consultar` | RF8.1–RF8.6 | Prefiltro `{PUBLICO + materia} ∪ {EXPEDIENTE + expediente_id}`, saneamiento contra inyección y síntesis con citas `[n]`. Registra en `ia_uso`. |
| `POST /interno/ingesta` | P15 | Limpieza, anonimización `[PERSONA_n]`, fragmentos de 400 palabras con traslape de 50, embeddings e inserción. |

## Ejecutar

```bash
cp .env.example .env          # IA_SERVICIO_TOKEN = SJI_IA_TOKEN de core-api
uv sync --extra test
uv run python ../../persistence/mongo/inicializar.py   # colecciones, validadores, índices y corpus sintético
uv run uvicorn api.main:app --app-dir src --port 8001
```

Ollama debe estar corriendo con los modelos descargados (`ollama pull qwen2.5:7b bge-m3`). Al iniciar, el servicio precarga los modelos y los mantiene en memoria 60 minutos.

## Rendimiento medido (MacBook M3, 16 GB, modelos en SSD externo)

| Operación | Modelo ya cargado | Primera carga |
| --- | --- | --- |
| Clasificación | 4.7–8.4 s | ~4 min (lectura de 4.7 GB) |
| Sugerencia de acuerdo | 18–28 s | — |
| Consulta RAG | ~32 s | — |

El documento pide menos de 3 s para clasificar (RNF2.1) y menos de 5 s para sugerir acuerdos (RNF2.3). Con un modelo de 7B en esta laptop **no se cumple**. Hay que medirlo en el hardware institucional, o usar un modelo más ligero (`IA_MODELO_CHAT`). Si la IA no responde a tiempo, `core-api` usa reglas o plantillas y el trámite continúa.

## Pruebas

```bash
uv run pytest
```
