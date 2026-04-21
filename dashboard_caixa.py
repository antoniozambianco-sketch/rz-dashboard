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

# ==================== LIMITES GLOBAIS (para defaults dos number_inputs) ====================

preco_min_geral = int(df['Preço'].dropna().min())
preco_max_geral = int(df['Preço'].dropna().max())
aval_min_geral = int(df['Valor de avaliação'].dropna().min())
aval_max_geral = int(df['Valor de avaliação'].dropna().max())
area_terreno_min_geral = float(df['Área Terreno (m²)'].dropna().min() or 0)
area_terreno_max_geral = float(df['Área Terreno (m²)'].dropna().max() or 0)
area_priv_min_geral = float(df['Área Privativa (m²)'].dropna().min() or 0)
area_priv_max_geral = float(df['Área Privativa (m²)'].dropna().max() or 0)

# ==================== FILTROS (STAGED) ====================
# Widgets escrevem em staged_*; "Salvar" copia staged → filtros_aplicados.
# aplicar_filtros lê APENAS de filtros_aplicados → resultados só mudam ao salvar.

st.sidebar.header("Filtros")

def _ms(label, opcoes, key):
    """Multiselect com botões Todos / Nenhum acima."""
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Todos", key=f"_all_{key}"):
            st.session_state[key] = list(opcoes)
    with c2:
        if st.button("Nenhum", key=f"_none_{key}"):
            st.session_state[key] = []
    return st.multiselect(label, opcoes, key=key)

# ===== LOCALIZAÇÃO =====
with st.sidebar.expander("Localização", expanded=True):
    estados = sorted(df['UF'].dropna().unique().tolist())
    _ms("Estado (UF)", estados, "s_uf")
    st.text_input("Cidade (busca)", placeholder="ex: JOAO PESSOA", key="s_cidade")
    st.text_input("Bairro (busca)", placeholder="ex: CENTRO", key="s_bairro")
    st.divider()
    st.checkbox("Apenas Endereços Não Batidos", value=False, key="s_end_nao_batido")

# ===== ANÁLISE DE OPORTUNIDADE =====
with st.sidebar.expander("Análise de Oportunidade", expanded=False):
    tiers = sorted([t for t in df['Tier'].dropna().unique().tolist() if t != ""])
    _ms("Tier", tiers, "s_tiers")
    acoes = sorted([a for a in df['Ação'].dropna().unique().tolist() if a != ""])
    _ms("Ação", acoes, "s_acoes")

# ===== PREÇO & AVALIAÇÃO =====
with st.sidebar.expander("Preço & Avaliação", expanded=False):
    faixas = sorted([f for f in df['Faixa Preço'].dropna().unique().tolist() if f != ""])
    _ms("Faixa de Preço", faixas, "s_faixas")
    st.number_input("Preço Mín (R$)", value=preco_min_geral, step=1000, key="s_preco_min")
    st.number_input("Preço Máx (R$)", value=preco_max_geral, step=1000, key="s_preco_max")
    st.divider()
    st.number_input("Avaliação Mín (R$)", value=aval_min_geral, step=1000, key="s_aval_min")
    st.number_input("Avaliação Máx (R$)", value=aval_max_geral, step=1000, key="s_aval_max")

# ===== CARACTERÍSTICAS =====
with st.sidebar.expander("Características", expanded=False):
    tipos = sorted([t for t in df['Tipo'].dropna().unique().tolist() if t != ""])
    _ms("Tipo de Imóvel", tipos, "s_tipos")
    quartos_list = sorted([q for q in df['Quartos'].dropna().unique().tolist()])
    _ms("Quartos", quartos_list, "s_quartos")
    andares_list = sorted([a for a in df['Andar'].dropna().unique().tolist()])
    _ms("Andar", andares_list, "s_andares")
    st.checkbox("Tem Varanda", value=False, key="s_varanda")
    st.checkbox("Tem Vaga", value=False, key="s_vaga")
    st.divider()
    st.number_input("Terreno Mín (m²)", value=area_terreno_min_geral, step=10.0, key="s_at_min")
    st.number_input("Terreno Máx (m²)", value=area_terreno_max_geral, step=10.0, key="s_at_max")
    st.number_input("Privativa Mín (m²)", value=area_priv_min_geral, step=10.0, key="s_ap_min")
    st.number_input("Privativa Máx (m²)", value=area_priv_max_geral, step=10.0, key="s_ap_max")

# ===== MODALIDADE & PAGAMENTO =====
with st.sidebar.expander("Modalidade & Pagamento", expanded=False):
    if 'Modalidade de venda' in df.columns:
        modalidades = sorted([m for m in df['Modalidade de venda'].dropna().unique().tolist() if m != ""])
        _ms("Modalidade de Venda", modalidades, "s_modalidades")
    st.checkbox("Apenas Financiáveis", value=False, key="s_financiavel")

