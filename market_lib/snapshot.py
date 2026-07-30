"""Monta o snapshot em Markdown (macro + performance + valor relativo + correlacoes)
para o usuario baixar e trazer para uma conversa com a Claude, junto com PDFs de
research de outras casas, e pedir a leitura de oportunidades/riscos.

Esta camada nao chama nenhuma API de IA — so organiza os numeros que o resto do
dashboard ja calcula, num texto facil de colar/anexar numa conversa.
"""

import pandas as pd


def tabela_para_markdown(df: pd.DataFrame, formato: dict = None) -> str:
    """Converte um DataFrame numa tabela Markdown simples, sem depender de 'tabulate'."""
    formato = formato or {}
    colunas = df.columns.tolist()
    linhas = ["| " + " | ".join(colunas) + " |", "| " + " | ".join(["---"] * len(colunas)) + " |"]
    for _, linha in df.iterrows():
        valores = []
        for coluna in colunas:
            valor = linha[coluna]
            if coluna in formato and pd.notna(valor):
                valores.append(formato[coluna].format(valor))
            else:
                valores.append("-" if pd.isna(valor) else str(valor))
        linhas.append("| " + " | ".join(valores) + " |")
    return "\n".join(linhas)


def montar_snapshot(
    data_geracao: str,
    resumo_macro: pd.DataFrame,
    tabela_performance: pd.DataFrame,
    ranking_zscore: pd.DataFrame,
    ranking_posicao: pd.DataFrame,
    pares_correlacao: dict,
    ranking_tendencia: pd.DataFrame = None,
    ranking_rsi: pd.DataFrame = None,
    consolidado: pd.DataFrame = None,
) -> str:
    partes = [
        f"# Snapshot AVIN Quant — {data_geracao}",
        "",
        "Dados brutos do dashboard (sem interpretacao) — para analise de cenario, "
        "oportunidades/riscos e cruzamento com research de terceiros.",
        "",
        "## Cenario macro EUA (destaques)",
    ]

    if resumo_macro.empty:
        partes.append("_Sem dados macro disponiveis neste snapshot (FRED indisponivel)._")
    else:
        partes.append(tabela_para_markdown(resumo_macro))

    partes += ["", "## Performance do universo de ativos", ""]
    if tabela_performance.empty:
        partes.append("_Sem dados de performance._")
    else:
        colunas = ["Ticker", "Nome", "Categoria", "Subcategoria", "Variacao 1 Semana (%)",
                   "Variacao 1 Mes (%)", "Variacao YTD (%)", "Variacao 1 Ano (%)"]
        formato = {c: "{:.2f}" for c in colunas if "%" in c}
        partes.append(tabela_para_markdown(tabela_performance[colunas], formato))

    partes += ["", "## Valor relativo (z-score vs. propria historia)", ""]
    if ranking_zscore.empty:
        partes.append("_Sem dados suficientes para z-score._")
    else:
        colunas_zscore = ["Ticker", "Nome", "Categoria", "Subcategoria", "Preco Atual (US$)",
                          "Media Historica (US$)", "Z-Score"]
        formato = {"Preco Atual (US$)": "{:.2f}", "Media Historica (US$)": "{:.2f}", "Z-Score": "{:.2f}"}
        partes.append(tabela_para_markdown(ranking_zscore[colunas_zscore], formato))

    partes += ["", "## Posicao no range (min/media/max/atual)", ""]
    if ranking_posicao.empty:
        partes.append("_Sem dados suficientes para posicao no range._")
    else:
        colunas = ["Ticker", "Nome", "Categoria", "Subcategoria", "Minimo (US$)", "Media (US$)", "Maximo (US$)",
                   "Atual (US$)", "Posicao (%)"]
        formato = {"Minimo (US$)": "{:.2f}", "Media (US$)": "{:.2f}", "Maximo (US$)": "{:.2f}",
                   "Atual (US$)": "{:.2f}", "Posicao (%)": "{:.0f}"}
        partes.append(tabela_para_markdown(ranking_posicao[colunas], formato))

    partes += ["", "## Correlacoes — pares extremos", ""]
    mais = pares_correlacao.get("mais_correlacionados", pd.DataFrame())
    menos = pares_correlacao.get("menos_correlacionados", pd.DataFrame())
    if mais.empty and menos.empty:
        partes.append("_Sem dados suficientes para correlacao._")
    else:
        partes.append("**Mais correlacionados** (tendem a se mover juntos):")
        partes.append(tabela_para_markdown(mais, {"Correlacao": "{:.2f}"}))
        partes.append("")
        partes.append("**Menos correlacionados / mais diversificadores:**")
        partes.append(tabela_para_markdown(menos, {"Correlacao": "{:.2f}"}))

    if ranking_tendencia is not None:
        partes += ["", "## Estrutura de tendencia (medias moveis)", ""]
        if ranking_tendencia.empty:
            partes.append("_Sem dados suficientes para estrutura de tendencia._")
        else:
            colunas = ["Ticker", "Nome", "Categoria", "Preco Atual (US$)", "MA20", "MA50", "MA100", "MA200",
                       "Acima de (0-4)", "Tendencia (MA50 x MA200)", "Cruzamento recente"]
            formato = {c: "{:.2f}" for c in ["Preco Atual (US$)", "MA20", "MA50", "MA100", "MA200"]}
            partes.append(tabela_para_markdown(ranking_tendencia[colunas], formato))

    if ranking_rsi is not None:
        partes += ["", "## Momentum (RSI)", ""]
        if ranking_rsi.empty:
            partes.append("_Sem dados suficientes para RSI._")
        else:
            coluna_rsi = [c for c in ranking_rsi.columns if c.startswith("RSI")][0]
            colunas = ["Ticker", "Nome", "Categoria", coluna_rsi, "Classificacao"]
            partes.append(tabela_para_markdown(ranking_rsi[colunas], {coluna_rsi: "{:.1f}"}))

    if consolidado is not None:
        partes += ["", "## Score de Reversao consolidado (valor + range + momentum)", ""]
        if consolidado.empty:
            partes.append("_Sem dados suficientes para o consolidado._")
        else:
            partes.append(
                "Media de 3 percentis (barato vs. propria historia, perto do fundo do range, "
                "RSI sobrevendido) — leitura de mean reversion, nao a unica leitura valida "
                "(ver pagina 'Oportunidades Consolidadas' para o detalhe da metodologia)."
            )
            colunas = ["Ticker", "Nome", "Categoria", "Score Reversao (0-100)", "Z-Score",
                       "Posicao (%)", "RSI", "Tendencia (MA50 x MA200)"]
            formato = {"Score Reversao (0-100)": "{:.0f}", "Z-Score": "{:.2f}",
                       "Posicao (%)": "{:.0f}", "RSI": "{:.1f}"}
            partes.append(tabela_para_markdown(consolidado[colunas], formato))

    partes += [
        "",
        "---",
        "_Gerado pelo AVIN Quant Dashboard. Sem recomendacao de compra/venda — leitura "
        "estatistica descritiva, para cruzar com fundamento, cenario macro e research "
        "de terceiros antes de qualquer decisao._",
    ]

    return "\n".join(partes)
