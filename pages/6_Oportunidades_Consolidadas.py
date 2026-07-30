import sys
import datetime as dt
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROJETO))

from market_lib import precos as precos_lib
from market_lib import consolidado as consolidado_lib
from market_lib.estilo import aplicar_estilo

st.set_page_config(page_title="Oportunidades Consolidadas", layout="wide", page_icon="🎯")
aplicar_estilo()

CAMINHO_UNIVERSO = RAIZ_PROJETO / "data" / "universo_ativos.csv"

st.title("Oportunidades Consolidadas")
st.caption(
    "Cruza valor relativo (z-score + posicao no range) com momentum (RSI) numa unica tabela, "
    "com um score simples e auditavel — nao e caixa-preta e nao e recomendacao de compra/venda."
)

with st.expander("Como ler o Score de Reversao (leia antes de usar)", expanded=True):
    st.markdown(
        "O **Score de Reversao (0-100)** e a media de 3 percentis, calculados dentro do "
        "universo filtrado:\n\n"
        "- **Percentil Valor**: quao barato o ativo esta vs. a propria historia (z-score baixo → percentil alto)\n"
        "- **Percentil Range**: quao perto do fundo do range de preco ele esta (posicao baixa → percentil alto)\n"
        "- **Percentil Momentum**: quao sobrevendido ele esta pelo RSI (RSI baixo → percentil alto)\n\n"
        "Isso e uma leitura de **mean reversion** (aposta estatistica de que preco muito "
        "esticado tende a voltar pra media) — **nao e a unica leitura valida**. Quem segue "
        "tendencia leria a mesma tabela ao contrario (RSI alto + acima das medias = forca). "
        "Por isso todos os componentes crus ficam visiveis ao lado do score, e as colunas de "
        "tendencia/volatilidade ficam disponiveis para voce julgar o contexto, nao so o numero final."
    )

universo_base = precos_lib.carregar_universo(CAMINHO_UNIVERSO)

st.sidebar.header("Filtros")
categorias_disponiveis = sorted(universo_base["Categoria"].unique().tolist())
categorias_selecionadas = st.sidebar.multiselect(
    "Categorias", categorias_disponiveis, default=categorias_disponiveis
)

anos_valor_relativo = st.sidebar.slider("Janela de valor relativo (anos)", 1, 15, 5)
periodo_rsi = st.sidebar.slider("Periodo do RSI", 5, 30, 14)

universo = universo_base[universo_base["Categoria"].isin(categorias_selecionadas)].copy()

if universo.empty:
    st.info("Selecione ao menos uma categoria na barra lateral.")
    st.stop()

tickers = universo["Ticker"].tolist()
anos_busca = anos_valor_relativo + 1
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

consolidado = consolidado_lib.montar_consolidado(tabela_precos, universo, nomes, anos_valor_relativo, periodo_rsi)

if consolidado.empty:
    st.warning("Sem dados suficientes para montar o consolidado nesta janela/filtro.")
    st.stop()

st.header("Ranking — Score de Reversao")

def colorir_score(val):
    if pd.isna(val):
        return ""
    t = val / 100
    r = round(27 + (179 - 27) * t)
    g = round(122 + (38 - 122) * t)
    b = round(61 + (30 - 61) * t)
    return f"color: #{r:02x}{g:02x}{b:02x}; font-weight: 700"

colunas_tabela = [
    "Ticker", "Nome", "Categoria", "Subcategoria", "Score Reversao (0-100)",
    "Z-Score", "Posicao (%)", "RSI", "Acima de (0-4)", "Tendencia (MA50 x MA200)", "Z-Score Vol",
]

st.dataframe(
    consolidado[colunas_tabela].style
        .map(colorir_score, subset=["Score Reversao (0-100)"])
        .format({
            "Score Reversao (0-100)": "{:.0f}",
            "Z-Score": "{:.2f}",
            "Posicao (%)": "{:.0f}",
            "RSI": "{:.1f}",
            "Z-Score Vol": "{:.2f}",
        }),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Score de Reversao por ativo")
fig_score = px.bar(
    consolidado, x="Ticker", y="Score Reversao (0-100)", color="Categoria",
    hover_name="Nome", hover_data={"Subcategoria": True, "Descricao": True, "Categoria": False},
)
fig_score.update_xaxes(categoryorder="array", categoryarray=consolidado["Ticker"].tolist())
st.plotly_chart(fig_score, use_container_width=True)

st.divider()

col_top, col_bottom = st.columns(2)
with col_top:
    st.subheader("Setups de reversao mais fortes (nesta leitura)")
    top5 = consolidado.head(5)[["Ticker", "Nome", "Score Reversao (0-100)", "Z-Score", "Posicao (%)", "RSI"]]
    st.dataframe(top5, use_container_width=True, hide_index=True)

with col_bottom:
    st.subheader("Mais esticados para o outro lado")
    bottom5 = consolidado.tail(5)[["Ticker", "Nome", "Score Reversao (0-100)", "Z-Score", "Posicao (%)", "RSI"]]
    st.dataframe(bottom5, use_container_width=True, hide_index=True)

st.caption(
    "Leitura puramente estatistica sobre preco — nao considera fundamento, fluxo, catalisadores "
    "ou cenario macro. Cruze com a pagina de Cenario Macro e com o Snapshot para Analise antes "
    "de qualquer decisao."
)
