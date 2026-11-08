"""Recuperación léxica reproducible de ejemplos sintéticos; no es un modelo jurídico."""
import re
import unicodedata

EJEMPLOS = [
    {'id': 'SINT-CIV-01', 'materia': 'CIVIL', 'claves': {'renta', 'arrendamiento', 'pago', 'adeudo'},
     'texto': 'Ejemplo inventado: las partes propusieron un calendario de pagos y comprobantes de cumplimiento. Revisen montos y fechas según su situación.'},
    {'id': 'SINT-CIV-02', 'materia': 'CIVIL', 'claves': {'reparacion', 'humedad', 'filtracion', 'vecino'},
     'texto': 'Ejemplo inventado: las partes acordaron una inspección conjunta, un presupuesto y fechas de reparación.'},
    {'id': 'SINT-FAM-01', 'materia': 'FAMILIAR', 'claves': {'convivencia', 'horarios', 'visitas', 'calendario'},
     'texto': 'Ejemplo inventado: las partes prepararon un calendario de convivencia para revisión de un mediador. No determina derechos ni sustituye la revisión del caso.'},
]


def recomendar(narrativa, materia):
    normal = ''.join(c for c in unicodedata.normalize('NFD', narrativa.lower()) if unicodedata.category(c) != 'Mn')
    palabras = set(re.findall(r'\w+', normal))
    candidatos = [(len(palabras & e['claves']), e) for e in EJEMPLOS if e['materia'] == materia]
    puntos, ejemplo = max(candidatos, key=lambda x: x[0], default=(0, None))
    return {'motor': 'recuperacion-lexica-sintetica-v1', 'es_ia': False,
            'fuente': ejemplo['id'] if puntos >= 2 else None,
            'texto': ejemplo['texto'] if puntos >= 2 else 'No hay un ejemplo sintético suficientemente relacionado. Solicita revisión de un mediador.',
            'requiere_revision_humana': True}
