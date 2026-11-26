"""Clasificación de respaldo por palabras clave. Se usa cuando el servicio de IA no responde (RNF: no bloquear)."""
import re

_PATRONES = {
    "FAMILIAR": r"pensi[oó]n|alimento|divorci|custodia|convivencia|hij[oa]s?|c[oó]nyuge|patria potestad|r[eé]gimen",
    "LABORAL": r"despid|patr[oó]n|emplead|trabaj|salari|sueldo|finiquito|liquidaci[oó]n|aguinaldo|vacaciones|horas extra|imss",
    "MERCANTIL": r"pagar[eé]|cheque|factura|proveedor|comerci|empresa|mercanc|negocio|cr[eé]dito|tarjeta|socio",
    "CIVIL": r"pr[eé]st|deud|pag[oa]r?|arrend|renta|contrato|da[nñ]o|inmueble|vivienda|dinero|\$",
}


def clasificar(narrativa: str) -> dict:
    t = narrativa.lower()
    conteos = {m: len(re.findall(p, t)) for m, p in _PATRONES.items()}
    # En empate gana CIVIL (materia residual); las demás, por orden de especificidad.
    materia = max(reversed(list(conteos)), key=lambda m: conteos[m])
    total = sum(conteos.values())
    segundo = sorted(conteos.values())[-2]
    confianza = 0.5 if total == 0 else round(0.5 + 0.45 * (conteos[materia] - segundo) / total, 3)
    palabras = len(t.split())
    complejidad = "BAJA" if palabras < 60 else "MEDIA" if palabras < 250 else "ALTA"
    violencia = bool(re.search(r"violen|golpe|amenaz|agresi", t))
    return {
        "materia": materia, "confianza": confianza, "complejidad": complejidad,
        "mediable": not violencia and complejidad != "ALTA",
        "motivo": "Hay indicios de violencia: la conciliación no es adecuada" if violencia
                  else "Asunto sin indicios de violencia que puede conciliarse",
        "origen": "REGLAS", "interaccion_ia_id": None,
    }
