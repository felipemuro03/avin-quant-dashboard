"""Catálogo curado dos principais indicadores econômicos dos EUA (FRED).

Nomes seguem o título oficial da série no FRED. Séries com "tipo": "indice"
são índices de base 100 (ex: CPI, PCE) — no dashboard são exibidas como
variação % em 12 meses, não como nível bruto.

"unidade" descreve como formatar valor/variação (ver fred_lib/formatos.py) e
qual selo de unidade mostrar (ex: "%", "US$ milhões", "Mil pessoas").
Unidades confirmadas direto na API do FRED (campo "units" de cada série).
"""

_PCT = {"badge": "%", "tipo": "percentual"}

CATALOGO = {
    "Crescimento": [
        {"id": "GDPC1", "nome": "Real Gross Domestic Product", "nota": "Trimestral, variação % vs. mesmo trimestre do ano anterior", "tipo": "indice", "destaque": True, "unidade": _PCT},
        {"id": "INDPRO", "nome": "Industrial Production: Total Index", "nota": "Mensal", "tipo": "indice", "unidade": _PCT},
    ],
    "Inflação": [
        {"id": "CPIAUCSL", "nome": "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average", "nota": "Mensal", "tipo": "indice", "destaque": True, "unidade": _PCT},
        {"id": "CPILFESL", "nome": "Consumer Price Index for All Urban Consumers: All Items Less Food and Energy in U.S. City Average", "nota": "Mensal (Core CPI)", "tipo": "indice", "unidade": _PCT},
        {"id": "PCEPI", "nome": "Personal Consumption Expenditures: Chain-type Price Index", "nota": "Mensal, métrica preferida do Fed", "tipo": "indice", "unidade": _PCT},
        {"id": "PCEPILFE", "nome": "Personal Consumption Expenditures Excluding Food and Energy (Chain-Type Price Index)", "nota": "Mensal (Core PCE)", "tipo": "indice", "unidade": _PCT},
    ],
    "Emprego": [
        {"id": "UNRATE", "nome": "Unemployment Rate", "nota": "Mensal, %", "destaque": True, "unidade": _PCT},
        {"id": "PAYEMS", "nome": "All Employees, Total Nonfarm", "nota": "Mensal, milhares de vagas", "unidade": {"badge": "Mil pessoas", "tipo": "numero"}},
        {"id": "ICSA", "nome": "Initial Claims", "nota": "Semanal", "unidade": {"badge": "Pessoas", "tipo": "numero"}},
        {"id": "CIVPART", "nome": "Labor Force Participation Rate", "nota": "Mensal, %", "unidade": _PCT},
    ],
    "Juros": [
        {"id": "FEDFUNDS", "nome": "Federal Funds Effective Rate", "nota": "Mensal, %", "destaque": True, "unidade": _PCT},
        {"id": "DGS10", "nome": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity", "nota": "Diário, %", "destaque": True, "unidade": _PCT},
        {"id": "DGS2", "nome": "Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity", "nota": "Diário, %", "unidade": _PCT},
        {"id": "T10Y2Y", "nome": "10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity", "nota": "Diário, indicador de curva/recessão", "unidade": _PCT},
    ],
    "Consumo": [
        {"id": "UMCSENT", "nome": "University of Michigan: Consumer Sentiment", "nota": "Mensal, nível do índice", "destaque": True, "unidade": {"badge": "Índice", "tipo": "numero"}},
        {"id": "RSAFS", "nome": "Advance Retail Sales: Retail Trade and Food Services", "nota": "Mensal", "unidade": {"badge": "US$ milhões", "tipo": "moeda", "simbolo": "US$"}},
        {"id": "PCE", "nome": "Personal Consumption Expenditures", "nota": "Mensal", "unidade": {"badge": "US$ bilhões", "tipo": "moeda", "simbolo": "US$"}},
    ],
    "Moradia": [
        {"id": "HOUST", "nome": "New Privately-Owned Housing Units Started: Total Units", "nota": "Mensal, anualizado", "unidade": {"badge": "Mil unidades", "tipo": "numero"}},
        {"id": "MORTGAGE30US", "nome": "30-Year Fixed Rate Mortgage Average in the United States", "nota": "Semanal, %", "unidade": _PCT},
        {"id": "CSUSHPISA", "nome": "S&P/Case-Shiller U.S. National Home Price Index", "nota": "Mensal", "tipo": "indice", "unidade": _PCT},
    ],
    "Mercados": [
        {"id": "SP500", "nome": "S&P 500", "nota": "Diário", "destaque": True, "unidade": {"badge": "Índice", "tipo": "numero"}},
        {"id": "M2SL", "nome": "M2", "nota": "Mensal", "unidade": {"badge": "US$ bilhões", "tipo": "moeda", "simbolo": "US$"}},
        {"id": "DTWEXBGS", "nome": "Nominal Broad U.S. Dollar Index", "nota": "Diário", "tipo": "indice", "unidade": _PCT},
    ],
}


def url_serie(series_id: str) -> str:
    return f"https://fred.stlouisfed.org/series/{series_id}"


def listar_todas_series():
    """Retorna lista achatada de todas as séries do catálogo, com categoria."""
    achatado = []
    for categoria, series in CATALOGO.items():
        for s in series:
            achatado.append({**s, "categoria": categoria})
    return achatado


def listar_destaques():
    """Retorna as séries marcadas como "destaque": True (resumo dos principais)."""
    return [s for s in listar_todas_series() if s.get("destaque")]
