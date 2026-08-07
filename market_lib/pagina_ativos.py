"""Renderizacao compartilhada das 4 sub-abas (Universo e Precos, Correlacoes e Valor
Relativo, Analise Tecnica, Oportunidades Consolidadas) usadas tanto pela pagina de
ETFs quanto pela de Stocks — cada uma chama renderizar_pagina() com seu proprio
arquivo de universo, so o dado muda, a logica e identica."""

import datetime as dt

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from market_lib import precos as precos_lib
from market_lib import analise
from market_lib import tecnica
from market_lib import consolidado as consolidado_lib
from market_lib import lamina as lamina_lib
from market_lib.estilo import NAVY, GOLD_ESCURO


@st.cache_data(ttl=3600, show_spinner="Buscando precos no Yahoo Finance...")
def _buscar_precos_cache(tickers, data_inicio):
    return precos_lib.buscar_precos(tickers, data_inicio)


@st.cache_data(ttl=86400, show_spinner=False)
def _buscar_nomes_cache(tickers):
    return precos_lib.buscar_nomes(tickers)


def renderizar_pagina(caminho_universo, titulo, chave_prefixo, permitir_nova_categoria=False):
    st.title(titulo)
    st.caption(
        "Universo de ativos, correlacoes/valor relativo, analise tecnica e o score consolidado de "
        "oportunidades, tudo numa aba so. Cada sub-aba tem seus proprios filtros."
    )

    universo_base = precos_lib.carregar_universo(caminho_universo)

    def _chave(sufixo):
        return f"{chave_prefixo}_{sufixo}"

    def _filtro_categorias(key):
        categorias_disponiveis = sorted(universo_base["Categoria"].dropna().unique().tolist())
        return st.multiselect(
            "Categorias", categorias_disponiveis, default=categorias_disponiveis, key=key
        )

    # ======================================================================
    # ABA 1 — Universo e Precos
    # ======================================================================
    def render_universo_precos():
        st.subheader("Universo de ativos")

        if universo_base.empty:
            st.info("Nenhum ativo cadastrado ainda — adicione o primeiro ticker abaixo.")
        else:
            categorias_selecionadas_top = _filtro_categorias(key=_chave("cat_universo"))
            st.caption(f"Universo atual: {len(universo_base)} ativo(s) (editavel em {caminho_universo})")

        with st.expander("➕ Adicionar ticker ao universo", expanded=universo_base.empty):
            col_ticker, col_categoria, col_subcategoria, col_botao = st.columns([2, 2, 2, 1])
            with col_ticker:
                novo_ticker = st.text_input("Ticker", key=_chave("novo_ticker_universo")).strip().upper()
            with col_categoria:
                if permitir_nova_categoria:
                    categorias_existentes = sorted(universo_base["Categoria"].dropna().unique().tolist())
                    nova_categoria = st.text_input(
                        "Categoria (setor)", key=_chave("nova_categoria_universo"),
                        help=f"Ja usadas: {', '.join(categorias_existentes)}" if categorias_existentes else None,
                    ).strip()
                else:
                    categorias_disponiveis_add = sorted(universo_base["Categoria"].dropna().unique().tolist())
                    nova_categoria = st.selectbox("Categoria", categorias_disponiveis_add, key=_chave("nova_categoria_universo"))
            with col_subcategoria:
                nova_subcategoria = st.text_input("Subcategoria", key=_chave("nova_subcategoria_universo")).strip()
            with col_botao:
                st.write("")
                st.write("")
                adicionar_clicado = st.button("Adicionar", key=_chave("botao_adicionar_ticker_universo"))

            if adicionar_clicado:
                if not novo_ticker:
                    st.warning("Digite um ticker.")
                elif permitir_nova_categoria and not nova_categoria:
                    st.warning("Digite uma categoria (setor).")
                elif novo_ticker in universo_base["Ticker"].values:
                    st.warning(f"{novo_ticker} ja esta no universo.")
                else:
                    with st.spinner(f"Procurando {novo_ticker} no Yahoo Finance..."):
                        resultado = precos_lib.validar_ticker(novo_ticker)
                    if resultado["valido"]:
                        precos_lib.adicionar_ticker_ao_universo(
                            caminho_universo, novo_ticker, nova_categoria, nova_subcategoria, "-", resultado["nome"]
                        )
                        st.success(f"{novo_ticker} ({resultado['nome']}) adicionado ao universo.")
                        st.rerun()
                    else:
                        st.error(f"Nao encontrei {novo_ticker} no Yahoo Finance. Confira o codigo.")

        if universo_base.empty:
            return

        universo = universo_base[universo_base["Categoria"].isin(categorias_selecionadas_top)].copy()
        universo = universo.drop_duplicates(subset="Ticker").reset_index(drop=True)

        if universo.empty:
            st.info("Selecione ao menos uma categoria acima.")
            return

        data_inicio = (dt.date.today() - dt.timedelta(days=400)).isoformat()

        tickers = universo["Ticker"].tolist()
        tabela_precos = _buscar_precos_cache(tickers, data_inicio)

        if tabela_precos.empty:
            st.error("Nao consegui buscar precos para esses tickers. Confira se os codigos estao corretos.")
            return

        nomes_ativos = _buscar_nomes_cache(tuple(tickers))

        st.divider()
        st.header("Performance dos ativos")

        col1, col2 = st.columns(2)
        col1.metric("Nº de ativos no universo", len(universo))
        col2.metric("Categorias selecionadas", len(categorias_selecionadas_top))

        tabela = precos_lib.montar_tabela_performance(tabela_precos, universo, nomes_ativos)

        if tabela.empty:
            st.warning("Nenhum preco encontrado para os ativos do universo selecionado.")
            return

        colunas_variacao = ["Variacao 1 Semana (%)", "Variacao 1 Mes (%)", "Variacao YTD (%)", "Variacao 1 Ano (%)"]

        def colorir_variacao(val):
            if pd.isna(val):
                return ""
            cor = "#1b7a3d" if val >= 0 else "#b3261e"
            return f"color: {cor}; font-weight: 600"

        st.dataframe(
            tabela.style
                .map(colorir_variacao, subset=colunas_variacao)
                .format({
                    "Preco Atual (US$)": "{:.2f}",
                    **{c: "{:.2f}" for c in colunas_variacao},
                }),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Ranking de variacao (menor → maior)")
        periodo_grafico = st.radio(
            "Ver variacao de:", colunas_variacao, horizontal=True, index=1, key=_chave("periodo_grafico_universo")
        )
        tabela_ordenada = tabela.sort_values(periodo_grafico)
        fig_var = px.bar(
            tabela_ordenada,
            x="Ticker", y=periodo_grafico,
            color="Categoria",
            hover_name="Nome",
            hover_data={"Subcategoria": True, "Descricao": True, "Categoria": False},
        )
        fig_var.update_layout(yaxis_tickformat=".2f")
        fig_var.update_xaxes(categoryorder="array", categoryarray=tabela_ordenada["Ticker"].tolist())
        st.plotly_chart(fig_var, use_container_width=True)

    # ======================================================================
    # ABA 2 — Correlacoes e Valor Relativo
    # ======================================================================
    def render_correlacoes():
        if universo_base.empty:
            st.info("Nenhum ativo cadastrado ainda — adicione tickers na aba 'Universo e Precos'.")
            return

        st.caption(
            "Leitura estatistica simples e transparente — sem caixa-preta: correlacao entre retornos "
            "diarios e z-score do preco atual vs. a propria historia de cada ativo. Passe o mouse nos "
            "graficos para ver o nome e a descricao de cada ativo."
        )

        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        with col_f1:
            categorias_selecionadas = _filtro_categorias(key=_chave("cat_corr"))
        with col_f2:
            anos_janela_corr = st.slider("Janela de correlacao (anos)", 1, 10, 3, key=_chave("janela_corr"))
        with col_f3:
            anos_janela_zscore = st.slider("Janela de valor relativo / z-score (anos)", 1, 15, 5, key=_chave("janela_zscore_corr"))

        universo = universo_base[universo_base["Categoria"].isin(categorias_selecionadas)].copy()

        if universo.empty:
            st.info("Selecione ao menos uma categoria acima.")
            return

        anos_busca = max(anos_janela_corr, anos_janela_zscore) + 1
        data_inicio = (dt.date.today() - dt.timedelta(days=365 * anos_busca)).isoformat()

        tickers = universo["Ticker"].tolist()
        tabela_precos = _buscar_precos_cache(tickers, data_inicio)

        if tabela_precos.empty:
            st.error("Nao consegui buscar precos para os ativos selecionados.")
            return

        nomes = _buscar_nomes_cache(tuple(tickers))

        st.divider()
        st.header("Matriz de correlacao")
        st.caption(
            f"Correlacao dos retornos diarios nos ultimos {anos_janela_corr} ano(s). "
            "Perto de +1: os ativos tendem a subir/cair juntos. Perto de -1: tendem a se mover em "
            "direcoes opostas (bom para diversificacao)."
        )

        data_corte_corr = tabela_precos.index[-1] - pd.Timedelta(days=365 * anos_janela_corr)
        precos_corr = tabela_precos[tabela_precos.index >= data_corte_corr]

        tickers_com_dados = [t for t in tickers if t in precos_corr.columns and precos_corr[t].notna().sum() > 30]

        if len(tickers_com_dados) < 2:
            st.warning("Poucos ativos com historico suficiente para calcular correlacao nesta janela.")
        else:
            matriz = analise.matriz_correlacao(precos_corr, tickers_com_dados)
            nomes_matriz = [nomes.get(t, t) for t in matriz.columns]
            customdata = np.dstack([
                np.broadcast_to(np.array(nomes_matriz)[None, :], matriz.shape),
                np.broadcast_to(np.array(nomes_matriz)[:, None], matriz.shape),
            ])
            fig_corr = px.imshow(
                matriz,
                color_continuous_scale=["#b3261e", "#ffffff", "#1b7a3d"],
                zmin=-1, zmax=1,
                aspect="auto",
                labels=dict(color="Correlacao"),
            )
            fig_corr.update_traces(
                customdata=customdata,
                hovertemplate="%{x} (%{customdata[0]}) x %{y} (%{customdata[1]})<br>Correlacao: %{z:.2f}<extra></extra>",
            )
            fig_corr.update_layout(height=max(400, 22 * len(tickers_com_dados)))
            st.plotly_chart(fig_corr, use_container_width=True)

        st.divider()
        st.header("Posicao no range")
        st.caption(
            f"Onde o preco atual esta hoje entre o minimo e o maximo dos ultimos {anos_janela_zscore} ano(s). "
            "A barra vai do minimo ao maximo da janela; o tracinho dourado marca a media; a bolinha marca "
            "o preco atual (verde = perto do minimo, vermelho = perto do maximo)."
        )

        posicoes = analise.ranking_posicao_no_range(tabela_precos, universo, anos_janela_zscore, nomes)

        if posicoes.empty:
            st.warning("Nao ha historico suficiente para calcular a posicao no range nesta janela.")
        else:
            fig_range = go.Figure()
            for _, linha in posicoes.iterrows():
                ticker = linha["Ticker"]
                legenda = f"{linha['Nome']}<br><i>{linha['Descricao']}</i>"
                fig_range.add_trace(go.Scatter(
                    x=[linha["Minimo (US$)"], linha["Maximo (US$)"]],
                    y=[ticker, ticker],
                    mode="lines",
                    line=dict(color="#C8BEAA", width=10),
                    showlegend=False,
                    hoverinfo="skip",
                ))
                fig_range.add_trace(go.Scatter(
                    x=[linha["Media (US$)"]],
                    y=[ticker],
                    mode="markers",
                    marker=dict(symbol="line-ns", size=16, color="#896F3D", line=dict(width=3, color="#896F3D")),
                    showlegend=False,
                    hovertemplate=f"{legenda}<br>Media: {linha['Media (US$)']:.2f}<extra></extra>",
                ))
                fig_range.add_trace(go.Scatter(
                    x=[linha["Atual (US$)"]],
                    y=[ticker],
                    mode="markers",
                    marker=dict(size=14, color=analise.cor_posicao(linha["Posicao (%)"]), line=dict(width=1, color="#102134")),
                    showlegend=False,
                    hovertemplate=(
                        f"{legenda}<br>Atual: {linha['Atual (US$)']:.2f}<br>"
                        f"Posicao no range: {linha['Posicao (%)']:.0f}%<extra></extra>"
                    ),
                ))

            fig_range.update_layout(
                height=max(400, 34 * len(posicoes)),
                xaxis_title="Preco (US$)",
                yaxis=dict(categoryorder="array", categoryarray=posicoes["Ticker"].tolist()),
                margin=dict(l=10, r=10, t=10, b=40),
            )
            st.plotly_chart(fig_range, use_container_width=True)

        st.divider()
        st.header("Valor relativo (z-score vs. propria historia)")
        st.caption(
            f"Z-score do preco atual vs. media dos ultimos {anos_janela_zscore} ano(s), em desvios-padrao. "
            "Negativo = preco abaixo da media historica ('mais barato' vs. a propria historia); "
            "positivo = acima. Nao e recomendacao de compra/venda — e so uma leitura estatistica, "
            "para cruzar com fundamento e cenario macro antes de qualquer decisao."
        )

        ranking = analise.ranking_zscore(tabela_precos, universo, anos_janela_zscore, nomes)

        if ranking.empty:
            st.warning("Nao ha historico suficiente para calcular o z-score nesta janela.")
            return

        def colorir_zscore(val):
            if pd.isna(val):
                return ""
            cor = "#b3261e" if val >= 0 else "#1b7a3d"
            return f"color: {cor}; font-weight: 600"

        colunas_tabela = ["Ticker", "Nome", "Categoria", "Subcategoria", "Preco Atual (US$)",
                           "Media Historica (US$)", "Z-Score"]
        st.dataframe(
            ranking[colunas_tabela].style
                .map(colorir_zscore, subset=["Z-Score"])
                .format({
                    "Preco Atual (US$)": "{:.2f}",
                    "Media Historica (US$)": "{:.2f}",
                    "Z-Score": "{:.2f}",
                }),
            use_container_width=True,
            hide_index=True,
        )

        fig_zscore = px.bar(
            ranking,
            x="Ticker", y="Z-Score",
            color="Categoria",
            hover_name="Nome",
            hover_data={"Subcategoria": True, "Descricao": True, "Categoria": False},
        )
        fig_zscore.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_zscore.update_xaxes(categoryorder="array", categoryarray=ranking["Ticker"].tolist())
        st.plotly_chart(fig_zscore, use_container_width=True)

    # ======================================================================
    # ABA 3 — Analise Tecnica
    # ======================================================================
    def render_analise_tecnica():
        if universo_base.empty:
            st.info("Nenhum ativo cadastrado ainda — adicione tickers na aba 'Universo e Precos'.")
            return

        st.caption(
            "Comportamento do preco: medias moveis (MA20/50/100/200), momentum (RSI) e volatilidade "
            "(regime + Bandas de Bollinger). Leitura estatistica do preco em si — nao usa fundamento "
            "nem cenario macro."
        )

        categorias_selecionadas = _filtro_categorias(key=_chave("cat_tecnica"))
        universo = universo_base[universo_base["Categoria"].isin(categorias_selecionadas)].copy()

        if universo.empty:
            st.info("Selecione ao menos uma categoria acima.")
            return

        with st.expander("Parametros avancados"):
            periodo_rsi = st.slider("Periodo do RSI", 5, 30, 14, key=_chave("periodo_rsi_tecnica"))
            janela_vol_curta = st.slider("Janela da volatilidade recente (dias)", 10, 60, 20, key=_chave("janela_vol_curta_tecnica"))
            anos_vol_historico = st.slider("Janela historica p/ regime de vol (anos)", 1, 10, 3, key=_chave("anos_vol_historico_tecnica"))
            janela_bollinger = st.slider("Janela das Bandas de Bollinger (dias)", 10, 60, 20, key=_chave("janela_bollinger_tecnica"))
            desvios_bollinger = st.slider("Bandas de Bollinger (desvios-padrao)", 1.0, 3.0, 2.0, step=0.5, key=_chave("desvios_bollinger_tecnica"))

        tickers = universo["Ticker"].tolist()
        anos_busca = max(anos_vol_historico, 3) + 1
        data_inicio = (dt.date.today() - dt.timedelta(days=365 * anos_busca)).isoformat()

        tabela_precos = _buscar_precos_cache(tickers, data_inicio)

        if tabela_precos.empty:
            st.error("Nao consegui buscar precos para os ativos selecionados.")
            return

        nomes = _buscar_nomes_cache(tuple(tickers))
        descricoes = universo.set_index("Ticker")["Descricao"].to_dict()

        st.divider()
        st.header("Detalhe por ativo")

        ticker_selecionado = st.selectbox(
            "Ativo",
            tickers,
            format_func=lambda t: f"{t} — {nomes.get(t, t)}",
            key=_chave("ticker_selecionado_tecnica"),
        )
        serie_selecionada = tabela_precos[ticker_selecionado].dropna()
        st.caption(f"**{nomes.get(ticker_selecionado, ticker_selecionado)}** — {descricoes.get(ticker_selecionado, '')}")

        aba_momentum, aba_vol = st.tabs(["Momentum (RSI)", "Volatilidade (Bollinger)"])

        with aba_momentum:
            serie_rsi = tecnica.rsi(serie_selecionada, periodo_rsi).dropna()
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=serie_rsi.index, y=serie_rsi.values, name=f"RSI ({periodo_rsi})", line=dict(color=GOLD_ESCURO, width=2)))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="#b3261e", annotation_text="Sobrecomprado (70)")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="#1b7a3d", annotation_text="Sobrevendido (30)")
            fig_rsi.update_layout(height=350, yaxis_title="RSI", yaxis_range=[0, 100])
            st.plotly_chart(fig_rsi, use_container_width=True)

            if not serie_rsi.empty:
                valor_rsi = serie_rsi.iloc[-1]
                st.metric(f"RSI ({periodo_rsi}) atual", f"{valor_rsi:.1f}", tecnica.classificar_rsi(valor_rsi))

        with aba_vol:
            df_bb = tecnica.bandas_bollinger(serie_selecionada, janela_bollinger, desvios_bollinger)
            fig_bb = go.Figure()
            fig_bb.add_trace(go.Scatter(x=df_bb.index, y=df_bb["Banda_Superior"], name="Banda Superior",
                                         line=dict(color="#C8BEAA", width=1), showlegend=True))
            fig_bb.add_trace(go.Scatter(x=df_bb.index, y=df_bb["Banda_Inferior"], name="Banda Inferior",
                                         line=dict(color="#C8BEAA", width=1), fill="tonexty",
                                         fillcolor="rgba(200,190,170,0.2)", showlegend=True))
            fig_bb.add_trace(go.Scatter(x=df_bb.index, y=df_bb["Media"], name=f"Media ({janela_bollinger}d)",
                                         line=dict(color=GOLD_ESCURO, width=1, dash="dash")))
            fig_bb.add_trace(go.Scatter(x=df_bb.index, y=df_bb["Preco"], name="Preco", line=dict(color=NAVY, width=2)))
            fig_bb.update_layout(height=450, yaxis_title="Preco (US$)", legend_title="Serie")
            st.plotly_chart(fig_bb, use_container_width=True)

            regime_vol = tecnica.regime_volatilidade(serie_selecionada, janela_vol_curta, anos_vol_historico)
            col1, col2, col3 = st.columns(3)
            col1.metric("Vol. anualizada recente", f"{regime_vol['vol_atual']:.1f}%" if pd.notna(regime_vol["vol_atual"]) else "-")
            col2.metric(f"Vol. media (ult. {anos_vol_historico}a)", f"{regime_vol['vol_media_historica']:.1f}%" if pd.notna(regime_vol["vol_media_historica"]) else "-")
            col3.metric("Z-Score da volatilidade", f"{regime_vol['zscore_vol']:.2f}" if pd.notna(regime_vol["zscore_vol"]) else "-")
            st.caption(
                "Z-Score da volatilidade positivo = o ativo esta mais agitado do que o normal para ele "
                "mesmo; negativo = mais calmo do que o normal."
            )

        st.divider()
        st.header("Visao do universo")

        aba_tendencia, aba_rsi, aba_vol_universo = st.tabs(["Estrutura de Tendencia", "Momentum (RSI)", "Regime de Volatilidade"])

        with aba_tendencia:
            st.caption(
                "'Acima de (0-4)': em quantas das 4 medias moveis o preco atual esta acima "
                "(4 = alinhamento de alta consistente; 0 = alinhamento de baixa). "
                "'Tendencia' compara MA50 x MA200 (golden/death cross classico)."
            )
            ranking_tend = tecnica.ranking_tendencia(tabela_precos, universo, nomes)
            if ranking_tend.empty:
                st.warning("Sem dados suficientes.")
            else:
                colunas = ["Ticker", "Nome", "Categoria", "Preco Atual (US$)", "MA20", "MA50", "MA100", "MA200",
                           "Acima de (0-4)", "Tendencia (MA50 x MA200)", "Cruzamento recente"]

                def colorir_acima_de(val):
                    if pd.isna(val):
                        return ""
                    cor = "#1b7a3d" if val >= 3 else ("#b3261e" if val <= 1 else "#896F3D")
                    return f"color: {cor}; font-weight: 600"

                st.dataframe(
                    ranking_tend[colunas].sort_values("Acima de (0-4)", ascending=False).style
                        .map(colorir_acima_de, subset=["Acima de (0-4)"])
                        .format({"Preco Atual (US$)": "{:.2f}", "MA20": "{:.2f}", "MA50": "{:.2f}",
                                 "MA100": "{:.2f}", "MA200": "{:.2f}"}),
                    use_container_width=True,
                    hide_index=True,
                )

        with aba_rsi:
            st.caption(
                f"RSI({periodo_rsi}) de Wilder. Acima de 70: sobrecomprado. Abaixo de 30: sobrevendido. "
                "Limiares convencionais de leitura, nao gatilhos automaticos de compra/venda."
            )
            ranking_rsi_df = tecnica.ranking_rsi(tabela_precos, universo, periodo_rsi, nomes)
            if ranking_rsi_df.empty:
                st.warning("Sem dados suficientes.")
            else:
                coluna_rsi = f"RSI ({periodo_rsi})"

                def colorir_rsi(val):
                    if pd.isna(val):
                        return ""
                    cor = "#b3261e" if val >= 70 else ("#1b7a3d" if val <= 30 else "#404751")
                    return f"color: {cor}; font-weight: 600"

                st.dataframe(
                    ranking_rsi_df[["Ticker", "Nome", "Categoria", coluna_rsi, "Classificacao"]].style
                        .map(colorir_rsi, subset=[coluna_rsi])
                        .format({coluna_rsi: "{:.1f}"}),
                    use_container_width=True,
                    hide_index=True,
                )

                fig_rsi_bar = px.bar(
                    ranking_rsi_df, x="Ticker", y=coluna_rsi, color="Categoria",
                    hover_name="Nome", hover_data={"Subcategoria": True, "Descricao": True, "Categoria": False},
                )
                fig_rsi_bar.add_hline(y=70, line_dash="dash", line_color="#b3261e")
                fig_rsi_bar.add_hline(y=30, line_dash="dash", line_color="#1b7a3d")
                fig_rsi_bar.update_xaxes(categoryorder="array", categoryarray=ranking_rsi_df["Ticker"].tolist())
                st.plotly_chart(fig_rsi_bar, use_container_width=True)

        with aba_vol_universo:
            st.caption(
                "Z-Score da volatilidade: compara a vol. anualizada recente de cada ativo com a "
                "distribuicao da propria vol. historica dele. Positivo = mais agitado que o normal "
                "para esse ativo especifico (nao entre ativos diferentes)."
            )
            ranking_vol_df = tecnica.ranking_volatilidade(tabela_precos, universo, janela_vol_curta, anos_vol_historico, nomes)
            if ranking_vol_df.empty:
                st.warning("Sem dados suficientes.")
            else:
                def colorir_vol(val):
                    if pd.isna(val):
                        return ""
                    cor = "#b3261e" if val >= 0 else "#1b7a3d"
                    return f"color: {cor}; font-weight: 600"

                st.dataframe(
                    ranking_vol_df[["Ticker", "Nome", "Categoria", "Vol Atual Anualizada (%)",
                                    "Vol Media Historica (%)", "Z-Score Vol"]].style
                        .map(colorir_vol, subset=["Z-Score Vol"])
                        .format({"Vol Atual Anualizada (%)": "{:.1f}", "Vol Media Historica (%)": "{:.1f}",
                                 "Z-Score Vol": "{:.2f}"}),
                    use_container_width=True,
                    hide_index=True,
                )

                fig_vol_bar = px.bar(
                    ranking_vol_df, x="Ticker", y="Z-Score Vol", color="Categoria",
                    hover_name="Nome", hover_data={"Subcategoria": True, "Descricao": True, "Categoria": False},
                )
                fig_vol_bar.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_vol_bar.update_xaxes(categoryorder="array", categoryarray=ranking_vol_df["Ticker"].tolist())
                st.plotly_chart(fig_vol_bar, use_container_width=True)

    # ======================================================================
    # ABA 4 — Oportunidades Consolidadas
    # ======================================================================
    def render_oportunidades():
        if universo_base.empty:
            st.info("Nenhum ativo cadastrado ainda — adicione tickers na aba 'Universo e Precos'.")
            return

        st.caption(
            "Ranking de reversao: aponta quais ativos estao mais descontados em relacao a propria "
            "media historica de preco (nao diz o motivo do desconto — fundamento, noticia, fluxo — so "
            "aponta a estatistica)."
        )

        with st.expander("Como ler esta tabela (leia antes de usar)", expanded=True):
            st.markdown(
                "**Em uma frase:** o Score de Reversao (0-100) rankeia os ativos do mais \"descontado\" "
                "pra baixo (perto de 100) ao mais \"esticado\" pra cima (perto de 0), olhando so pro "
                "comportamento do preco.\n\n"
                "**Glossario das colunas:**\n\n"
                "- **Score Reversao (0-100)**: media das 3 leituras abaixo — quanto mais alto, mais "
                "descontado o ativo esta nas 3 ao mesmo tempo\n"
                "- **Z-Score**: quantos desvios-padrao o preco atual esta da propria media historica "
                "(negativo = abaixo da media, ou seja mais barato do que o normal para ele mesmo)\n"
                "- **Posicao (%)**: onde o preco esta hoje entre a minima (0%) e a maxima (100%) do "
                "periodo escolhido\n"
                "- **RSI**: indicador de momentum de 0 a 100 — abaixo de 30 e considerado sobrevendido, "
                "acima de 70 e considerado sobrecomprado\n"
                "- **Acima de (0-4)** / **Tendencia (MA50 x MA200)**: quantas medias moveis o preco esta "
                "acima e se as medias de 50 e 200 dias apontam pra alta ou pra baixa — contexto de "
                "tendencia, nao entra na conta do score\n"
                "- **Z-Score Vol**: se o ativo esta mais ou menos volatil do que o normal pra ele mesmo — "
                "tambem so contexto, nao entra no score\n\n"
                "**Exemplo:** um ativo com Z-Score de -1,5 (bem abaixo da media historica), Posicao de "
                "10% no range (perto do fundo de 52 semanas) e RSI de 25 (sobrevendido) fica com score "
                "proximo de 100. Ja um ativo caro, no topo do range e com RSI de 80 fica com score "
                "proximo de 0.\n\n"
                "**Atencao — isso e so uma das leituras possiveis:** o score assume uma logica de "
                "**mean reversion** (aposta estatistica de que preco muito esticado tende a voltar pra "
                "media) — **nao e a unica leitura valida nem uma recomendacao**. Quem segue tendencia "
                "leria a mesma tabela ao contrario (RSI alto + preco acima das medias = forca, nao "
                "fraqueza). Por isso todos os componentes crus ficam visiveis ao lado do score."
            )

        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        with col_f1:
            categorias_selecionadas = _filtro_categorias(key=_chave("cat_oport"))
        with col_f2:
            anos_valor_relativo = st.slider("Janela de valor relativo (anos)", 1, 15, 5, key=_chave("janela_valor_relativo_oport"))
        with col_f3:
            periodo_rsi = st.slider("Periodo do RSI", 5, 30, 14, key=_chave("periodo_rsi_oport"))

        universo = universo_base[universo_base["Categoria"].isin(categorias_selecionadas)].copy()

        if universo.empty:
            st.info("Selecione ao menos uma categoria acima.")
            return

        tickers = universo["Ticker"].tolist()
        anos_busca = anos_valor_relativo + 1
        data_inicio = (dt.date.today() - dt.timedelta(days=365 * anos_busca)).isoformat()

        tabela_precos = _buscar_precos_cache(tickers, data_inicio)

        if tabela_precos.empty:
            st.error("Nao consegui buscar precos para os ativos selecionados.")
            return

        nomes = _buscar_nomes_cache(tuple(tickers))

        consolidado = consolidado_lib.montar_consolidado(tabela_precos, universo, nomes, anos_valor_relativo, periodo_rsi)

        if consolidado.empty:
            st.warning("Sem dados suficientes para montar o consolidado nesta janela/filtro.")
            return

        st.divider()
        st.header("Ranking — Score de Reversao")

        def colorir_score(val):
            if pd.isna(val):
                return ""
            t = val / 100
            r = round(27 + (179 - 27) * t)
            g = round(122 + (38 - 122) * t)
            b = round(61 + (30 - 61) * t)
            return f"color: #{r:02x}{g:02x}{b:02x}; font-weight: 700"

        colunas_tabela = [
            "Ticker", "Nome", "Categoria", "Subcategoria", "Score Reversao (0-100)",
            "Z-Score", "Posicao (%)", "RSI", "Acima de (0-4)", "Tendencia (MA50 x MA200)", "Z-Score Vol",
        ]

        st.dataframe(
            consolidado[colunas_tabela].style
                .map(colorir_score, subset=["Score Reversao (0-100)"])
                .format({
                    "Score Reversao (0-100)": "{:.0f}",
                    "Z-Score": "{:.2f}",
                    "Posicao (%)": "{:.0f}",
                    "RSI": "{:.1f}",
                    "Z-Score Vol": "{:.2f}",
                }),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        col_top, col_bottom = st.columns(2)
        with col_top:
            st.subheader("Setups de reversao mais fortes (nesta leitura)")
            top5 = consolidado.head(5)[["Ticker", "Nome", "Score Reversao (0-100)", "Z-Score", "Posicao (%)", "RSI"]]
            st.dataframe(top5, use_container_width=True, hide_index=True)

        with col_bottom:
            st.subheader("Mais esticados para o outro lado")
            bottom5 = consolidado.tail(5)[["Ticker", "Nome", "Score Reversao (0-100)", "Z-Score", "Posicao (%)", "RSI"]]
            st.dataframe(bottom5, use_container_width=True, hide_index=True)

        st.caption(
            "Leitura puramente estatistica sobre preco — nao considera fundamento, fluxo, catalisadores "
            "ou cenario macro."
        )

        st.divider()
        st.subheader("Lamina de Oportunidades")
        st.caption(
            "Gera um PDF de 1 pagina, so com as tabelas do que esta filtrado acima — pratico pra "
            "mandar pro gestor ou guardar o retrato da semana."
        )
        col_lamina1, col_lamina2 = st.columns([1, 3])
        with col_lamina1:
            top_n_lamina = st.slider("Ativos por tabela", 3, 20, 10, key=_chave("top_n_lamina"))

        pdf_bytes = lamina_lib.gerar_lamina_pdf(
            consolidado,
            categorias_selecionadas,
            anos_valor_relativo,
            periodo_rsi,
            top_n=top_n_lamina,
        )
        st.download_button(
            "Gerar lamina (PDF)",
            data=pdf_bytes,
            file_name=f"avin_lamina_oportunidades_{dt.date.today().isoformat()}.pdf",
            mime="application/pdf",
            key=_chave("download_lamina"),
        )

    tab_universo, tab_corr, tab_tecnica, tab_oport = st.tabs(
        ["Universo e Precos", "Correlacoes e Valor Relativo", "Analise Tecnica", "Oportunidades Consolidadas"]
    )

    with tab_universo:
        render_universo_precos()

    with tab_corr:
        render_correlacoes()

    with tab_tecnica:
        render_analise_tecnica()

    with tab_oport:
        render_oportunidades()
