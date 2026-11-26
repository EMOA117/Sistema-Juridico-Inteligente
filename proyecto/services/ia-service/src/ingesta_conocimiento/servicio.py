"""P15: ingesta → limpieza → anonimización [PERSONA_n] → fragmentos de 400 palabras con traslape de 50 → BGE-M3 → índice."""
from datetime import datetime, timezone

from compartido.mongo import conocimiento
from compartido.ollama import embeddings
from compartido.texto import anonimizar, fragmentar, limpiar


def ingerir(documento: str, acceso: str, materia: str, paginas: list[dict], *, expediente_id: str | None = None,
            documento_id: str | None = None, nombres: list[str] | None = None, sintetico: bool = True) -> int:
    if acceso == "EXPEDIENTE" and not expediente_id:
        raise ValueError("Un documento de expediente requiere expediente_id")
    piezas = []
    for p in paginas:
        for trozo in fragmentar(anonimizar(limpiar(p["texto"]), nombres)):
            piezas.append({"texto": trozo, "pagina": p.get("numero")})
    if not piezas:
        return 0
    vectores = []
    for i in range(0, len(piezas), 16):
        vectores += embeddings([x["texto"] for x in piezas[i:i + 16]])
    ahora = datetime.now(timezone.utc)
    conocimiento()["fragmentos"].insert_many([{
        "texto": x["texto"], "pagina": x["pagina"], "documento": documento, "acceso": acceso, "materia": materia,
        "origen": {"expediente_id": expediente_id, "documento_id": documento_id}, "embedding": v,
        "sintetico": sintetico, "creado_en": ahora} for x, v in zip(piezas, vectores)])
    return len(piezas)
