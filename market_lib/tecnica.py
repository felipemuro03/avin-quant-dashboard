"""Analise tecnica simples e transparente: medias moveis, momentum (RSI) e
volatilidade (regime + Bandas de Bollinger).

Mesma filosofia do resto do projeto — formulas classicas e documentadas,
nada de biblioteca de caixa-preta. Serve para descrever o comportamento do
preco, nao para prever ou recomendar.
"""

import numpy as np
import pandas as pd

JANELAS_MEDIAS = (20, 50, 100, 200)


# ======================================================================
# Medias moveis e estrutura de tendencia
# ======================================================================

def medias_moveis(serie: pd.Series) -> pd.DataFrame:
    """DataFrame com o preco e as medias moveis simples (MA20/50/100/200)."""
    serie = serie.dropna()
    df = pd.DataFrame({"Preco": serie})
    for janela in JANELAS_MEDIAS:
        df[f"MA{janela}"] = serie.rolling(janela).mean()
    return df


def estrutura_tendencia(serie: pd.Series, dias_cruzamento: int = 10) -> dict:
    """Le o comportamento do preco atual em relacao as medias moveis.

    "acima_de": em quantas das 4 medias (0 a 4) o preco atual esta acima —
    4 = alinhamento de alta (preco > todas as medias), 0 = alinhamento de
    baixa. "tendencia" compara MA50 x MA200 (golden/death cross classico).
    "cruzamento_recente" avisa se esse cruzamento aconteceu nos ultimos
    "dias_cruzamento" pregoes (nao so o estado atual, o evento em si).
    """
    df = medias_moveis(serie)
    if df.empty:
        return {"atual": np.nan, "MA20": np.nan, "MA50": np.nan, "MA100": np.nan, "MA200": np.nan,
                "acima_de": np.nan, "tendencia": "Indisponivel", "cruzamento_recente": False}

    atual = df["Preco"].iloc[-1]
    valores_ma = {f"MA{j}": df[f"MA{j}"].iloc[-1] for j in JANELAS_MEDIAS}
    acima_de = sum(1 for v in valores_ma.values() if pd.notna(v) and atual > v)

    ma50, ma200 = valores_ma["MA50"], valores_ma["MA200"]
    if pd.isna(ma50) or pd.isna(ma200):
        tendencia = "Indisponivel (historico curto)"
        cruzamento_recente = False
    else:
        tendencia = "Alta (Golden Cross vigente)" if ma50 > ma200 else "Baixa (Death Cross vigente)"
        diff_serie = (df["MA50"] - df["MA200"]).dropna()
        cruzamento_recente = False
        if len(diff_serie) > dias_cruzamento:
            recorte = np.sign(diff_serie.tail(dias_cruzamento + 1))
            cruzamento_recente = bool(recorte.iloc[0] != 0 and recorte.iloc[0] != recorte.iloc[-1])

    return {"atual": atual, **valores_ma, "acima_de": acima_de, "tendencia": tendencia,
            "cruzamento_recente": cruzamento_recente}


def ranking_tendencia(precos: pd.DataFrame, universo: pd.DataFrame, nomes: dict = None) -> pd.DataFrame:
    nomes = nomes or {}
    linhas = []
    for _, linha in universo.iterrows():
        ticker = linha["Ticker"]
        if ticker not in precos.columns:
            continue
        r = estrutura_tendencia(precos[ticker])
        linhas.append({
            "Ticker": ticker,
            "Nome": nomes.get(ticker, ticker),
            "Categoria": linha["Categoria"],
            "Subcategoria": linha["Subcategoria"],
            "Descricao": linha.get("Descricao", ""),
            "Preco Atual (US$)": r["atual"],
            "MA20": r["MA20"], "MA50": r["MA50"], "MA100": r["MA100"], "MA200": r["MA200"],
            "Acima de (0-4)": r["acima_de"],
            "Tendencia (MA50 x MA200)": r["tendencia"],
            "Cruzamento recente": "Sim" if r["cruzamento_recente"] else "Nao",
        })
    return pd.DataFrame(linhas)


# ======================================================================
# Momentum — RSI (Wilder, periodo padrao 14)
# ======================================================================

def rsi(serie: pd.Series, periodo: int = 14) -> pd.Series:
    """RSI classico de Wilder. 0-100; >70 sobrecomprado, <30 sobrevendido
    (limiares convencionais, nao gatilhos automaticos)."""
    serie = serie.dropna()
    delta = serie.diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)
    media_ganho = ganho.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()
    media_perda = perda.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()
    rs = media_ganho / media_perda
    return 100 - (100 / (1 + rs))


def classificar_rsi(valor: float) -> str:
    if pd.isna(valor):
        return "-"
    if valor >= 70:
        return "Sobrecomprado"
    if valor <= 30:
        return "Sobrevendido"
    return "Neutro"


