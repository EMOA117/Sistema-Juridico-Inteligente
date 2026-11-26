"""Limpieza, anonimización y fragmentación de texto (P15) y saneamiento contra inyección de instrucciones."""
import re

_CURP = re.compile(r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b")
_CORREO = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_TEL = re.compile(r"\b(?:\+?52\s?)?(?:\d[\s-]?){10}\b")
_INYECCION = re.compile(
    r"(?im)^.*\b(ignora|olvida|ignore|disregard)\b.*\b(instrucci|indicaci|instruction|previous|anterior)\w*.*$"
    r"|^\s*(system|sistema|assistant|asistente)\s*:.*$|<\|[^>]*\|>")


def limpiar(texto: str) -> str:
    texto = re.sub(r"[ \t]+", " ", texto.replace("\r", ""))
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def anonimizar(texto: str, nombres: list[str] | None = None) -> str:
    """Sustituye nombres conocidos por etiquetas [PERSONA_n] y elimina identificadores directos."""
    for i, nombre in enumerate(sorted({n for n in (nombres or []) if n and len(n) > 2}, key=len, reverse=True), 1):
        texto = re.sub(re.escape(nombre), f"[PERSONA_{i}]", texto, flags=re.I)
    texto = _CURP.sub("[CURP]", texto)
    texto = _CORREO.sub("[CORREO]", texto)
    return _TEL.sub("[TELÉFONO]", texto)


def fragmentar(texto: str, palabras: int = 400, traslape: int = 50) -> list[str]:
    tokens = texto.split()
    if len(tokens) <= palabras:
        return [texto] if tokens else []
    paso = palabras - traslape
    return [" ".join(tokens[i:i + palabras]) for i in range(0, max(len(tokens) - traslape, 1), paso)]


def sanear(texto: str) -> str:
    """Quita líneas que intentan dar órdenes al modelo; el contenido se trata siempre como dato."""
    return _INYECCION.sub("[texto omitido por seguridad]", texto)
