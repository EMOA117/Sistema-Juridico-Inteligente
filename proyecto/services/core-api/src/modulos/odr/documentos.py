"""Documento de revisión: bytes estables cuya huella firman todas las partes."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


def generar_convenio(conflicto_id, partes, convenio):
    salida = BytesIO()
    doc = SimpleDocTemplate(salida, pagesize=(21*cm, 29.7*cm), leftMargin=2.2*cm,
                            rightMargin=2.2*cm, topMargin=2*cm, bottomMargin=2*cm,
                            title='Convenio ODR - demostración académica')
    estilos = getSampleStyleSheet()
    estilos['BodyText'].leading = 16
    contenido = [Paragraph('CONCORDIA / MEDIACIÓN', estilos['Title']), Spacer(1, .4*cm),
                 Paragraph('DEMOSTRACIÓN ACADÉMICA. DATOS SINTÉTICOS.<br/>Sin firma electrónica institucional ni efectos jurídicos certificados.', estilos['Heading2']),
                 Paragraph(f'Convenio {convenio.tipo.lower()} / Asunto {conflicto_id}', estilos['BodyText'])]
    for parte in partes:
        contenido.append(Paragraph(escape(parte['rol'] + ': ' + parte['nombre']), estilos['BodyText']))
    contenido += [Spacer(1, .5*cm), Paragraph('Términos para revisión y aceptación', estilos['Heading2'])]
    contenido += [Paragraph(escape(p), estilos['BodyText']) for p in convenio.terminos.splitlines() if p.strip()]
    if convenio.puntos_pendientes:
        contenido += [Paragraph('Puntos pendientes (no resueltos)', estilos['Heading2'])]
        contenido += [Paragraph(escape(p), estilos['BodyText']) for p in convenio.puntos_pendientes]
    contenido += [Spacer(1, .6*cm), Paragraph('La aceptación de cada participante se conserva en el registro de firmas de demostración, vinculada a la huella SHA-256 de este documento. Un acuerdo parcial mantiene abierto el conflicto.', estilos['BodyText'])]

    def pie(canvas, documento):
        canvas.setFillColor(colors.HexColor('#4a5568'))
        canvas.setFont('Helvetica', 8)
        canvas.drawString(2.2*cm, 1.2*cm, 'Confidencial ODR | Documento sintético de demostración')
        canvas.drawRightString(18.8*cm, 1.2*cm, str(documento.page))

    doc.build(contenido, onFirstPage=pie, onLaterPages=pie)
    return salida.getvalue()
