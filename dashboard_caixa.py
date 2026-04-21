#!/usr/bin/env python3
"""
Dashboard Streamlit - Análise de Imóveis Caixa Econômica
Dados ao vivo do Google Sheets
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from datetime import datetime
import os

st.set_page_config(page_title="Dashboard Caixa", layout="wide", initial_sidebar_state="expanded")

# ==================== AUTENTICAÇÃO & DADOS ====================

@st.cache_resource
def get_sheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    local_creds = r"C:\Users\antonio.zambianco_if\Desktop\Claude\plataforma-leiloes\01_config\credenciais.json"
    if os.path.exists(local_creds):
        creds = Credentials.from_service_account_file(local_creds, scopes=scopes)
    else:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
    return gspread.authorize(creds)

def convert_br_to_float(value):
    if pd.isna(value) or value == '' or value == 'nan':
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.replace('R$', '').strip().replace('.', '').replace(',', '.')
    try:
        return float(value)
    except:
        return None

@st.cache_data(ttl=3600)
def load_data():
    try:
        client = get_sheets_client()
        spreadsheet = client.open_by_key("162QLT4L9eg0Q5AV63th88OGeow_12YlAWOpwn-UOLMY")
        sheet = spreadsheet.worksheet("IMOVEIS_ATUAL")
        dados = sheet.get_all_values()
        df = pd.DataFrame(dados[1:], columns=dados[0])

        numeric_cols = ['Preço', 'Valor de avaliação', 'Desconto', 'Área Terreno (m²)', 'Área Privativa (m²)', 'Quartos', 'Andar']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(convert_br_to_float)

        for col in ['Quartos', 'Andar']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

# ==================== HEADER ====================

st.title("Dashboard Caixa Econômica")
st.markdown("Imóveis para Leilão — Dados ao vivo")

df = load_data()

if df is None or len(df) == 0:
    st.error("Erro ao carregar dados. Verifique a conexão com Google Sheets.")
    st.stop()

# ==================== FILTROS ====================

st.sidebar.header("Filtros")

# ===== LOCALIZAÇÃO =====
with st.sidebar.expander("Localização", expanded=True):
    estados = sorted(df['UF'].dropna().unique().tolist())
    estados_selecionados = st.multiselect("Estado (UF)", estados, default=[], key="multiselect_uf")

    busca_cidade = st.text_input("Cidade (busca)", placeholder="ex: JOAO PESSOA", key="busca_cidade").strip().upper()

    busca_bairro = st.text_input("Bairro (busca)", placeholder="ex: CENTRO", key="busca_bairro").strip().upper()

    st.divider()
    apenas_end_nao_batido = st.checkbox("Apenas Endereços Não Batidos", value=False, key="checkbox_endraro")

# ===== ANÁLISE DE OPORTUNIDADE =====
with st.sidebar.expander("Análise de Oportunidade", expanded=False):
    tiers = sorted([t for t in df['Tier'].dropna().unique().tolist() if t != ""])
    tiers_selecionados = st.multiselect("Tier", tiers, default=[], key="multiselect_tier")

    acoes = sorted([a for a in df['Ação'].dropna().unique().tolist() if a != ""])
    acoes_selecionadas = st.multiselect("Ação", acoes, default=[], key="multiselect_acao")

# ===== PREÇO & AVALIAÇÃO =====
with st.sidebar.expander("Preço & Avaliação", expanded=False):
    faixas = sorted([f for f in df['Faixa Preço'].dropna().unique().tolist() if f != ""])
    faixas_selecionadas = st.multiselect("Faixa de Preço", faixas, default=[], key="multiselect_faixa")

    preco_min_geral = int(df['Preço'].dropna().min())
    preco_max_geral = int(df['Preço'].dropna().max())
    col1, col2 = st.columns(2)
    with col1:
        preco_min_filtro = st.number_input("Preço Mín (R$)", value=preco_min_geral, step=1000, key="preco_min")
    with col2:
        preco_max_filtro = st.number_input("Preço Máx (R$)", value=preco_max_geral, step=1000, key="preco_max")

    st.divider()
    aval_min_geral = int(df['Valor de avaliação'].dropna().min())
    aval_max_geral = int(df['Valor de avaliação'].dropna().max())
    col1, col2 = st.columns(2)
    with col1:
        aval_min_filtro = st.number_input("Avaliação Mín (R$)", value=aval_min_geral, step=1000, key="aval_min")
    with col2:
        aval_max_filtro = st.number_input("Avaliação Máx (R$)", value=aval_max_geral, step=1000, key="aval_max")

# ===== CARACTERÍSTICAS =====
with st.sidebar.expander("Características", expanded=False):
    tipos = sorted([t for t in df['Tipo'].dropna().unique().tolist() if t != ""])
    tipos_selecionados = st.multiselect("Tipo de Imóvel", tipos, default=[], key="multiselect_tipo")

    quartos_list = sorted([q for q in df['Quartos'].dropna().unique().tolist()])
    quartos_selecionados = st.multiselect("Quartos", quartos_list, default=[], key="multiselect_quartos")

    andares_list = sorted([a for a in df['Andar'].dropna().unique().tolist()])
    andares_selecionados = st.multiselect("Andar", andares_list, default=[], key="multiselect_andar")

    tem_varanda = st.checkbox("Tem Varanda", value=False, key="checkbox_varanda")
    tem_vaga = st.checkbox("Tem Vaga", value=False, key="checkbox_vaga")

    st.divider()
    area_terreno_min_geral = float(df['Área Terreno (m²)'].dropna().min() or 0)
    area_terreno_max_geral = float(df['Área Terreno (m²)'].dropna().max() or 0)
    col1, col2 = st.columns(2)
    with col1:
        area_terreno_min_filtro = st.number_input("Terreno Mín (m²)", value=area_terreno_min_geral, step=10.0, key="area_terreno_min")
    with col2:
        area_terreno_max_filtro = st.number_input("Terreno Máx (m²)", value=area_terreno_max_geral, step=10.0, key="area_terreno_max")

    area_priv_min_geral = float(df['Área Privativa (m²)'].dropna().min() or 0)
    area_priv_max_geral = float(df['Área Privativa (m²)'].dropna().max() or 0)
    col1, col2 = st.columns(2)
    with col1:
        area_priv_min_filtro = st.number_input("Privativa Mín (m²)", value=area_priv_min_geral, step=10.0, key="area_priv_min")
    with col2:
        area_priv_max_filtro = st.number_input("Privativa Máx (m²)", value=area_priv_max_geral, step=10.0, key="area_priv_max")

# ===== MODALIDADE & PAGAMENTO =====
with st.sidebar.expander("Modalidade & Pagamento", expanded=False):
    if 'Modalidade de venda' in df.columns:
        modalidades = sorted([m for m in df['Modalidade de venda'].dropna().unique().tolist() if m != ""])
        modalidades_selecionadas = st.multiselect("Modalidade de Venda", modalidades, default=[], key="multiselect_modalidade")
    else:
        modalidades_selecionadas = []

    apenas_financiavel = st.checkbox("Apenas Financiáveis", value=False, key="checkbox_financ")

# ===== LIMPAR FILTROS =====
st.sidebar.divider()
if st.sidebar.button("Limpar Todos os Filtros"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==================== APLICAR FILTROS ====================

def aplicar_filtros(df_base, incluir_acao=True):
    d = df_base.copy()

    if estados_selecionados:
        d = d[d['UF'].isin(estados_selecionados)]
    if busca_cidade:
        d = d[d['Cidade'].str.upper().str.contains(busca_cidade, na=False)]
    if busca_bairro:
        d = d[d['Bairro'].str.upper().str.contains(busca_bairro, na=False)]
    if apenas_end_nao_batido:
        d = d[d['Endereço não batido'] == 'Sim']
    if tiers_selecionados:
        d = d[d['Tier'].isin(tiers_selecionados)]
    if incluir_acao and acoes_selecionadas:
        d = d[d['Ação'].isin(acoes_selecionadas)]
    if faixas_selecionadas:
        d = d[d['Faixa Preço'].isin(faixas_selecionadas)]
    if tipos_selecionados:
        d = d[d['Tipo'].isin(tipos_selecionados)]
    if quartos_selecionados:
        d = d[d['Quartos'].isin(quartos_selecionados)]
    if andares_selecionados:
        d = d[d['Andar'].isin(andares_selecionados)]
    if tem_varanda:
        d = d[d['Varanda'] == 'Sim']
    if tem_vaga:
        d = d[d['Vaga'] == 'Sim']
    if modalidades_selecionadas:
        d = d[d['Modalidade de venda'].isin(modalidades_selecionadas)]
    if apenas_financiavel:
        d = d[d['Financiamento'] == 'Sim']

    d = d[(d['Preço'] >= preco_min_filtro) & (d['Preço'] <= preco_max_filtro)]
    d = d[(d['Valor de avaliação'] >= aval_min_filtro) & (d['Valor de avaliação'] <= aval_max_filtro)]

    if area_terreno_min_filtro > area_terreno_min_geral or area_terreno_max_filtro < area_terreno_max_geral:
        d = d[d['Área Terreno (m²)'].isna() |
              ((d['Área Terreno (m²)'] >= area_terreno_min_filtro) & (d['Área Terreno (m²)'] <= area_terreno_max_filtro))]

    if area_priv_min_filtro > area_priv_min_geral or area_priv_max_filtro < area_priv_max_geral:
        d = d[d['Área Privativa (m²)'].isna() |
              ((d['Área Privativa (m²)'] >= area_priv_min_filtro) & (d['Área Privativa (m²)'] <= area_priv_max_filtro))]

    return d

df_filtrado = aplicar_filtros(df, incluir_acao=True)
df_oportunidades = aplicar_filtros(df, incluir_acao=False)

st.sidebar.markdown(f"**Resultados: {len(df_filtrado):,} imóveis**")

# ==================== ABAS ====================

tab1, tab2, tab3 = st.tabs(["Geral", "Oportunidades", "Dados"])

# ========== TAB 1: GERAL ==========
with tab1:
    st.subheader("Visão Geral do Mercado")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Imóveis", f"{len(df_filtrado):,}")
    with col2:
        st.metric("Cidades Únicas", f"{df_filtrado['Cidade'].nunique():,}")
    with col3:
        st.metric("Endereços Não Batidos", f"{(df_filtrado['Endereço não batido'] == 'Sim').sum():,}")

    st.divider()

    preco_valido = df_filtrado['Preço'].dropna()
    preco_valido = preco_valido[preco_valido > 0]
    col1, col2 = st.columns(2)
    with col1:
        preco_medio = preco_valido.mean() if len(preco_valido) > 0 else 0
        st.metric("Preço Médio", f"R$ {preco_medio:,.0f}" if preco_medio > 0 else "N/A")
    with col2:
        preco_min_val = preco_valido.min() if len(preco_valido) > 0 else 0
        st.metric("Preço Mínimo", f"R$ {preco_min_val:,.0f}" if preco_min_val > 0 else "N/A")

    st.divider()

    faixa_counts = df_filtrado['Faixa Preço'].value_counts().sort_index()
    fig_faixa = px.bar(
        x=faixa_counts.index,
        y=faixa_counts.values,
        title="Distribuição por Faixa de Preço",
        labels={'x': 'Faixa', 'y': 'Quantidade'},
        color=faixa_counts.values,
        color_continuous_scale='Plasma',
        text_auto=True
    )
    fig_faixa.update_layout(showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig_faixa, use_container_width=True)

    top_n = st.selectbox("Top N cidades", [30, 50, 100], index=0, key="top_n_cidades")
    cidade_counts = df_filtrado['Cidade'].value_counts().head(top_n)
    altura_cidades = max(500, top_n * 20)
    fig_cidades = px.bar(
        x=cidade_counts.values,
        y=cidade_counts.index,
        orientation='h',
        title=f"Top {top_n} Cidades",
        labels={'x': 'Quantidade', 'y': 'Cidade'},
        color=cidade_counts.values,
        color_continuous_scale='Viridis',
        text_auto=True,
        height=altura_cidades
    )
    fig_cidades.update_layout(yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False)
    st.plotly_chart(fig_cidades, use_container_width=True)

# ========== TAB 2: OPORTUNIDADES ==========
with tab2:
    colunas_ord_op = ['Preço', 'Valor de avaliação', 'Desconto', 'Área Privativa (m²)', 'Quartos', 'Andar']

    # --- APROFUNDAR ---
    aprofundar_df = df_oportunidades[df_oportunidades['Ação'] == 'aprofundar'].copy()

    preco_apr = aprofundar_df['Preço'].dropna()
    preco_apr = preco_apr[preco_apr > 0]

    st.subheader(f"Aprofundar ({len(aprofundar_df):,})")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Preço Médio", f"R$ {preco_apr.mean():,.0f}" if len(preco_apr) > 0 else "N/A")
    with m2:
        st.metric("Preço Máx", f"R$ {preco_apr.max():,.0f}" if len(preco_apr) > 0 else "N/A")
    with m3:
        ord_apr_col = st.selectbox("Ordenar por", colunas_ord_op, index=0, key="ord_apr_col")
    with m4:
        ord_apr_asc = st.selectbox("Ordem", ["Crescente", "Decrescente"], index=0, key="ord_apr_asc")

    aprofundar_df = aprofundar_df.sort_values(ord_apr_col, ascending=(ord_apr_asc == "Crescente"))

    if len(aprofundar_df) > 0:
        st.dataframe(
            aprofundar_df,
            use_container_width=True,
            height=600,
            hide_index=True,
            column_config={"Link de acesso": st.column_config.LinkColumn("Link", display_text="🔗 Abrir")}
        )
    else:
        st.info("Nenhum imóvel para aprofundar com os filtros atuais.")

    st.divider()

    # --- ACOMPANHAR ---
    acompanhar_df = df_oportunidades[df_oportunidades['Ação'] == 'acompanhar'].copy()

    preco_aco = acompanhar_df['Preço'].dropna()
    preco_aco = preco_aco[preco_aco > 0]

    st.subheader(f"Acompanhar ({len(acompanhar_df):,})")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Preço Médio", f"R$ {preco_aco.mean():,.0f}" if len(preco_aco) > 0 else "N/A")
    with m2:
        st.metric("Preço Máx", f"R$ {preco_aco.max():,.0f}" if len(preco_aco) > 0 else "N/A")
    with m3:
        ord_aco_col = st.selectbox("Ordenar por", colunas_ord_op, index=0, key="ord_aco_col")
    with m4:
        ord_aco_asc = st.selectbox("Ordem", ["Crescente", "Decrescente"], index=0, key="ord_aco_asc")

    acompanhar_df = acompanhar_df.sort_values(ord_aco_col, ascending=(ord_aco_asc == "Crescente"))

    if len(acompanhar_df) > 0:
        st.dataframe(
            acompanhar_df,
            use_container_width=True,
            height=600,
            hide_index=True,
            column_config={"Link de acesso": st.column_config.LinkColumn("Link", display_text="🔗 Abrir")}
        )
    else:
        st.info("Nenhum imóvel para acompanhar com os filtros atuais.")

# ========== TAB 3: DADOS ==========
with tab3:
    st.subheader(f"Tabela Completa — {len(df_filtrado):,} imóveis")

    colunas_ord_dados = ['Preço', 'Valor de avaliação', 'Desconto', 'Área Privativa (m²)', 'Área Terreno (m²)', 'Quartos', 'Andar', 'Cidade', 'Bairro', 'Tipo', 'Tier']
    c1, c2 = st.columns(2)
    with c1:
        ord_dados_col = st.selectbox("Ordenar por", colunas_ord_dados, index=0, key="ord_dados_col")
    with c2:
        ord_dados_asc = st.selectbox("Ordem", ["Crescente", "Decrescente"], index=0, key="ord_dados_asc")

    df_dados_ord = df_filtrado.sort_values(ord_dados_col, ascending=(ord_dados_asc == "Crescente"))

    st.dataframe(
        df_dados_ord,
        use_container_width=True,
        height=700,
        hide_index=True,
        column_config={
            "Link de acesso": st.column_config.LinkColumn("Link", display_text="🔗 Abrir")
        }
    )

    csv = df_filtrado.to_csv(index=False)
    st.download_button(
        label="Download CSV (filtrado)",
        data=csv,
        file_name=f"caixa_imoveis_{datetime.now().strftime('%d%m%Y')}.csv",
        mime="text/csv"
    )

# ==================== FOOTER ====================
st.divider()
st.caption(f"Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Cache: 1h")
