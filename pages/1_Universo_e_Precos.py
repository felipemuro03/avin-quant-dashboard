import sys
import io
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
from market_lib.estilo import aplicar_estilo

st.set_page_config(page_title="Universo e Precos", layout="wide", page_icon="📈")
aplicar_estilo()

CAMINHO_UNIVERSO = RAIZ_PROJETO / "data" / "universo_ativos.csv"

st.title("Universo e Precos")
st.caption("Performance do universo de ativos e backtest de alocacoes hipoteticas.")

universo_base = precos_lib.carregar_universo(CAMINHO_UNIVERSO)

# ---------- 1. Filtro de categoria + tickers extras ----------
st.sidebar.header("1. Universo de ativos")

categorias_disponiveis = sorted(universo_base["Categoria"].unique().tolist())
categorias_selecionadas = st.sidebar.multiselect(
    "Categorias", categorias_disponiveis, default=categorias_disponiveis
)

st.sidebar.caption(
    f"Universo padrao: {len(universo_base)} ativos (editavel em data/universo_ativos.csv)"
)

with st.sidebar.expander("➕ Adicionar tickers extras (opcional)"):

    def modelo_excel_bytes():
        modelo = pd.DataFrame({"Ticker": ["AAPL", "MSFT"]})
        buffer = io.BytesIO()
        modelo.to_excel(buffer, index=False)
        return buffer.getvalue()

    st.download_button(
        "⬇️ Baixar modelo de planilha",
        data=modelo_excel_bytes(),
        file_name="modelo_ativos_extras.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    arquivo_extra = st.file_uploader("Subir planilha de tickers extras (.xlsx)", type=["xlsx"])

universo = universo_base[universo_base["Categoria"].isin(categorias_selecionadas)].copy()

if arquivo_extra is not None:
    extra = pd.read_excel(arquivo_extra)
    extra.columns = [str(c).strip() for c in extra.columns]
    col_ticker = None
    for candidato in ["Ticker", "Nome do Produto", "Produto", "Ativo"]:
        if candidato in extra.columns:
            col_ticker = candidato
            break
    if col_ticker is None:
        st.sidebar.error("A planilha extra precisa ter uma coluna 'Ticker'.")
    else:
        extra = extra.rename(columns={col_ticker: "Ticker"})
        extra["Ticker"] = extra["Ticker"].astype(str).str.strip().str.upper()
        extra = extra.dropna(subset=["Ticker"])
        extra = extra[~extra["Ticker"].isin(universo["Ticker"])]
        for coluna in ["Categoria", "Subcategoria", "Duration_Bucket", "Descricao"]:
            if coluna not in extra.columns:
                extra[coluna] = "Extra" if coluna == "Categoria" else "-"
        universo = pd.concat([universo, extra[universo.columns]], ignore_index=True)

universo = universo.drop_duplicates(subset="Ticker").reset_index(drop=True)

if universo.empty:
    st.info("Selecione ao menos uma categoria na barra lateral.")
    st.stop()

# ---------- 2. Backtest: configuracao ----------
st.sidebar.header("2. Backtest")
tickers_disponiveis = sorted(universo["Ticker"].unique().tolist())
tickers_backtest = st.sidebar.multiselect(
    "Ativos para o backtest (escolha os que quiser incluir)",
    tickers_disponiveis,
    default=[],
)

periodo_opcoes = {"YTD (Ano atual)": None, "1 ano": 365, "2 anos": 730}
periodo_label = st.sidebar.selectbox("Periodo do backtest (grafico)", list(periodo_opcoes.keys()), index=1)

if periodo_label == "YTD (Ano atual)":
    dias_historico = (dt.date.today() - dt.date(dt.date.today().year, 1, 1)).days
else:
    dias_historico = periodo_opcoes[periodo_label]

benchmark = st.sidebar.text_input("Ticker de benchmark (comparacao)", value="SPY").strip().upper()

# ---------- 3. Buscar precos de todo o universo ----------
dias_busca = max(dias_historico, 400)
data_inicio = (dt.date.today() - dt.timedelta(days=dias_busca)).isoformat()


@st.cache_data(ttl=3600, show_spinner="Buscando precos no Yahoo Finance...")
def _buscar_precos_cache(tickers, data_inicio):
    return precos_lib.buscar_precos(tickers, data_inicio)


@st.cache_data(ttl=86400, show_spinner=False)
def _buscar_nomes_cache(tickers):
    return precos_lib.buscar_nomes(tickers)


todos_tickers = sorted(set(universo["Ticker"].tolist() + ([benchmark] if benchmark else [])))
tabela_precos = _buscar_precos_cache(todos_tickers, data_inicio)

if tabela_precos.empty:
    st.error("Nao consegui buscar precos para esses tickers. Confira se os codigos estao corretos.")
    st.stop()

nomes_ativos = _buscar_nomes_cache(tuple(universo["Ticker"].tolist()))

# ======================================================================
# PARTE DE CIMA — Performance de todos os ativos do universo
# ======================================================================
st.header("Performance dos ativos")

col1, col2, col3 = st.columns(3)
col1.metric("Nº de ativos no universo", len(universo))
col2.metric("Categorias selecionadas", len(categorias_selecionadas))
col3.metric("Benchmark", benchmark or "-")

tabela = precos_lib.montar_tabela_performance(tabela_precos, universo, nomes_ativos)

if tabela.empty:
    st.warning("Nenhum preco encontrado para os ativos do universo selecionado.")
    st.stop()

colunas_variacao = ["Variacao 1 Semana (%)", "Variacao 1 Mes (%)", "Variacao YTD (%)", "Variacao 1 Ano (%)"]


def colorir_variacao(val):
    if pd.isna(val):
        return ""
    cor = "#1b7a3d" if val >= 0 else "#b3261e"
    return f"color: {cor}; font-weight: 600"


st.dataframe(
    tabela.style
        .map(colorir_variacao, subset=colunas_variacao)
        .format({
            "Preco Atual (US$)": "{:.2f}",
            **{c: "{:.2f}" for c in colunas_variacao},
        }),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Ranking de variacao (menor → maior)")
periodo_grafico = st.radio("Ver variacao de:", colunas_variacao, horizontal=True, index=1)
tabela_ordenada = tabela.sort_values(periodo_grafico)
fig_var = px.bar(
    tabela_ordenada,
    x="Ticker", y=periodo_grafico,
    color="Categoria",
    hover_name="Nome",
    hover_data={"Subcategoria": True, "Descricao": True, "Categoria": False},
)
fig_var.update_layout(yaxis_tickformat=".2f")
fig_var.update_xaxes(categoryorder="array", categoryarray=tabela_ordenada["Ticker"].tolist())
st.plotly_chart(fig_var, use_container_width=True)

st.divider()

# ======================================================================
# PARTE DE BAIXO — Backtest de uma alocacao escolhida
# ======================================================================
st.header("Backtest de alocacao")

if not tickers_backtest:
    st.info("Selecione ao menos um ativo em '2. Backtest', na barra lateral, para montar a simulacao.")
else:
    st.caption(
        "Ajuste o peso (%) de cada ativo para simular diferentes alocacoes — util para estudar carteiras futuras. "
        "Por padrao, todos comecam com peso igual."
    )

    peso_padrao = round(100 / len(tickers_backtest), 2)
    tabela_pesos = pd.DataFrame({"Ticker": tickers_backtest, "Peso (%)": peso_padrao})

    pesos_editados = st.data_editor(
        tabela_pesos,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Peso (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.01, format="%.2f"),
        },
    )

    soma_pesos = pesos_editados["Peso (%)"].sum()
    if soma_pesos == 0:
        st.warning("A soma dos pesos esta zerada — ajuste a alocacao acima.")
    else:
        st.caption(f"Soma atual dos pesos: {soma_pesos:.2f}% (nao precisa ser exatamente 100% — o app normaliza automaticamente)")

        pesos = pesos_editados.set_index("Ticker")["Peso (%)"] / soma_pesos

        tabela_backtest = tabela[tabela["Ticker"].isin(tickers_backtest)].copy()
        tabela_backtest["Peso (%)"] = tabela_backtest["Ticker"].map(pesos) * 100

        st.subheader("Alocacao definida")
        fig_alocacao = px.pie(
            tabela_backtest, names="Ticker", values="Peso (%)", hole=0.4,
            hover_name="Nome", hover_data={"Descricao": True},
        )
        st.plotly_chart(fig_alocacao, use_container_width=True)

        st.subheader(f"Evolucao da alocacao hipotetica ({periodo_label})")

        data_corte = tabela_precos.index[-1] - pd.Timedelta(days=dias_historico)
        precos_periodo = tabela_precos[tabela_precos.index >= data_corte]

        tickers_validos = [t for t in tickers_backtest if t in precos_periodo.columns]
        precos_carteira = precos_periodo[tickers_validos].dropna(how="all").ffill().dropna()

        if precos_carteira.empty:
            st.warning("Nao ha dados suficientes no periodo escolhido para montar o backtest.")
        else:
            pesos_alinhados = pesos.reindex(precos_carteira.columns).fillna(0)
            precos_normalizados = precos_carteira / precos_carteira.iloc[0]
            indice_por_ativo = precos_normalizados.mul(pesos_alinhados, axis=1)
            indice_carteira = indice_por_ativo.sum(axis=1)
            retorno_carteira = (indice_carteira - 1) * 100

            fig_backtest = go.Figure()
            fig_backtest.add_trace(go.Scatter(x=retorno_carteira.index, y=retorno_carteira.values, name="Alocacao (%)"))

            if benchmark and benchmark in precos_periodo.columns:
                serie_bench = precos_periodo[benchmark].dropna()
                serie_bench = serie_bench[serie_bench.index >= precos_carteira.index[0]]
                if not serie_bench.empty:
                    retorno_bench = (serie_bench / serie_bench.iloc[0] - 1) * 100
                    fig_backtest.add_trace(go.Scatter(
                        x=retorno_bench.index, y=retorno_bench.values, name=f"Benchmark ({benchmark})",
                    ))

            fig_backtest.update_layout(
                yaxis_title="Retorno acumulado (%)", xaxis_title="Data", legend_title="Serie", yaxis_tickformat=".2f",
            )
            st.plotly_chart(fig_backtest, use_container_width=True)

            retorno_total = retorno_carteira.iloc[-1]

            retornos_diarios = indice_carteira.pct_change().dropna()
            volatilidade = retornos_diarios.std() * np.sqrt(252) * 100

            pico = indice_carteira.cummax()
            drawdown = (indice_carteira / pico - 1) * 100
            max_drawdown = drawdown.min()

            col_ret, col_vol, col_dd = st.columns(3)
            col_ret.metric(f"Retorno da alocacao ({periodo_label})", f"{retorno_total:.2f}%")
            col_vol.metric("Volatilidade anualizada", f"{volatilidade:.2f}%")
            col_dd.metric("Maximo Drawdown", f"{max_drawdown:.2f}%")

            st.subheader("Contribuicao de cada ativo para o resultado")

            contribuicao = (indice_por_ativo.iloc[-1] - pesos_alinhados) * 100
            tabela_contribuicao = contribuicao.rename("Contribuicao (p.p.)").reset_index()
            tabela_contribuicao.columns = ["Ticker", "Contribuicao (p.p.)"]
            tabela_contribuicao = tabela_contribuicao.merge(
                tabela_backtest[["Ticker", "Nome"]], on="Ticker", how="left"
            ).sort_values("Contribuicao (p.p.)")

            fig_contribuicao = px.bar(
                tabela_contribuicao,
                x="Ticker", y="Contribuicao (p.p.)",
                color="Contribuicao (p.p.)",
                color_continuous_scale=["#b3261e", "#dddddd", "#1b7a3d"],
                hover_name="Nome",
            )
            fig_contribuicao.update_layout(yaxis_tickformat=".2f")
            fig_contribuicao.update_xaxes(categoryorder="array", categoryarray=tabela_contribuicao["Ticker"].tolist())
            st.plotly_chart(fig_contribuicao, use_container_width=True)
            st.caption("A soma das contribuicoes de todos os ativos bate com o retorno total da alocacao, acima.")

    st.caption(
        "Backtest de estudo: simula um investimento hipotetico seguindo os pesos definidos acima, "
        "mantidos constantes ao longo do periodo (sem rebalanceamento). "
        "Nao considera custos ou impostos (dividendos ja entram no preco, pois os precos sao ajustados)."
    )
