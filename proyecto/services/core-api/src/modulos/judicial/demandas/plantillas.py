"""Plantilla procesal base (respaldo cuando no hay IA). El texto siempre se revisa y edita antes de presentarse."""
from datetime import date

_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
          "noviembre", "diciembre"]
_JUEZ = {"CIVIL": "C. JUEZ DE LO CIVIL DE PROCESO ORAL EN TURNO", "FAMILIAR": "C. JUEZ DE LO FAMILIAR EN TURNO"}


def redactar(d: dict) -> str:
    hoy = date.today()
    demandado = d["demandado"]
    domicilio = demandado.get("domicilio_notificaciones") or "[falta domicilio]"
    pendientes = ""
    if d["puntos_pendientes"]:
        pendientes = "\n\nPuntos no resueltos en el convenio parcial de mediación:\n" + "\n".join(
            f"- {x}" for x in d["puntos_pendientes"])
    return f"""Ciudad de México, a {hoy.day} de {_MESES[hoy.month - 1]} de {hoy.year}

{_JUEZ[d['materia']]}
P R E S E N T E

{d['demandante']['nombre'].upper()}, por mi propio derecho, señalando como correo para oír y recibir notificaciones {d['demandante'].get('correo') or '[correo]'}, ante Usted comparezco para promover {d['tipo_juicio'].lower()} en contra de {demandado['nombre'].upper()}, con domicilio en {domicilio}, de quien reclamo las siguientes

P R E S T A C I O N E S

A) {d['pretension']}.

H E C H O S

1. {d['narrativa']}{pendientes}

D E R E C H O

[Fundamentos aplicables según la materia {d['materia'].lower()}.]

P R U E B A S

[Relaciona aquí los anexos que adjuntes.]

Por lo expuesto, atentamente pido se admita la presente demanda.

{d['demandante']['nombre'].upper()}"""
