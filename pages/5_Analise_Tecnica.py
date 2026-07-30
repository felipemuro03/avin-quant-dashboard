import sys
import datetime as dt
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROJETO))

from market_lib import precos as precos_lib
from market_lib import tecnica
from market_lib.estilo import aplicar_estilo, NAVY, GOLD_ESCURO

st.set_page_config(page_title="Analise Tecnica", layout="wide", page_icon="📉")
aplicar_estilo()

CAMINHO_UNIVERSO = RAIZ_PROJETO / "data" / "universo_ativos.csv"

st.title("Analise Tecnica")
st.caption(
    "Comportamento do preco: medias moveis (MA20/50/100/200), momentum (RSI) e volatilidade "
    "(regime + Bandas de Bollinger). Leitura estatistica do preco em si — nao usa fundamento "
    "nem cenario macro."
)

universo_base = precos_lib.carregar_universo(CAMINHO_UNIVERSO)

st.sidebar.header("Filtros")
categorias_disponiveis = sorted(universo_base["Categoria"].unique().tolist())
categorias_selecionadas = st.sidebar.multiselect(
    "Categorias", categorias_disponiveis, default=categorias_disponiveis
)

universo = universo_base[universo_base["Categoria"].isin(categorias_selecionadas)].copy()

if universo.empty:
    st.info("Selecione ao menos uma categoria na barra lateral.")
    st.stop()

with st.sidebar.expander("Parametros avancados"):
    periodo_rsi = st.slider("Periodo do RSI", 5, 30, 14)
    janela_vol_curta = st.slider("Janela da volatilidade recente (dias)", 10, 60, 20)
    anos_vol_historico = st.slider("Janela historica p/ regime de vol (anos)", 1, 10, 3)
    janela_bollinger = st.slider("Janela das Bandas de Bollinger (dias)", 10, 60, 20)
    desvios_bollinger = st.slider("Bandas de Bollinger (desvios-padrao)", 1.0, 3.0, 2.0, step=0.5)

tickers = universo["Ticker"].tolist()
anos_busca = max(anos_vol_historico, 3) + 1
data_inicio = (dt.date.today() - dt.timedelta(days=365 * anos_busca)).isoformat()


@st.cache_data(ttl=3600, show_spinner="Buscando precos no Yahoo Finance...")
def _buscar_precos_cache(tickers, data_inicio):
    return precos_lib.buscar_precos(tickers, data_inicio)


@st.cache_data(ttl=86400, show_spinner=False)
def _buscar_nomes_cache(tickers):
    return precos_lib.buscar_nomes(tickers)


tabela_precos = _buscar_precos_cache(tickers, data_inicio)

if tabela_precos.empty:
    st.error("Nao consegui buscar precos para os ativos selecionados.")
    st.stop()

nomes = _buscar_nomes_cache(tuple(tickers))
descricoes = universo.set_index("Ticker")["Descricao"].to_dict()

# ======================================================================
# Deep-dive num ativo
# ======================================================================
st.header("Detalhe por ativo")

ticker_selecionado = st.selectbox(
    "Ativo",
    tickers,
    format_func=lambda t: f"{t} — {nomes.get(t, t)}",
)
serie_selecionada = tabela_precos[ticker_selecionado].dropna()
st.caption(f"**{nomes.get(ticker_selecionado, ticker_selecionado)}** — {descricoes.get(ticker_selecionado, '')}")

aba_medias, aba_momentum, aba_vol = st.tabs(["Medias Moveis", "Momentum (RSI)", "Volatilidade (Bollinger)"])

with aba_medias:
    df_ma = tecnica.medias_moveis(serie_selecionada)
    fig_ma = go.Figure()
    fig_ma.add_trace(go.Scatter(x=df_ma.index, y=df_ma["Preco"], name="Preco", line=dict(color=NAVY, width=2)))
    cores_ma = {"MA20": "#896F3D", "MA50": "#1b7a3d", "MA100": "#C8BEAA", "MA200": "#b3261e"}
    for coluna, cor in cores_ma.items():
        fig_ma.add_trace(go.Scatter(x=df_ma.index, y=df_ma[coluna], name=coluna, line=dict(color=cor, width=1.5)))
    fig_ma.update_layout(height=450, yaxis_title="Preco (US$)", legend_title="Serie")
    st.plotly_chart(fig_ma, use_container_width=True)

    estrutura = tecnica.estrutura_tendencia(serie_selecionada)
    col1, col2, col3 = st.columns(3)
    col1.metric("Acima de quantas medias (0-4)", estrutura["acima_de"])
    col2.metric("Tendencia (MA50 x MA200)", estrutura["tendencia"])
    col3.metric("Cruzamento nos ultimos 10 pregoes", "Sim" if estrutura["cruzamento_recente"] else "Nao")

