import sys
from pathlib import Path

import streamlit as st

RAIZ_PROJETO = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ_PROJETO))

from market_lib.estilo import aplicar_estilo

st.set_page_config(page_title="AVIN Quant Dashboard", layout="wide", page_icon="📊")
aplicar_estilo()

caminho_logo = RAIZ_PROJETO / "assets" / "logo_avin.png"
if caminho_logo.exists():
    st.image(str(caminho_logo), width=280)

st.title("AVIN Quant Dashboard")
st.caption("Universo global de ativos, cenario macro e leitura de valor relativo — foco offshore.")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📈 Universo e Precos")
    st.write(
        "Performance do universo de ativos (renda variavel, renda fixa por duration/credito "
        "e alternativos) e backtest de alocacoes hipoteticas."
    )

with col2:
    st.subheader("🇺🇸 Cenario Macro EUA")
    st.write(
        "Crescimento, inflacao, emprego, juros e mercados — indicadores oficiais via FRED."
    )

with col3:
    st.subheader("🔗 Correlacoes e Valor Relativo")
    st.write(
        "Matriz de correlacao, posicao no range (min/media/max/atual) e ranking de z-score "
        "de preco vs. a propria historia."
    )

col4, col5, col6 = st.columns(3)

with col4:
    st.subheader("📄 Snapshot para Analise")
    st.write(
        "Exporta um Markdown com macro + performance + valor relativo + tecnica + correlacoes — "
        "para trazer numa conversa com a Claude junto com research de terceiros e pedir a "
        "leitura de oportunidades e riscos."
    )

with col5:
    st.subheader("📉 Analise Tecnica")
    st.write(
        "Medias moveis (MA20/50/100/200) e o comportamento do preco em relacao a elas, "
        "momentum (RSI) e volatilidade (regime + Bandas de Bollinger)."
    )

with col6:
    st.subheader("🎯 Oportunidades Consolidadas")
    st.write(
        "Cruza valor relativo, posicao no range e momentum num score simples e auditavel — "
        "leitura de mean reversion, com todos os componentes visiveis, nao uma caixa-preta."
    )

st.divider()
st.caption(
    "Use o menu na barra lateral para navegar entre as paginas. "
    "O universo de ativos padrao fica em data/universo_ativos.csv — edite esse arquivo para "
    "adicionar ou remover tickers."
)
