"""Gera o PDF do resultado do Mapa Político pra enviar por e-mail ao participante.

Usa reportlab (pura Python, sem binário externo tipo wkhtmltopdf/Chrome) —
importante pra rodar sem dor de cabeça num free tier de PaaS.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROXO = colors.HexColor("#7c3aed")
ROXO_ESCURO = colors.HexColor("#5b21b6")
CINZA = colors.HexColor("#6b6880")
TEXTO = colors.HexColor("#211f2e")


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Title"], textColor=ROXO_ESCURO, fontSize=22, spaceAfter=4),
        "sub": ParagraphStyle("sub", parent=base["Normal"], textColor=CINZA, fontSize=10, spaceAfter=16),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], textColor=ROXO_ESCURO, fontSize=14, spaceBefore=14, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], textColor=TEXTO, fontSize=11.5, spaceBefore=10, spaceAfter=4),
        "corpo": ParagraphStyle("corpo", parent=base["Normal"], textColor=TEXTO, fontSize=10, leading=14),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"], textColor=TEXTO, fontSize=10, leading=14, leftIndent=14, bulletIndent=2),
        "frase": ParagraphStyle("frase", parent=base["Italic"], textColor=CINZA, fontSize=11, spaceAfter=14),
        "rodape": ParagraphStyle("rodape", parent=base["Normal"], textColor=CINZA, fontSize=7.5, spaceBefore=18),
    }


def gerar_pdf_resultado(nome, narrativa, macros, resultados_por_cargo):
    """Devolve os bytes do PDF com o resultado do teste."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    s = _estilos()
    story = []

    story.append(Paragraph("🧭 Mapa Político 2026", s["titulo"]))
    story.append(Paragraph(
        f"Resultado de {nome} — gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        s["sub"],
    ))

    story.append(Paragraph(narrativa.get("estilo_geral", ""), s["h2"]))
    if narrativa.get("frase_estilo"):
        story.append(Paragraph(f"“{narrativa['frase_estilo']}”", s["frase"]))

    for secao in narrativa.get("secoes", []):
        titulo = f"{secao.get('emoji', '')} {secao.get('titulo', '')} — {secao.get('classificacao', '')}".strip()
        story.append(Paragraph(titulo, s["h3"]))
        for bullet in secao.get("bullets", []):
            story.append(Paragraph(f"• {bullet}", s["bullet"]))
        if secao.get("lema"):
            story.append(Paragraph(secao["lema"], s["frase"]))

    if narrativa.get("resumo_final"):
        story.append(Paragraph("🎯 Em resumo", s["h2"]))
        story.append(Paragraph(narrativa["resumo_final"], s["corpo"]))

    for resultado in resultados_por_cargo.values():
        story.append(Paragraph(f"🏆 Ranking — {resultado['nome_cargo']}", s["h2"]))
        linhas = [["#", "Candidato(a)", "Partido", "Compatibilidade"]]
        for i, c in enumerate(resultado["ranking"], start=1):
            linhas.append([str(i), c["nome"], c["partido"], f"{c['percentual']}%"])
        tabela = Table(linhas, colWidths=[1.2 * cm, 7.5 * cm, 3 * cm, 4 * cm])
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ROXO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f5fb")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2dff2")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(tabela)
        if resultado.get("aviso"):
            story.append(Paragraph(resultado["aviso"], s["rodape"]))
        story.append(Spacer(1, 10))

    story.append(Paragraph(
        "⚠️ Este resultado não é uma recomendação de voto — mostra apenas o quanto as posições "
        "declaradas pelos candidatos se aproximam do que você respondeu. Dados coletados de fontes "
        "públicas e sujeitos a mudança até a eleição.",
        s["rodape"],
    ))

    doc.build(story)
    return buf.getvalue()
