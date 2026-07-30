import sys
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROJETO))

from market_lib import precos as precos_lib
from market_lib import analise
from market_lib.estilo import aplicar_estilo

st.set_page_config(page_title="Correlacoes e Valor Relativo", layout="wide", page_icon="🔗")
aplicar_estilo()

CAMINHO_UNIVERSO = RAIZ_PROJETO / "data" / "universo_ativos.csv"

st.title("Correlacoes e Valor Relativo")
st.caption(
    "Leitura estatistica simples e transparente — sem caixa-preta: correlacao entre retornos "
    "diarios e z-score do preco atual vs. a propria historia de cada ativo. Passe o mouse nos "
    "graficos para ver o nome e a descricao de cada ativo."
)

universo_base = precos_lib.carregar_universo(CAMINHO_UNIVERSO)

st.sidebar.header("Filtros")
categorias_disponiveis = sorted(universo_base["Categoria"].unique().tolist())
categorias_selecionadas = st.sidebar.multiselect(
    "Categorias", categorias_disponiveis, default=categorias_disponiveis
)

anos_janela_corr = st.sidebar.slider("Janela de correlacao (anos)", 1, 10, 3)
anos_janela_zscore = st.sidebar.slider("Janela de valor relativo / z-score (anos)", 1, 15, 5)

universo = universo_base[universo_base["Categoria"].isin(categorias_selecionadas)].copy()

if universo.empty:
    st.info("Selecione ao menos uma categoria na barra lateral.")
    st.stop()

anos_busca = max(anos_janela_corr, anos_janela_zscore) + 1
data_inicio = (dt.date.today() - dt.timedelta(days=365 * anos_busca)).isoformat()


@st.cache_data(ttl=3600, show_spinner="Buscando precos no Yahoo Finance...")
def _buscar_precos_cache(tickers, data_inicio):
    return precos_lib.buscar_precos(tickers, data_inicio)


@st.cache_data(ttl=86400, show_spinner=False)
def _buscar_nomes_cache(tickers):
    return precos_lib.buscar_nomes(tickers)


tickers = universo["Ticker"].tolist()
tabela_precos = _buscar_precos_cache(tickers, data_inicio)

if tabela_precos.empty:
    st.error("Nao consegui buscar precos para os ativos selecionados.")
    st.stop()

nomes = _buscar_nomes_cache(tuple(tickers))

# ======================================================================
# Matriz de correlacao
# ======================================================================
st.header("Matriz de correlacao")
st.caption(
    f"Correlacao dos retornos diarios nos ultimos {anos_janela_corr} ano(s). "
    "Perto de +1: os ativos tendem a subir/cair juntos. Perto de -1: tendem a se mover em "
    "direcoes opostas (bom para diversificacao)."
)

data_corte_corr = tabela_precos.index[-1] - pd.Timedelta(days=365 * anos_janela_corr)
precos_corr = tabela_precos[tabela_precos.index >= data_corte_corr]

tickers_com_dados = [t for t in tickers if t in precos_corr.columns and precos_corr[t].notna().sum() > 30]

if len(tickers_com_dados) < 2:
    st.warning("Poucos ativos com historico suficiente para calcular correlacao nesta janela.")
else:
    matriz = analise.matriz_correlacao(precos_corr, tickers_com_dados)
    nomes_matriz = [nomes.get(t, t) for t in matriz.columns]
    customdata = np.dstack([
        np.broadcast_to(np.array(nomes_matriz)[None, :], matriz.shape),
        np.broadcast_to(np.array(nomes_matriz)[:, None], matriz.shape),
    ])
    fig_corr = px.imshow(
        matriz,
        color_continuous_scale=["#b3261e", "#ffffff", "#1b7a3d"],
        zmin=-1, zmax=1,
        aspect="auto",
        labels=dict(color="Correlacao"),
    )
    fig_corr.update_traces(
        customdata=customdata,
        hovertemplate="%{x} (%{customdata[0]}) x %{y} (%{customdata[1]})<br>Correlacao: %{z:.2f}<extra></extra>",
    )
    fig_corr.update_layout(height=max(400, 22 * len(tickers_com_dados)))
    st.plotly_chart(fig_corr, use_container_width=True)

st.divider()