with aba_momentum:
    serie_rsi = tecnica.rsi(serie_selecionada, periodo_rsi).dropna()
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=serie_rsi.index, y=serie_rsi.values, name=f"RSI ({periodo_rsi})", line=dict(color=GOLD_ESCURO, width=2)))
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="#b3261e", annotation_text="Sobrecomprado (70)")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="#1b7a3d", annotation_text="Sobrevendido (30)")
    fig_rsi.update_layout(height=350, yaxis_title="RSI", yaxis_range=[0, 100])
    st.plotly_chart(fig_rsi, use_container_width=True)

    if not serie_rsi.empty:
        valor_rsi = serie_rsi.iloc[-1]
        st.metric(f"RSI ({periodo_rsi}) atual", f"{valor_rsi:.1f}", tecnica.classificar_rsi(valor_rsi))

with aba_vol:
    df_bb = tecnica.bandas_bollinger(serie_selecionada, janela_bollinger, desvios_bollinger)
    fig_bb = go.Figure()
    fig_bb.add_trace(go.Scatter(x=df_bb.index, y=df_bb["Banda_Superior"], name="Banda Superior",
                                 line=dict(color="#C8BEAA", width=1), showlegend=True))
    fig_bb.add_trace(go.Scatter(x=df_bb.index, y=df_bb["Banda_Inferior"], name="Banda Inferior",
                                 line=dict(color="#C8BEAA", width=1), fill="tonexty",
                                 fillcolor="rgba(200,190,170,0.2)", showlegend=True))
    fig_bb.add_trace(go.Scatter(x=df_bb.index, y=df_bb["Media"], name=f"Media ({janela_bollinger}d)",
                                 line=dict(color=GOLD_ESCURO, width=1, dash="dash")))
    fig_bb.add_trace(go.Scatter(x=df_bb.index, y=df_bb["Preco"], name="Preco", line=dict(color=NAVY, width=2)))
    fig_bb.update_layout(height=450, yaxis_title="Preco (US$)", legend_title="Serie")
    st.plotly_chart(fig_bb, use_container_width=True)

    regime_vol = tecnica.regime_volatilidade(serie_selecionada, janela_vol_curta, anos_vol_historico)
    col1, col2, col3 = st.columns(3)
    col1.metric("Vol. anualizada recente", f"{regime_vol['vol_atual']:.1f}%" if pd.notna(regime_vol["vol_atual"]) else "-")
    col2.metric(f"Vol. media (ult. {anos_vol_historico}a)", f"{regime_vol['vol_media_historica']:.1f}%" if pd.notna(regime_vol["vol_media_historica"]) else "-")
    col3.metric("Z-Score da volatilidade", f"{regime_vol['zscore_vol']:.2f}" if pd.notna(regime_vol["zscore_vol"]) else "-")
    st.caption(
        "Z-Score da volatilidade positivo = o ativo esta mais agitado do que o normal para ele "
        "mesmo; negativo = mais calmo do que o normal."
    )

st.divider()

# ======================================================================
# Visao do universo
# ======================================================================
st.header("Visao do universo")

aba_tendencia, aba_rsi, aba_vol_universo = st.tabs(["Estrutura de Tendencia", "Momentum (RSI)", "Regime de Volatilidade"])

