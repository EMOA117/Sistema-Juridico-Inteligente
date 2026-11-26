"""Documentos oficiales en PDF con el estilo Concordia (convenio P5 y resolución P12)."""
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

TINTA, JADE, TOGA, LATON = colors.HexColor("#101C2E"), colors.HexColor("#1F6B5C"), colors.HexColor("#2B4A86"), colors.HexColor("#C9922E")
_base = ParagraphStyle("base", fontName="Times-Roman", fontSize=11.5, leading=16, textColor=TINTA)
_titulo = ParagraphStyle("titulo", parent=_base, fontSize=22, leading=26, spaceAfter=6)
_etiqueta = ParagraphStyle("etiqueta", parent=_base, fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=colors.HexColor("#4A5568"))
_mono = ParagraphStyle("mono", parent=_base, fontName="Courier", fontSize=9, leading=12)


def _p(texto: str, estilo=_base) -> Paragraph:
    return Paragraph(escape(texto).replace("\n", "<br/>"), estilo)


def _documento(encabezado: str, titulo: str, referencia: str, color, cuerpo: list, pie: str) -> bytes:
    buf = BytesIO()

    def marco(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(TINTA)
        canvas.rect(0, LETTER[1] - 1.4 * cm, LETTER[0], 1.4 * cm, stroke=0, fill=1)
        canvas.setFillColor(LATON)
        canvas.rect(0, LETTER[1] - 1.5 * cm, LETTER[0], 0.1 * cm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Times-Roman", 12)
        canvas.drawString(2 * cm, LETTER[1] - 0.9 * cm, "Plataforma Jurídica Inteligente")
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#4A5568"))
        canvas.drawString(2 * cm, 1.2 * cm, pie)
        canvas.drawRightString(LETTER[0] - 2 * cm, 1.2 * cm, f"Pág. {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=2.4 * cm, rightMargin=2.4 * cm, topMargin=2.6 * cm,
                            bottomMargin=2.4 * cm, title=titulo, author="Plataforma Jurídica Inteligente (demo)")
    cab = Table([[_p(encabezado, _etiqueta), _p(referencia, ParagraphStyle("ref", parent=_mono, textColor=color, alignment=2))]],
                colWidths=[10 * cm, 6.5 * cm])
    cab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    doc.build([cab, Spacer(1, 6), _p(titulo, _titulo), Spacer(1, 6), *cuerpo], onFirstPage=marco, onLaterPages=marco)
    return buf.getvalue()


def convenio(folio: str, tipo: str, partes: list[str], mediador: str | None, terminos: str, pendientes: list[str]) -> bytes:
    cuerpo = [_p("PARTES", _etiqueta),
              _p(", ".join(p.upper() for p in partes) + (f", con la intervención de {mediador}" if mediador else "") + "."),
              Spacer(1, 10), _p("CLÁUSULAS ACORDADAS", _etiqueta), _p(terminos)]
    if pendientes:
        cuerpo += [Spacer(1, 10), _p("PUNTOS PENDIENTES · CANALIZABLES A LA VÍA JUDICIAL", _etiqueta),
                   *[_p(f"• {x}") for x in pendientes]]
    cuerpo += [Spacer(1, 14), _p("FIRMAS ELECTRÓNICAS", _etiqueta),
               _p("Este documento se firma electrónicamente por cada interviniente. Las firmas, certificados y sellos de tiempo "
                  "se encuentran incrustados en el archivo PDF (PAdES) y pueden validarse con cualquier lector compatible.")]
    return _documento("CENTRO DE JUSTICIA ALTERNATIVA", "Convenio de mediación",
                      f"{folio}\nACUERDO {tipo}", JADE, cuerpo,
                      f"Generado {datetime.now():%d/%m/%Y %H:%M} · Documento sintético de demostración (ESCOM) · Sin validez legal")


def resolucion(numero: str, juzgado: str, partes: str, resultado: str, texto: str, juez: str) -> bytes:
    cuerpo = [_p(f"Expediente {numero} · {partes}"), Spacer(1, 8), _p("SENTIDO DE LA RESOLUCIÓN", _etiqueta),
              _p(resultado), Spacer(1, 8), _p("CONSIDERANDOS Y PUNTOS RESOLUTIVOS", _etiqueta), _p(texto),
              Spacer(1, 16), _p(f"Así lo resolvió {juez}.")]
    return _documento(juzgado.upper(), "Resolución judicial", f"EXP {numero}", TOGA, cuerpo,
                      f"Generado {datetime.now():%d/%m/%Y %H:%M} · Documento sintético de demostración (ESCOM) · Sin validez legal")
