"""Clasificación de respaldo por palabras clave. Se usa cuando el servicio de IA no responde (RNF: no bloquear)."""
import re

_FAMILIAR = r"pensi[oó]n|alimento|divorci|custodia|convivencia|hij[oa]s?|c[oó]nyuge|patria potestad|r[eé]gimen"
_CIVIL = r"pr[eé]st|deud|pag[oa]r?|arrend|renta|contrato|da[nñ]o|inmueble|vivienda|dinero|\$"


def clasificar(narrativa: str) -> dict:
    t = narrativa.lower()
    fam = len(re.findall(_FAMILIAR, t))
    civ = len(re.findall(_CIVIL, t))
    materia = "FAMILIAR" if fam > civ else "CIVIL"
    total = fam + civ
    confianza = 0.5 if total == 0 else round(0.5 + 0.45 * abs(fam - civ) / total, 3)
    palabras = len(t.split())
    complejidad = "BAJA" if palabras < 60 else "MEDIA" if palabras < 250 else "ALTA"
    violencia = bool(re.search(r"violen|golpe|amenaz|agresi", t))
    return {
        "materia": materia, "confianza": confianza, "complejidad": complejidad,
        "mediable": not violencia and complejidad != "ALTA",
        "motivo": "Hay indicios de violencia: la mediación no es adecuada" if violencia
                  else "Asunto patrimonial o familiar sin indicios de violencia",
        "origen": "REGLAS", "interaccion_ia_id": None,
    }
