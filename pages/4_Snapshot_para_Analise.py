import sys
import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROJETO))

from market_lib import precos as precos_lib
from market_lib import analise
from market_lib import tecnica
from market_lib import consolidado as consolidado_lib
from market_lib import snapshot as snapshot_lib
from market_lib.estilo import aplicar_estilo
from fred_lib import client as fred_client, formatos
from fred_lib.series_catalog import listar_destaques

st.set_page_config(page_title="Snapshot para Analise", layout="wide", page_icon="📄")
aplicar_estilo()

CAMINHO_UNIVERSO = RAIZ_PROJETO / "data" / "universo_ativos.csv"
ANOS_CORRELACAO = 3
ANOS_VALOR_RELATIVO = 5
PERIODO_RSI = 14

st.title("Snapshot para Analise")
st.caption(
    "Junta o cenario macro, a performance do universo, o valor relativo (z-score/posicao no "
    "range), a analise tecnica (medias moveis/RSI) e as correlacoes num unico Markdown. Baixe e "
    "traga para uma conversa com a Claude junto com PDFs de research de outras casas, e peca a "
    "leitura de oportunidades e riscos — esta pagina so organiza os numeros, nao interpreta nada."
)

if st.button("📄 Gerar snapshot"):
    universo = precos_lib.carregar_universo(CAMINHO_UNIVERSO)
    tickers = universo["Ticker"].tolist()

    anos_busca = max(ANOS_CORRELACAO, ANOS_VALOR_RELATIVO) + 1
    data_inicio = (dt.date.today() - dt.timedelta(days=365 * anos_busca)).isoformat()

    with st.spinner("Buscando precos no Yahoo Finance..."):
        tabela_precos = precos_lib.buscar_precos(tickers, data_inicio)

    if tabela_precos.empty:
        st.error("Nao consegui buscar precos para o universo. Tente novamente em alguns minutos.")
        st.stop()

    with st.spinner("Buscando destaques macro no FRED..."):
        resumo_macro = pd.DataFrame()
        try:
            fred_client.obter_cliente()
            linhas_resumo = []
            inicio_macro = dt.date.today() - dt.timedelta(days=365 * 2)
            for s in listar_destaques():
                e_indice = s.get("tipo") == "indice"
                try:
                    serie = fred_client.buscar_serie(
                        s["id"], inicio=inicio_macro, fim=None, unidades="pc1" if e_indice else None
                    ).dropna()
                except Exception:
                    continue
                if serie.empty:
                    continue
                unidade = s.get("unidade", {})
                ultimo = serie.iloc[-1]
                anterior = serie.iloc[-2] if len(serie) > 1 else ultimo
                linhas_resumo.append({
                    "Indicador": s["nome"],
                    "Categoria": s["categoria"],
                    "Valor": formatos.formatar_valor(ultimo, unidade),
                    "Variacao": formatos.formatar_delta(ultimo - anterior, unidade),
                    "Dado de": serie.index[-1].strftime("%d/%m/%Y"),
                })
            resumo_macro = pd.DataFrame(linhas_resumo)
        except RuntimeError:
            st.warning("FRED_API_KEY nao encontrada — snapshot vai sem a secao macro.")

    with st.spinner("Calculando performance, valor relativo e correlacoes..."):
        nomes = precos_lib.buscar_nomes(tickers)
        tabela_performance = precos_lib.montar_tabela_performance(tabela_precos, universo, nomes)
        ranking_zscore = analise.ranking_zscore(tabela_precos, universo, ANOS_VALOR_RELATIVO, nomes)
        ranking_posicao = analise.ranking_posicao_no_range(tabela_precos, universo, ANOS_VALOR_RELATIVO, nomes)

        data_corte_corr = tabela_precos.index[-1] - pd.Timedelta(days=365 * ANOS_CORRELACAO)
        precos_corr = tabela_precos[tabela_precos.index >= data_corte_corr]
        tickers_com_dados = [t for t in tickers if t in precos_corr.columns and precos_corr[t].notna().sum() > 30]
        pares_correlacao = {"mais_correlacionados": pd.DataFrame(), "menos_correlacionados": pd.DataFrame()}
        if len(tickers_com_dados) >= 2:
            matriz = analise.matriz_correlacao(precos_corr, tickers_com_dados)
            pares_correlacao = analise.pares_extremos_correlacao(matriz, top_n=5)

    with st.spinner("Calculando analise tecnica (medias moveis, RSI) e consolidado..."):
        ranking_tendencia = tecnica.ranking_tendencia(tabela_precos, universo, nomes)
        ranking_rsi = tecnica.ranking_rsi(tabela_precos, universo, PERIODO_RSI, nomes)
        consolidado = consolidado_lib.montar_consolidado(
            tabela_precos, universo, nomes, ANOS_VALOR_RELATIVO, PERIODO_RSI
        )

    data_geracao = dt.date.today().strftime("%d/%m/%Y")
    texto_snapshot = snapshot_lib.montar_snapshot(
        data_geracao, resumo_macro, tabela_performance, ranking_zscore, ranking_posicao, pares_correlacao,
        ranking_tendencia, ranking_rsi, consolidado,
    )

    st.success("Snapshot gerado.")
    st.download_button(
        "⬇️ Baixar snapshot (.md)",
        data=texto_snapshot,
        file_name=f"snapshot_avin_{dt.date.today().isoformat()}.md",
        mime="text/markdown",
    )
    with st.expander("Ver conteudo do snapshot"):
        st.markdown(texto_snapshot)
else:
    st.info("Clique em 'Gerar snapshot' para montar o resumo do cenario atual.")