def ranking_rsi(precos: pd.DataFrame, universo: pd.DataFrame, periodo: int = 14, nomes: dict = None) -> pd.DataFrame:
    nomes = nomes or {}
    linhas = []
    for _, linha in universo.iterrows():
        ticker = linha["Ticker"]
        if ticker not in precos.columns:
            continue
        serie_rsi = rsi(precos[ticker], periodo).dropna()
        if serie_rsi.empty:
            continue
        valor = serie_rsi.iloc[-1]
        linhas.append({
            "Ticker": ticker,
            "Nome": nomes.get(ticker, ticker),
            "Categoria": linha["Categoria"],
            "Subcategoria": linha["Subcategoria"],
            "Descricao": linha.get("Descricao", ""),
            f"RSI ({periodo})": valor,
            "Classificacao": classificar_rsi(valor),
        })
    df = pd.DataFrame(linhas)
    return df.sort_values(f"RSI ({periodo})") if not df.empty else df


# ======================================================================
# Volatilidade — regime (z-score da vol) e Bandas de Bollinger
# ======================================================================

def volatilidade_anualizada(serie: pd.Series, janela: int = 20) -> pd.Series:
    """Volatilidade anualizada (desvio-padrao dos retornos diarios x sqrt(252))
    numa janela movel — mesma formula usada no backtest da pagina 1."""
    retornos = serie.dropna().pct_change()
    return retornos.rolling(janela).std() * np.sqrt(252) * 100


def regime_volatilidade(serie: pd.Series, janela_curta: int = 20, anos_janela_historica: float = 3) -> dict:
    """Compara a vol anualizada recente com a distribuicao da propria vol do
    ativo — mesma logica do z-score de preco, aplicada a volatilidade.
    Z positivo = ativo mais agitado que o normal para ele; negativo = mais
    calmo que o normal."""
    vol_serie = volatilidade_anualizada(serie, janela_curta).dropna()
    if vol_serie.empty:
        return {"vol_atual": np.nan, "vol_media_historica": np.nan, "zscore_vol": np.nan}

    data_corte = vol_serie.index[-1] - pd.Timedelta(days=int(anos_janela_historica * 365))
    janela_hist = vol_serie[vol_serie.index >= data_corte]
    if len(janela_hist) < 30:
        return {"vol_atual": vol_serie.iloc[-1], "vol_media_historica": np.nan, "zscore_vol": np.nan}

    vol_atual = vol_serie.iloc[-1]
    media_hist = janela_hist.mean()
    desvio_hist = janela_hist.std()
    zscore_vol = (vol_atual - media_hist) / desvio_hist if desvio_hist else np.nan
    return {"vol_atual": vol_atual, "vol_media_historica": media_hist, "zscore_vol": zscore_vol}


def ranking_volatilidade(precos: pd.DataFrame, universo: pd.DataFrame, janela_curta: int = 20,
                          anos_janela_historica: float = 3, nomes: dict = None) -> pd.DataFrame:
    nomes = nomes or {}
    linhas = []
    for _, linha in universo.iterrows():
        ticker = linha["Ticker"]
        if ticker not in precos.columns:
            continue
        r = regime_volatilidade(precos[ticker], janela_curta, anos_janela_historica)
        linhas.append({
            "Ticker": ticker,
            "Nome": nomes.get(ticker, ticker),
            "Categoria": linha["Categoria"],
            "Subcategoria": linha["Subcategoria"],
            "Descricao": linha.get("Descricao", ""),
            "Vol Atual Anualizada (%)": r["vol_atual"],
            "Vol Media Historica (%)": r["vol_media_historica"],
            "Z-Score Vol": r["zscore_vol"],
        })
    df = pd.DataFrame(linhas).dropna(subset=["Z-Score Vol"])
    return df.sort_values("Z-Score Vol", ascending=False) if not df.empty else df


def bandas_bollinger(serie: pd.Series, janela: int = 20, n_desvios: float = 2) -> pd.DataFrame:
    """Bandas de Bollinger: media movel +/- N desvios-padrao moveis.
    Pct_B: onde o preco esta entre as bandas (0 = banda inferior, 100 = banda
    superior; pode passar de 0/100 quando rompe a banda)."""
    serie = serie.dropna()
    media = serie.rolling(janela).mean()
    desvio = serie.rolling(janela).std()
    banda_superior = media + n_desvios * desvio
    banda_inferior = media - n_desvios * desvio
    pct_b = (serie - banda_inferior) / (banda_superior - banda_inferior) * 100
    return pd.DataFrame({
        "Preco": serie,
        "Media": media,
        "Banda_Superior": banda_superior,
        "Banda_Inferior": banda_inferior,
        "Pct_B": pct_b,
    })