with aba_tendencia:
    st.caption(
        "'Acima de (0-4)': em quantas das 4 medias moveis o preco atual esta acima "
        "(4 = alinhamento de alta consistente; 0 = alinhamento de baixa). "
        "'Tendencia' compara MA50 x MA200 (golden/death cross classico)."
    )
    ranking_tend = tecnica.ranking_tendencia(tabela_precos, universo, nomes)
    if ranking_tend.empty:
        st.warning("Sem dados suficientes.")
    else:
        colunas = ["Ticker", "Nome", "Categoria", "Preco Atual (US$)", "MA20", "MA50", "MA100", "MA200",
                   "Acima de (0-4)", "Tendencia (MA50 x MA200)", "Cruzamento recente"]

        def colorir_acima_de(val):
            if pd.isna(val):
                return ""
            cor = "#1b7a3d" if val >= 3 else ("#b3261e" if val <= 1 else "#896F3D")
            return f"color: {cor}; font-weight: 600"

        st.dataframe(
            ranking_tend[colunas].sort_values("Acima de (0-4)", ascending=False).style
                .map(colorir_acima_de, subset=["Acima de (0-4)"])
                .format({"Preco Atual (US$)": "{:.2f}", "MA20": "{:.2f}", "MA50": "{:.2f}",
                         "MA100": "{:.2f}", "MA200": "{:.2f}"}),
            use_container_width=True,
            hide_index=True,
        )

with aba_rsi:
    st.caption(
        f"RSI({periodo_rsi}) de Wilder. Acima de 70: sobrecomprado. Abaixo de 30: sobrevendido. "
        "Limiares convencionais de leitura, nao gatilhos automaticos de compra/venda."
    )
    ranking_rsi_df = tecnica.ranking_rsi(tabela_precos, universo, periodo_rsi, nomes)
    if ranking_rsi_df.empty:
        st.warning("Sem dados suficientes.")
    else:
        coluna_rsi = f"RSI ({periodo_rsi})"

        def colorir_rsi(val):
            if pd.isna(val):
                return ""
            cor = "#b3261e" if val >= 70 else ("#1b7a3d" if val <= 30 else "#404751")
            return f"color: {cor}; font-weight: 600"

        st.dataframe(
            ranking_rsi_df[["Ticker", "Nome", "Categoria", coluna_rsi, "Classificacao"]].style
                .map(colorir_rsi, subset=[coluna_rsi])
                .format({coluna_rsi: "{:.1f}"}),
            use_container_width=True,
            hide_index=True,
        )

        fig_rsi_bar = px.bar(
            ranking_rsi_df, x="Ticker", y=coluna_rsi, color="Categoria",
            hover_name="Nome", hover_data={"Subcategoria": True, "Descricao": True, "Categoria": False},
        )
        fig_rsi_bar.add_hline(y=70, line_dash="dash", line_color="#b3261e")
        fig_rsi_bar.add_hline(y=30, line_dash="dash", line_color="#1b7a3d")
        fig_rsi_bar.update_xaxes(categoryorder="array", categoryarray=ranking_rsi_df["Ticker"].tolist())
        st.plotly_chart(fig_rsi_bar, use_container_width=True)

with aba_vol_universo:
    st.caption(
        "Z-Score da volatilidade: compara a vol. anualizada recente de cada ativo com a "
        "distribuicao da propria vol. historica dele. Positivo = mais agitado que o normal "
        "para esse ativo especifico (nao entre ativos diferentes)."
    )
    ranking_vol_df = tecnica.ranking_volatilidade(tabela_precos, universo, janela_vol_curta, anos_vol_historico, nomes)
    if ranking_vol_df.empty:
        st.warning("Sem dados suficientes.")
    else:
        def colorir_vol(val):
            if pd.isna(val):
                return ""
            cor = "#b3261e" if val >= 0 else "#1b7a3d"
            return f"color: {cor}; font-weight: 600"

        st.dataframe(
            ranking_vol_df[["Ticker", "Nome", "Categoria", "Vol Atual Anualizada (%)",
                            "Vol Media Historica (%)", "Z-Score Vol"]].style
                .map(colorir_vol, subset=["Z-Score Vol"])
                .format({"Vol Atual Anualizada (%)": "{:.1f}", "Vol Media Historica (%)": "{:.1f}",
                         "Z-Score Vol": "{:.2f}"}),
            use_container_width=True,
            hide_index=True,
        )

        fig_vol_bar = px.bar(
            ranking_vol_df, x="Ticker", y="Z-Score Vol", color="Categoria",
            hover_name="Nome", hover_data={"Subcategoria": True, "Descricao": True, "Categoria": False},
        )
        fig_vol_bar.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_vol_bar.update_xaxes(categoryorder="array", categoryarray=ranking_vol_df["Ticker"].tolist())
        st.plotly_chart(fig_vol_bar, use_container_width=True)
