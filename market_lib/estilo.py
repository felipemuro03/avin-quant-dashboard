"""Paleta e CSS da marca AVIN, compartilhados por todas as paginas."""

import streamlit as st

NAVY = "#102134"
GOLD = "#BAA377"
GOLD_ESCURO = "#896F3D"
BRANCO = "#FFFFFF"

NAVY_SECUNDARIO = "#1A293F"
BEGE_SECUNDARIO = "#C8BEAA"
CINZA_SECUNDARIO = "#404751"


def aplicar_estilo():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Montserrat', Arial, sans-serif;
        }}
        h1, h2, h3 {{
            font-weight: 600 !important;
            color: {NAVY};
        }}
        [data-testid="stMetricLabel"] {{
            font-weight: 600;
            color: {NAVY};
        }}
        [data-testid="stMetricValue"] {{
            color: {NAVY};
        }}
        [data-testid="stSidebar"] {{
            background-color: {NAVY};
        }}
        [data-testid="stSidebar"] * {{
            color: {BRANCO} !important;
        }}
        .stButton > button, .stDownloadButton > button {{
            background-color: {GOLD};
            color: {NAVY};
            border: none;
            font-weight: 600;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            background-color: {GOLD_ESCURO};
            color: {BRANCO};
        }}
        .stTabs [aria-selected="true"] {{
            color: {GOLD_ESCURO};
            border-bottom-color: {GOLD_ESCURO} !important;
        }}
        .avin-tag {{
            display: inline-block;
            background-color: {BEGE_SECUNDARIO};
            color: {NAVY_SECUNDARIO};
            border-radius: 4px;
            padding: 1px 8px;
            font-size: 0.8em;
            font-weight: 600;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
