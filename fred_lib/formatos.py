"""Formatação de valores/variações de acordo com a unidade de cada indicador.

Cada indicador do catálogo carrega um dict "unidade" no formato:
    {"badge": "US$ milhões", "tipo": "moeda", "simbolo": "US$"}
    {"badge": "%", "tipo": "percentual"}
    {"badge": "Índice", "tipo": "numero"}

"tipo" controla como o número é formatado; "badge" é o texto curto exibido
como legenda (ex: "US$ milhões", "% do PIB", "Mil pessoas").
"""


def formatar_valor(valor: float, unidade: dict) -> str:
    tipo = unidade.get("tipo", "numero")
    if tipo == "percentual":
        return f"{valor:,.2f}%"
    if tipo == "moeda":
        simbolo = unidade.get("simbolo", "")
        return f"{simbolo} {valor:,.2f}".strip()
    return f"{valor:,.2f}"


def formatar_delta(delta: float, unidade: dict) -> str:
    """Sempre começa com '+' ou '-' explícito, pra o st.metric colorir certo
    (verde/vermelho) mesmo quando há um prefixo de moeda antes do número."""
    tipo = unidade.get("tipo", "numero")
    sinal = "+" if delta >= 0 else "-"
    valor_abs = abs(delta)
    if tipo == "percentual":
        return f"{sinal}{valor_abs:,.2f} p.p."
    if tipo == "moeda":
        simbolo = unidade.get("simbolo", "")
        return f"{sinal}{simbolo} {valor_abs:,.2f}".strip()
    return f"{sinal}{valor_abs:,.2f}"


def badge_unidade(unidade: dict) -> str:
    return unidade.get("badge", "Número")
