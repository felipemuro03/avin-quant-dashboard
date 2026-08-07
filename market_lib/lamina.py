"""Geracao da lamina PDF de Oportunidades: um resumo de 1 pagina, so com tabelas,
para o gestor consultar sem precisar abrir o dashboard."""

import datetime as dt
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from market_lib.estilo import GOLD_ESCURO, NAVY

COLUNAS_LAMINA = ["Ticker", "Nome", "Score Reversao (0-100)", "Z-Score", "Posicao (%)", "RSI"]
CABECALHO_LAMINA = ["Ticker", "Nome", "Score", "Z-Score", "Posicao (%)", "RSI"]

_ESTILO_NOME = ParagraphStyle("NomeCelula", fontName="Helvetica", fontSize=8, leading=9.5)


def _formatar_linhas(df: pd.DataFrame) -> list:
    linhas = [CABECALHO_LAMINA]
    for _, row in df.iterrows():
        linhas.append([
            row["Ticker"],
            Paragraph(row["Nome"], _ESTILO_NOME),
            f"{row['Score Reversao (0-100)']:.0f}",
            f"{row['Z-Score']:.2f}",
            f"{row['Posicao (%)']:.0f}",
            f"{row['RSI']:.1f}",
        ])
    return linhas


def _montar_tabela(df: pd.DataFrame) -> Table:
    tabela = Table(_formatar_linhas(df), colWidths=[2 * cm, 5.5 * cm, 1.8 * cm, 2 * cm, 2.5 * cm, 1.8 * cm])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2EFE8")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabela


def gerar_lamina_pdf(
    consolidado: pd.DataFrame,
    categorias: list,
    anos_valor_relativo: float,
    periodo_rsi: int,
    top_n: int = 10,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )

    estilo_titulo = ParagraphStyle("Titulo", fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=6, textColor=colors.HexColor(NAVY))
    estilo_sub = ParagraphStyle("Sub", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#555555"))
    estilo_secao = ParagraphStyle("Secao", fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor(GOLD_ESCURO), spaceBefore=10, spaceAfter=4)
    estilo_rodape = ParagraphStyle("Rodape", fontName="Helvetica-Oblique", fontSize=7.5, textColor=colors.HexColor("#777777"))

    elementos = [
        Paragraph("AVIN Quant &mdash; Lamina de Oportunidades", estilo_titulo),
        Paragraph(
            f"Gerada em {dt.date.today().strftime('%d/%m/%Y')} &middot; "
            f"Categorias: {', '.join(categorias) if categorias else 'todas'} &middot; "
            f"Janela de valor relativo: {anos_valor_relativo} anos &middot; Periodo RSI: {periodo_rsi}",
            estilo_sub,
        ),
        Spacer(1, 10),
        Paragraph(f"Top {top_n} &mdash; Setups de reversao mais fortes (nesta leitura)", estilo_secao),
        _montar_tabela(consolidado.head(top_n)[COLUNAS_LAMINA]),
        Paragraph(f"Top {top_n} &mdash; Mais esticados para o outro lado", estilo_secao),
        _montar_tabela(consolidado.tail(top_n)[COLUNAS_LAMINA]),
        Spacer(1, 10),
        Paragraph(
            "Em resumo: e um ranking de ativos que estao descontados em relacao a propria media "
            "historica de preco (nao diz o motivo do desconto, so aponta a estatistica).",
            estilo_rodape,
        ),
        Paragraph(
            "<b>Score</b>: media dos 3 itens abaixo, de 0 a 100 &mdash; quanto mais perto de 100, "
            "mais descontado nas 3 leituras ao mesmo tempo. "
            "<b>Z-Score</b>: quantos desvios-padrao o preco atual esta da media historica do proprio "
            "ativo (negativo = abaixo da media / mais barato). "
            "<b>Posicao (%)</b>: onde o preco esta hoje entre a minima (0%) e a maxima (100%) do "
            "periodo. "
            "<b>RSI</b>: momentum de 0 a 100 &mdash; abaixo de 30 e considerado sobrevendido, acima "
            "de 70 e considerado sobrecomprado.",
            estilo_rodape,
        ),
        Spacer(1, 4),
        Paragraph(
            "E uma leitura de mean reversion, nao a unica leitura valida e nao e recomendacao de "
            "compra/venda &mdash; leitura puramente estatistica sobre preco, nao considera "
            "fundamento, fluxo, catalisadores ou cenario macro.",
            estilo_rodape,
        ),
    ]

    doc.build(elementos)
    return buffer.getvalue()
