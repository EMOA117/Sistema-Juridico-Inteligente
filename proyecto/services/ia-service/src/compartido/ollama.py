"""Cliente mínimo de Ollama: chat con salida JSON y embeddings BGE-M3 (1024 dimensiones)."""
import json
import time

import httpx

from compartido.config import config


class IANoDisponible(RuntimeError):
    pass


def _chat_openai(sistema: str, usuario: str, temperatura: float, timeout: float) -> str:
    """Servidor compatible con OpenAI (p. ej. vLLM remoto). Se usa cuando IA_CHAT_URL está definido."""
    c = config()
    r = httpx.post(f"{c.chat_url.rstrip('/')}/chat/completions", timeout=timeout,
                   headers={"Authorization": f"Bearer {c.chat_api_key}"} if c.chat_api_key else {}, json={
        "model": c.chat_modelo or c.modelo_chat, "temperature": temperatura, "max_tokens": 800,
        "response_format": {"type": "json_object"},
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]})
    r.raise_for_status()
    texto = r.json()["choices"][0]["message"]["content"] or ""
    inicio, fin = texto.find("{"), texto.rfind("}")   # tolera texto o bloques ``` alrededor del JSON
    return texto[inicio:fin + 1] if inicio >= 0 else texto


def chat_json(sistema: str, usuario: str, *, temperatura: float = 0.2, timeout: float | None = None) -> tuple[dict, int]:
    c = config()
    inicio = time.perf_counter()
    try:
        if c.chat_url:
            texto = _chat_openai(sistema, usuario, temperatura, timeout or c.timeout_chat_s)
            return json.loads(texto), int((time.perf_counter() - inicio) * 1000)
        r = httpx.post(f"{c.ollama_url}/api/chat", timeout=timeout or c.timeout_chat_s, json={
            "model": c.modelo_chat, "stream": False, "format": "json", "keep_alive": c.mantener_cargado,
            "options": {"temperature": temperatura, "num_ctx": c.contexto_tokens, "num_predict": 600},
            "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]})
        r.raise_for_status()
        return json.loads(r.json()["message"]["content"]), int((time.perf_counter() - inicio) * 1000)
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError) as e:
        raise IANoDisponible(f"Modelo no disponible: {type(e).__name__}") from e


def embeddings(textos: list[str]) -> list[list[float]]:
    c = config()
    try:
        r = httpx.post(f"{c.ollama_url}/api/embed", timeout=120,
                       json={"model": c.modelo_embeddings, "input": textos, "keep_alive": c.mantener_cargado})
        r.raise_for_status()
        return r.json()["embeddings"]
    except (httpx.HTTPError, KeyError) as e:
        raise IANoDisponible(f"Embeddings no disponibles: {type(e).__name__}") from e


def precalentar() -> None:
    """Carga los modelos en memoria al iniciar para que la primera petición no espere la carga en frío."""
    try:
        embeddings(["calentamiento"])
        chat_json("Responde JSON.", '{"ok": true}', timeout=600)
    except IANoDisponible:
        pass
