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
st.caption("Universo global de ativos e leitura de valor relativo — foco offshore.")

st.divider()

st.subheader("🎯 Analise Tecnica e Oportunidades ETFs")
st.write(
    "Uma unica pagina com 4 sub-abas: performance do universo de ativos (renda variavel, "
    "renda fixa por duration/credito e alternativos) e backtest de alocacoes hipoteticas; "
    "matriz de correlacao, posicao no range e ranking de z-score; medias moveis, RSI e "
    "volatilidade (Bandas de Bollinger); e um score consolidado de oportunidades cruzando "
    "valor relativo, posicao no range e momentum."
)

st.divider()
st.caption(
    "Use o menu na barra lateral para abrir a pagina. "
    "O universo de ativos padrao fica em data/universo_ativos.csv — edite esse arquivo para "
    "adicionar ou remover tickers."
)
