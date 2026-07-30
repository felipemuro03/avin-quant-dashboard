"""Consolidado de oportunidades: cruza valor relativo (z-score/posicao no range)
com momentum (RSI) numa unica tabela, com um score simples e 100% auditavel.

IMPORTANTE sobre a lente adotada: o "Score de Reversao" premia ativos baratos
(z-score baixo) + perto do fundo do range + sobrevendidos (RSI baixo). Essa e
uma leitura de "mean reversion" (aposta de que o preco tende a voltar pra
media) — nao e a unica leitura valida. Quem segue tendencia leria a MESMA
tabela do jeito oposto (RSI alto + acima das medias = forca, nao fraqueza).
Por isso a tabela sempre mostra os componentes crus ao lado do score, para
quem usar poder discordar do peso dado a cada fator.
"""

import pandas as pd

from market_lib import analise, tecnica


def montar_consolidado(
    precos: pd.DataFrame,
    universo: pd.DataFrame,
    nomes: dict,
    anos_valor_relativo: float = 5,
    periodo_rsi: int = 14,
) -> pd.DataFrame:
    coluna_rsi = f"RSI ({periodo_rsi})"

    rz = analise.ranking_zscore(precos, universo, anos_valor_relativo, nomes)
    rz = rz[["Ticker", "Nome", "Categoria", "Subcategoria", "Descricao", "Z-Score"]]

    rp = analise.ranking_posicao_no_range(precos, universo, anos_valor_relativo, nomes)
    rp = rp[["Ticker", "Posicao (%)"]]

    rr = tecnica.ranking_rsi(precos, universo, periodo_rsi, nomes)
    rr = rr[["Ticker", coluna_rsi]].rename(columns={coluna_rsi: "RSI"})

    rt = tecnica.ranking_tendencia(precos, universo, nomes)
    rt = rt[["Ticker", "Acima de (0-4)", "Tendencia (MA50 x MA200)"]]

    rv = tecnica.ranking_volatilidade(precos, universo, nomes=nomes)
    rv = rv[["Ticker", "Z-Score Vol"]]

    df = (
        rz.merge(rp, on="Ticker", how="inner")
          .merge(rr, on="Ticker", how="inner")
          .merge(rt, on="Ticker", how="left")
          .merge(rv, on="Ticker", how="left")
    )

    if df.empty:
        return df

    df["Percentil Valor"] = (-df["Z-Score"]).rank(pct=True) * 100
    df["Percentil Range"] = (-df["Posicao (%)"]).rank(pct=True) * 100
    df["Percentil Momentum"] = (-df["RSI"]).rank(pct=True) * 100
    df["Score Reversao (0-100)"] = df[
        ["Percentil Valor", "Percentil Range", "Percentil Momentum"]
    ].mean(axis=1)

    return df.sort_values("Score Reversao (0-100)", ascending=False)
