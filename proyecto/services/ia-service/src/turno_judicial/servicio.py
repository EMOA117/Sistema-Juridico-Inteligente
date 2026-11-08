"""RF7.2: sugerencia de turno por carga y especialidad (contrato §11.1.1). Sin hechos, nombres ni datos ODR."""
from compartido.mongo import registrar_interaccion
from compartido.ollama import IANoDisponible, chat_json


def sugerir(expediente_id: str, materia: str, candidatos: list[dict]) -> dict:
    elegibles = [c for c in candidatos if c["especialidad"] == materia]
    if not elegibles:
        return {"expediente_id": expediente_id, "sugerencias": [], "modelo_version": None}
    maxima = max(c["expedientes_activos"] for c in elegibles) or 1
    puntuados = sorted(({**c, "puntaje": round(1 - 0.8 * c["expedientes_activos"] / (maxima + 1), 3)} for c in elegibles),
                       key=lambda c: -c["puntaje"])
    resumen = "; ".join(f"juez {i + 1}: {c['expedientes_activos']} expedientes activos, especialidad {c['especialidad']}" for i, c in enumerate(puntuados))
    try:
        datos, ms = chat_json('Explica en una frase por qué conviene el primer candidato para equilibrar cargas. Responde JSON {"justificacion": "..."}',
                              f"Materia del expediente: {materia}. Candidatos ordenados: {resumen}.", timeout=20)
        principal = str(datos.get("justificacion", ""))[:300]
    except IANoDisponible:
        principal, ms = "", 0
    sugerencias = [{"juzgado_id": c["juzgado_id"], "juez_id": c["juez_id"], "puntaje": c["puntaje"],
                    "justificacion": (principal if i == 0 and principal else
                                      f"Especialidad {c['especialidad'].lower()} con {c['expedientes_activos']} expedientes activos.")}
                   for i, c in enumerate(puntuados)]
    registrar_interaccion(odr=False, tipo="SUGERENCIA_TURNO", entrada={"materia": materia, "candidatos": len(elegibles)},
                          salida={"primero": sugerencias[0]["juez_id"]}, latencia_ms=ms, contexto={"expediente_id": expediente_id})
    return {"expediente_id": expediente_id, "sugerencias": sugerencias, "modelo_version": "qwen2.5:7b+reglas"}
