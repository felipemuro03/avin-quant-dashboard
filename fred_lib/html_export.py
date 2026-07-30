import base64
from pathlib import Path

import plotly.graph_objects as go
import plotly.offline as pyo

from . import formatos

NAVY = "#102134"
GOLD = "#BAA377"
GOLD_ESCURO = "#896F3D"

RAIZ_PROJETO = Path(__file__).resolve().parents[1]

_SEM_CATEGORIA = "Outros"


def _logo_base64() -> str:
    caminho = RAIZ_PROJETO / "assets" / "logo_swm.png"
    if not caminho.exists():
        return ""
    return base64.b64encode(caminho.read_bytes()).decode("ascii")


def _slug(texto: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in texto).strip("-")


def _grafico_html(serie) -> str:
    serie = serie.dropna()
    fig = go.Figure(
        go.Scatter(
            x=serie.index,
            y=serie.values,
            mode="lines",
            line=dict(color=GOLD_ESCURO, width=2),
            hovertemplate="%{x|%b/%Y}: %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=280,
        margin=dict(l=48, r=24, t=16, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Montserrat, Arial, sans-serif", color="#0D0D0D", size=12),
        xaxis=dict(
            type="date",
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1A", step="year", stepmode="backward"),
                    dict(count=3, label="3A", step="year", stepmode="backward"),
                    dict(count=5, label="5A", step="year", stepmode="backward"),
                    dict(step="all", label="Máx"),
                ],
                font=dict(color=NAVY),
                bgcolor="#F2EFE9",
                activecolor=GOLD,
            ),
            rangeslider=dict(visible=True, thickness=0.08, bgcolor="#F2EFE9"),
        ),
        yaxis=dict(gridcolor="#EDEDED"),
    )
    return pyo.plot(
        fig,
        include_plotlyjs=False,
        output_type="div",
        config={"displaylogo": False, "locale": "pt-BR"},
    )


def _card_html(dados: dict) -> str:
    nome = dados.get("nome", "")
    nota = dados.get("nota", "")
    url = dados.get("url", "")
    unidade = dados.get("unidade", {})
    serie = dados["serie"].dropna()
    ultimo = serie.iloc[-1]
    data_ultima = serie.index[-1].strftime("%m/%Y")
    grafico = _grafico_html(serie)
    valor_fmt = formatos.formatar_valor(ultimo, unidade)
    badge = formatos.badge_unidade(unidade)
    meta_texto = f"{nota} · {badge}" if nota else badge
    link_html = (
        f'<a href="{url}" target="_blank" rel="noopener">Ver fonte ↗</a>' if url else ""
    )
    return f"""
        <section class="card">
            <h3>{nome}</h3>
            <div class="meta">{meta_texto}</div>
            <div class="valor">{valor_fmt}<span class="valor-data">último dado: {data_ultima}</span></div>
            {grafico}
            <div class="link">{link_html}</div>
        </section>
        """


def exportar_html(
    series_por_indicador: dict,
    caminho_saida: str,
    gerado_em: str,
    titulo: str = "Cenário Econômico dos EUA",
    fonte: str = "FRED (Federal Reserve Economic Data)",
) -> str:
    """
    series_por_indicador: dict no formato
        {series_id: {"nome": str, "serie": pandas.Series, "nota": str, "url": str,
                      "categoria": str (opcional)}}
    Gera um relatório HTML autocontido (funciona offline, sem servidor), agrupado
    por categoria, com um gráfico interativo (zoom/seletor de período) por
    indicador — pensado para ver o cenário completo, não só indicadores avulsos.
    """
    logo_b64 = _logo_base64()
    logo_html = (
        f'<img class="logo" src="data:image/png;base64,{logo_b64}" alt="SWM">'
        if logo_b64
        else ""
    )

    grupos = {}
    for series_id, dados in series_por_indicador.items():
        if dados["serie"].dropna().empty:
            continue
        categoria = dados.get("categoria") or _SEM_CATEGORIA
        grupos.setdefault(categoria, []).append(dados)

    nav_links = []
    secoes = []
    for categoria, itens in grupos.items():
        ancora = _slug(categoria)
        nav_links.append(f'<a href="#{ancora}">{categoria}</a>')
        cards = "".join(_card_html(d) for d in itens)
        secoes.append(
            f"""
            <section class="grupo" id="{ancora}">
                <h2>{categoria}</h2>
                <div class="grid">{cards}</div>
            </section>
            """
        )

    plotlyjs = pyo.get_plotlyjs()

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');

    * {{ box-sizing: border-box; }}
    body {{
        margin: 0;
        font-family: 'Montserrat', Arial, sans-serif;
        background: #F7F6F3;
        color: #0D0D0D;
    }}
    header.hero {{
        background: {NAVY};
        color: #FFFFFF;
        padding: 32px 48px;
        display: flex;
        align-items: center;
        gap: 20px;
    }}
    header.hero .logo {{
        height: 48px;
    }}
    header.hero h1 {{
        font-weight: 300;
        font-size: 28px;
        margin: 0;
    }}
    header.hero .sub {{
        color: {GOLD};
        font-size: 13px;
        margin-top: 4px;
    }}
    nav {{
        position: sticky;
        top: 0;
        background: #FFFFFF;
        border-bottom: 1px solid #E5E1D8;
        padding: 12px 48px;
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        z-index: 10;
    }}
    nav a {{
        color: {NAVY};
        text-decoration: none;
        font-size: 13px;
        font-weight: 600;
    }}
    nav a:hover {{
        color: {GOLD_ESCURO};
    }}
    main {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 32px 24px 64px;
    }}
    .grupo {{
        margin-bottom: 40px;
        scroll-margin-top: 56px;
    }}
    .grupo h2 {{
        font-size: 20px;
        font-weight: 600;
        color: {NAVY};
        margin: 0 0 16px;
    }}
    .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
        gap: 20px;
    }}
    .card {{
        background: #FFFFFF;
        border-radius: 10px;
        box-shadow: 0 1px 6px rgba(16, 33, 52, 0.08);
        padding: 20px;
    }}
    .card h3 {{
        font-size: 15px;
        font-weight: 600;
        color: {NAVY};
        margin: 0 0 2px;
    }}
    .card .meta {{
        font-size: 12px;
        color: #7A7A7A;
        margin-bottom: 8px;
    }}
    .card .valor {{
        font-size: 26px;
        font-weight: 700;
        color: {NAVY};
        margin-bottom: 8px;
    }}
    .card .valor-data {{
        font-size: 12px;
        font-weight: 400;
        color: #7A7A7A;
        margin-left: 10px;
    }}
    .card .link {{
        margin-top: 8px;
        font-size: 13px;
    }}
    .card .link a {{
        color: {GOLD_ESCURO};
        text-decoration: none;
        font-weight: 600;
    }}
    .card .link a:hover {{
        text-decoration: underline;
    }}
    footer {{
        text-align: center;
        font-size: 12px;
        color: #999999;
        padding: 24px;
    }}
</style>
</head>
<body>
<header class="hero">
    {logo_html}
    <div>
        <h1>{titulo}</h1>
        <div class="sub">Gerado em {gerado_em} · Fonte: {fonte}</div>
    </div>
</header>
<nav>{"".join(nav_links)}</nav>
<main>
    {''.join(secoes)}
</main>
<footer>Uso interno · SWM Gestão</footer>
<script>{plotlyjs}</script>
</body>
</html>
"""

    Path(caminho_saida).write_text(html, encoding="utf-8")
    return caminho_saida
