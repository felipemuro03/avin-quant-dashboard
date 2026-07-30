"""Analises cross-asset simples e transparentes: correlacao e valor relativo (z-score).

Nada de caixa-preta — so estatistica descritiva sobre a mesma base de precos
usada na pagina de performance, pra dar pra explicar o numero pra qualquer um.
"""

import numpy as np
import pandas as pd


def matriz_correlacao(precos: pd.DataFrame, tickers: list) -> pd.DataFrame:
    """Correlacao dos retornos diarios entre os ativos informados."""
    tickers_validos = [t for t in tickers if t in precos.columns]
    retornos = precos[tickers_validos].pct_change().dropna(how="all")
    return retornos.corr()


def pares_extremos_correlacao(matriz: pd.DataFrame, top_n: int = 5) -> dict:
    """Pares de ativos mais e menos correlacionados (sem repetir A-B e B-A)."""
    colunas = matriz.columns.tolist()
    pares = []
    for i in range(len(colunas)):
        for j in range(i + 1, len(colunas)):
            pares.append((colunas[i], colunas[j], matriz.iloc[i, j]))
    df = pd.DataFrame(pares, columns=["Ativo A", "Ativo B", "Correlacao"]).dropna()
    if df.empty:
        return {"mais_correlacionados": df, "menos_correlacionados": df}
    return {
        "mais_correlacionados": df.sort_values("Correlacao", ascending=False).head(top_n),
        "menos_correlacionados": df.sort_values("Correlacao").head(top_n),
    }


def zscore_valor_relativo(serie: pd.Series, anos_janela: float) -> dict:
    """Z-score do preco atual vs. media/desvio da propria serie na janela.

    Z positivo = preco acima da media historica (mais "caro" vs. a propria
    historia); Z negativo = abaixo (mais "barato"). Nao e recomendacao de
    compra/venda, e uma leitura estatistica simples.
    """
    serie = serie.dropna()
    if serie.empty:
        return {"preco_atual": np.nan, "media": np.nan, "desvio": np.nan, "zscore": np.nan}

    data_corte = serie.index[-1] - pd.Timedelta(days=int(anos_janela * 365))
    janela = serie[serie.index >= data_corte]
    if len(janela) < 30:
        return {"preco_atual": serie.iloc[-1], "media": np.nan, "desvio": np.nan, "zscore": np.nan}

    media = janela.mean()
    desvio = janela.std()
    preco_atual = serie.iloc[-1]
    zscore = (preco_atual - media) / desvio if desvio else np.nan
    return {"preco_atual": preco_atual, "media": media, "desvio": desvio, "zscore": zscore}


def ranking_zscore(precos: pd.DataFrame, universo: pd.DataFrame, anos_janela: float, nomes: dict = None) -> pd.DataFrame:
    """Ranking de valor relativo (z-score) para todo o universo, com categoria."""
    nomes = nomes or {}
    linhas = []
    for _, linha in universo.iterrows():
        ticker = linha["Ticker"]
        if ticker not in precos.columns:
            continue
        resultado = zscore_valor_relativo(precos[ticker], anos_janela)
        linhas.append(
            {
                "Ticker": ticker,
                "Nome": nomes.get(ticker, ticker),
                "Categoria": linha["Categoria"],
                "Subcategoria": linha["Subcategoria"],
                "Descricao": linha.get("Descricao", ""),
                "Preco Atual (US$)": resultado["preco_atual"],
                "Media Historica (US$)": resultado["media"],
                "Z-Score": resultado["zscore"],
            }
        )
    df = pd.DataFrame(linhas).dropna(subset=["Z-Score"])
    return df.sort_values("Z-Score")


def posicao_no_range(serie: pd.Series, anos_janela: float) -> dict:
    """Onde o preco atual esta hoje entre o minimo e o maximo da janela.

    Posicao_Pct = 0 no minimo da janela, 100 no maximo. Complementa o z-score
    de um jeito mais intuitivo de visualizar (min/media/max/atual), sem exigir
    ler um numero de desvios-padrao.
    """
    serie = serie.dropna()
    if serie.empty:
        return {"minimo": np.nan, "maximo": np.nan, "media": np.nan, "atual": np.nan, "posicao_pct": np.nan}

    data_corte = serie.index[-1] - pd.Timedelta(days=int(anos_janela * 365))
    janela = serie[serie.index >= data_corte]
    if len(janela) < 30:
        return {"minimo": np.nan, "maximo": np.nan, "media": np.nan, "atual": serie.iloc[-1], "posicao_pct": np.nan}

    minimo = janela.min()
    maximo = janela.max()
    media = janela.mean()
    atual = serie.iloc[-1]
    posicao_pct = (atual - minimo) / (maximo - minimo) * 100 if maximo > minimo else np.nan
    return {"minimo": minimo, "maximo": maximo, "media": media, "atual": atual, "posicao_pct": posicao_pct}


def cor_posicao(pct: float) -> str:
    """Interpola verde (barato, perto do minimo) -> vermelho (caro, perto do maximo)."""
    if pd.isna(pct):
        return "#404751"
    t = max(0.0, min(1.0, pct / 100))
    verde = (27, 122, 61)
    vermelho = (179, 38, 30)
    r = round(verde[0] + (vermelho[0] - verde[0]) * t)
    g = round(verde[1] + (vermelho[1] - verde[1]) * t)
    b = round(verde[2] + (vermelho[2] - verde[2]) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def ranking_posicao_no_range(precos: pd.DataFrame, universo: pd.DataFrame, anos_janela: float, nomes: dict = None) -> pd.DataFrame:
    """Posicao no range (min/media/max/atual) para todo o universo, com categoria."""
    nomes = nomes or {}
    linhas = []
    for _, linha in universo.iterrows():
        ticker = linha["Ticker"]
        if ticker not in precos.columns:
            continue
        resultado = posicao_no_range(precos[ticker], anos_janela)
        linhas.append(
            {
                "Ticker": ticker,
                "Nome": nomes.get(ticker, ticker),
                "Categoria": linha["Categoria"],
                "Subcategoria": linha["Subcategoria"],
                "Descricao": linha.get("Descricao", ""),
                "Minimo (US$)": resultado["minimo"],
                "Media (US$)": resultado["media"],
                "Maximo (US$)": resultado["maximo"],
                "Atual (US$)": resultado["atual"],
                "Posicao (%)": resultado["posicao_pct"],
            }
        )
    df = pd.DataFrame(linhas).dropna(subset=["Posicao (%)"])
    return df.sort_values("Posicao (%)")
