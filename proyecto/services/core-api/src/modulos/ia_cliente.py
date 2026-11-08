"""Cliente de ia-service (API interna autenticada). Si la IA falla o tarda, devuelve None y el trámite sigue
con el respaldo correspondiente (reglas o plantilla): la IA nunca bloquea el procedimiento (decisión 003)."""
import logging

import httpx

from compartido.config import config

log = logging.getLogger("core-api.ia")


def _llamar(ruta: str, cuerpo: dict, timeout: float | None = None) -> dict | None:
    c = config()
    if not c.ia_token:
        return None
    try:
        r = httpx.post(f"{c.ia_url}{ruta}", json=cuerpo, headers={"X-Servicio-Token": c.ia_token},
                       timeout=timeout or c.ia_timeout_s)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        log.warning("ia-service %s no disponible: %s", ruta, type(e).__name__)  # sin contenido en logs
        return None


def clasificar(narrativa: str) -> dict | None:
    return _llamar("/interno/clasificar", {"narrativa": narrativa}, timeout=20)


def sugerir_acuerdo(materia: str, narrativa: str, propuestas: list[str], nombres: list[str]) -> dict | None:
    return _llamar("/interno/acuerdos/sugerir", {"materia": materia, "narrativa": narrativa, "propuestas": propuestas, "nombres": nombres},
                   timeout=90)


def borrador_demanda(datos: dict) -> dict | None:
    return _llamar("/interno/demanda/borrador", datos, timeout=90)


def sugerir_turno(expediente_id: str, materia: str, candidatos: list[dict]) -> dict | None:
    return _llamar("/interno/turnos/sugerir", {"expediente_id": expediente_id, "materia": materia, "candidatos": candidatos})


def consultar_rag(datos: dict) -> dict | None:
    return _llamar("/interno/rag/consultar", datos, timeout=90)


def ingerir(datos: dict) -> dict | None:
    return _llamar("/interno/ingesta", datos, timeout=180)
