import os
from pathlib import Path

from dotenv import load_dotenv
from fredapi import Fred

_RAIZ_PROJETO = Path(__file__).resolve().parents[1]
load_dotenv(_RAIZ_PROJETO / ".env")

_fred = None


def _obter_chave() -> str:
    chave = os.getenv("FRED_API_KEY")
    if chave:
        return chave
    try:
        import streamlit as st

        return st.secrets.get("FRED_API_KEY")
    except Exception:
        return None


def obter_cliente():
    global _fred
    if _fred is None:
        chave = _obter_chave()
        if not chave:
            raise RuntimeError(
                "FRED_API_KEY não encontrada. Localmente, verifique o arquivo .env na raiz "
                "do projeto. No Streamlit Cloud, configure em Settings > Secrets."
            )
        _fred = Fred(api_key=chave)
    return _fred


def buscar_serie(series_id: str, inicio=None, fim=None, unidades: str = None):
    """Retorna uma pandas Series com o histórico da série do FRED.

    unidades: transformação nativa do FRED (ex: "pc1" = variação % vs. 12 meses
    atrás). None = valor bruto ("lin"). Ver documentação da API do FRED,
    parâmetro "units", para as opções completas.
    """
    fred = obter_cliente()
    kwargs = {"units": unidades} if unidades else {}
    return fred.get_series(series_id, observation_start=inicio, observation_end=fim, **kwargs)


def buscar_info_serie(series_id: str) -> dict:
    """Retorna metadados da série (título, unidade, frequência, notas)."""
    fred = obter_cliente()
    info = fred.get_series_info(series_id)
    return info.to_dict()


def pesquisar_series(termo: str, limite: int = 20):
    """Pesquisa séries do FRED por palavra-chave. Retorna um DataFrame."""
    fred = obter_cliente()
    resultado = fred.search(termo, order_by="popularity", sort_order="desc")
    if resultado is None or resultado.empty:
        return resultado
    return resultado.head(limite)