# ======================================================================
# Posicao no range (min / media / max / atual)
# ======================================================================
st.header("Posicao no range")
st.caption(
    f"Onde o preco atual esta hoje entre o minimo e o maximo dos ultimos {anos_janela_zscore} ano(s). "
    "A barra vai do minimo ao maximo da janela; o tracinho dourado marca a media; a bolinha marca "
    "o preco atual (verde = perto do minimo, vermelho = perto do maximo)."
)

posicoes = analise.ranking_posicao_no_range(tabela_precos, universo, anos_janela_zscore, nomes)

if posicoes.empty:
    st.warning("Nao ha historico suficiente para calcular a posicao no range nesta janela.")
else:
    fig_range = go.Figure()
    for _, linha in posicoes.iterrows():
        ticker = linha["Ticker"]
        legenda = f"{linha['Nome']}<br><i>{linha['Descricao']}</i>"
        fig_range.add_trace(go.Scatter(
            x=[linha["Minimo (US$)"], linha["Maximo (US$)"]],
            y=[ticker, ticker],
            mode="lines",
            line=dict(color="#C8BEAA", width=10),
            showlegend=False,
            hoverinfo="skip",
        ))
        fig_range.add_trace(go.Scatter(
            x=[linha["Media (US$)"]],
            y=[ticker],
            mode="markers",
            marker=dict(symbol="line-ns", size=16, color="#896F3D", line=dict(width=3, color="#896F3D")),
            showlegend=False,
            hovertemplate=f"{legenda}<br>Media: {linha['Media (US$)']:.2f}<extra></extra>",
        ))
        fig_range.add_trace(go.Scatter(
            x=[linha["Atual (US$)"]],
            y=[ticker],
            mode="markers",
            marker=dict(size=14, color=analise.cor_posicao(linha["Posicao (%)"]), line=dict(width=1, color="#102134")),
            showlegend=False,
            hovertemplate=(
                f"{legenda}<br>Atual: {linha['Atual (US$)']:.2f}<br>"
                f"Posicao no range: {linha['Posicao (%)']:.0f}%<extra></extra>"
            ),
        ))

    fig_range.update_layout(
        height=max(400, 34 * len(posicoes)),
        xaxis_title="Preco (US$)",
        yaxis=dict(categoryorder="array", categoryarray=posicoes["Ticker"].tolist()),
        margin=dict(l=10, r=10, t=10, b=40),
    )
    st.plotly_chart(fig_range, use_container_width=True)

st.divider()

# ======================================================================
# Valor relativo (z-score)
# ======================================================================
st.header("Valor relativo (z-score vs. propria historia)")
st.caption(
    f"Z-score do preco atual vs. media dos ultimos {anos_janela_zscore} ano(s), em desvios-padrao. "
    "Negativo = preco abaixo da media historica ('mais barato' vs. a propria historia); "
    "positivo = acima. Nao e recomendacao de compra/venda — e so uma leitura estatistica, "
    "para cruzar com fundamento e cenario macro antes de qualquer decisao."
)

ranking = analise.ranking_zscore(tabela_precos, universo, anos_janela_zscore, nomes)

if ranking.empty:
    st.warning("Nao ha historico suficiente para calcular o z-score nesta janela.")
else:
    def colorir_zscore(val):
        if pd.isna(val):
            return ""
        cor = "#b3261e" if val >= 0 else "#1b7a3d"
        return f"color: {cor}; font-weight: 600"

    colunas_tabela = ["Ticker", "Nome", "Categoria", "Subcategoria", "Preco Atual (US$)",
                       "Media Historica (US$)", "Z-Score"]
    st.dataframe(
        ranking[colunas_tabela].style
            .map(colorir_zscore, subset=["Z-Score"])
            .format({
                "Preco Atual (US$)": "{:.2f}",
                "Media Historica (US$)": "{:.2f}",
                "Z-Score": "{:.2f}",
            }),
        use_container_width=True,
        hide_index=True,
    )

    fig_zscore = px.bar(
        ranking,
        x="Ticker", y="Z-Score",
        color="Categoria",
        hover_name="Nome",
        hover_data={"Subcategoria": True, "Descricao": True, "Categoria": False},
    )
    fig_zscore.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_zscore.update_xaxes(categoryorder="array", categoryarray=ranking["Ticker"].tolist())
    st.plotly_chart(fig_zscore, use_container_width=True)