# ===== SALVAR / LIMPAR =====
st.sidebar.divider()
c1, c2 = st.sidebar.columns(2)
with c1:
    if st.button("💾 Salvar", type="primary", use_container_width=True):
        st.session_state['filtros_aplicados'] = {
            'uf':            st.session_state.get('s_uf', []),
            'cidade':        st.session_state.get('s_cidade', '').strip().upper(),
            'bairro':        st.session_state.get('s_bairro', '').strip().upper(),
            'end_nao_batido': st.session_state.get('s_end_nao_batido', False),
            'tiers':         st.session_state.get('s_tiers', []),
            'acoes':         st.session_state.get('s_acoes', []),
            'faixas':        st.session_state.get('s_faixas', []),
            'preco_min':     st.session_state.get('s_preco_min', preco_min_geral),
            'preco_max':     st.session_state.get('s_preco_max', preco_max_geral),
            'aval_min':      st.session_state.get('s_aval_min', aval_min_geral),
            'aval_max':      st.session_state.get('s_aval_max', aval_max_geral),
            'tipos':         st.session_state.get('s_tipos', []),
            'quartos':       st.session_state.get('s_quartos', []),
            'andares':       st.session_state.get('s_andares', []),
            'varanda':       st.session_state.get('s_varanda', False),
            'vaga':          st.session_state.get('s_vaga', False),
            'at_min':        st.session_state.get('s_at_min', area_terreno_min_geral),
            'at_max':        st.session_state.get('s_at_max', area_terreno_max_geral),
            'ap_min':        st.session_state.get('s_ap_min', area_priv_min_geral),
            'ap_max':        st.session_state.get('s_ap_max', area_priv_max_geral),
            'modalidades':   st.session_state.get('s_modalidades', []),
            'financiavel':   st.session_state.get('s_financiavel', False),
        }
        st.rerun()
with c2:
    if st.button("🗑 Limpar", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ==================== APLICAR FILTROS ====================
# Lê apenas de filtros_aplicados (estado salvo), nunca dos widgets diretamente.

fa = st.session_state.get('filtros_aplicados', {})

def _fa(key, default):
    return fa.get(key, default)

def aplicar_filtros(df_base, incluir_acao=True):
    d = df_base.copy()

    uf = _fa('uf', [])
    cidade = _fa('cidade', '')
    bairro = _fa('bairro', '')
    if uf:
        d = d[d['UF'].isin(uf)]
    if cidade:
        d = d[d['Cidade'].str.upper().str.contains(cidade, na=False)]
    if bairro:
        d = d[d['Bairro'].str.upper().str.contains(bairro, na=False)]
    if _fa('end_nao_batido', False):
        d = d[d['Endereço não batido'] == 'Sim']

    tiers_sel = _fa('tiers', [])
    acoes_sel = _fa('acoes', [])
    if tiers_sel:
        d = d[d['Tier'].isin(tiers_sel)]
    if incluir_acao and acoes_sel:
        d = d[d['Ação'].isin(acoes_sel)]

    faixas_sel = _fa('faixas', [])
    if faixas_sel:
        d = d[d['Faixa Preço'].isin(faixas_sel)]

    preco_min = _fa('preco_min', preco_min_geral)
    preco_max = _fa('preco_max', preco_max_geral)
    aval_min  = _fa('aval_min', aval_min_geral)
    aval_max  = _fa('aval_max', aval_max_geral)
    d = d[(d['Preço'] >= preco_min) & (d['Preço'] <= preco_max)]
    d = d[(d['Valor de avaliação'] >= aval_min) & (d['Valor de avaliação'] <= aval_max)]

    tipos_sel   = _fa('tipos', [])
    quartos_sel = _fa('quartos', [])
    andares_sel = _fa('andares', [])
    if tipos_sel:
        d = d[d['Tipo'].isin(tipos_sel)]
    if quartos_sel:
        d = d[d['Quartos'].isin(quartos_sel)]
    if andares_sel:
        d = d[d['Andar'].isin(andares_sel)]
    if _fa('varanda', False):
        d = d[d['Varanda'] == 'Sim']
    if _fa('vaga', False):
        d = d[d['Vaga'] == 'Sim']

    at_min = _fa('at_min', area_terreno_min_geral)
    at_max = _fa('at_max', area_terreno_max_geral)
    ap_min = _fa('ap_min', area_priv_min_geral)
    ap_max = _fa('ap_max', area_priv_max_geral)
    if at_min > area_terreno_min_geral or at_max < area_terreno_max_geral:
        d = d[d['Área Terreno (m²)'].isna() |
              ((d['Área Terreno (m²)'] >= at_min) & (d['Área Terreno (m²)'] <= at_max))]
    if ap_min > area_priv_min_geral or ap_max < area_priv_max_geral:
        d = d[d['Área Privativa (m²)'].isna() |
              ((d['Área Privativa (m²)'] >= ap_min) & (d['Área Privativa (m²)'] <= ap_max))]

    modal_sel = _fa('modalidades', [])
    if modal_sel:
        d = d[d['Modalidade de venda'].isin(modal_sel)]
    if _fa('financiavel', False):
        d = d[d['Financiamento'] == 'Sim']

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
    top_cidades = df_filtrado['Cidade'].value_counts().head(top_n).index.tolist()
    df_top = df_filtrado[df_filtrado['Cidade'].isin(top_cidades)].copy()
    cidade_faixa = (
        df_top.groupby(['Cidade', 'Faixa Preço'], observed=True)
        .size().reset_index(name='Quantidade')
    )
    total_por_cidade = df_filtrado['Cidade'].value_counts().head(top_n)
    faixas_order = sorted(cidade_faixa['Faixa Preço'].dropna().unique().tolist())
    altura_cidades = max(500, top_n * 20)
    fig_cidades = px.bar(
        cidade_faixa,
        x='Quantidade',
        y='Cidade',
        color='Faixa Preço',
        orientation='h',
        title=f"Top {top_n} Cidades por Faixa de Preço",
        barmode='stack',
        height=altura_cidades,
        color_discrete_sequence=px.colors.sequential.Plasma_r,
        category_orders={'Faixa Preço': faixas_order}
    )
    for cidade, total in total_por_cidade.items():
        fig_cidades.add_annotation(
            x=total, y=cidade,
            text=f"<b>{total:,}</b>",
            showarrow=False, xanchor='left', xshift=6,
            font=dict(size=13)
        )
    fig_cidades.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_range=[0, total_por_cidade.max() * 1.18],
        legend_title_text='Faixa'
    )
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
