#!/usr/bin/env python3
"""
Dashboard Streamlit - Análise de Imóveis Caixa Econômica
Dados ao vivo do Google Sheets

📚 REFERÊNCIA DE COLUNAS:
   Consulte: SHEETS_COLUMNS_REFERENCE.md
   - Descrição de todas as 25 colunas
   - Regras de Negócio (Tier, Ação)
   - Modalidades de Venda possíveis
   - Notas importantes sobre formato de dados

⚠️ IMPORTANTE:
   - Cidades vêm SEM ACENTO (JOAO PESSOA)
   - Desconto é percentual (0-100%), não valor em R$
   - Vaga: Sheets=número / Dashboard=Sim/Não (checkbox)
   - Endereços não batidos = count ≤ 5
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import re

st.set_page_config(page_title="Dashboard Caixa", layout="wide", initial_sidebar_state="expanded")

# ==================== CACHE & AUTENTICAÇÃO ====================

@st.cache_resource
def get_sheets_client():
    """Conecta ao Google Sheets — local usa arquivo, produção usa st.secrets"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    local_creds = r"C:\Users\antonio.zambianco_if\Desktop\Claude\credenciais.json"
    if os.path.exists(local_creds):
        creds = Credentials.from_service_account_file(local_creds, scopes=scopes)
    else:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
    return gspread.authorize(creds)

def convert_br_to_float(value):
    """Converte formato brasileiro (1.234,56) para float (1234.56)"""
    if pd.isna(value) or value == '' or value == 'nan':
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove "R$ " se existir
        value = value.replace('R$', '').strip()
        # Converte formato brasileiro: 1.234,56 -> 1234.56
        value = value.replace('.', '').replace(',', '.')
    try:
        return float(value)
    except:
        return None

@st.cache_data(ttl=3600)
def load_data():
    """Carrega dados do Sheets (cache 1 hora)"""
    try:
        client = get_sheets_client()
        spreadsheet = client.open_by_key("162QLT4L9eg0Q5AV63th88OGeow_12YlAWOpwn-UOLMY")
        sheet = spreadsheet.worksheet("IMOVEIS_ATUAL")

        # Pega todos os dados
        dados = sheet.get_all_values()
        headers = dados[0]

        # Converte pra DataFrame
        df = pd.DataFrame(dados[1:], columns=headers)

        # Converte tipos com função correta para valores brasileiros
        numeric_cols = ['Preço', 'Valor de avaliação', 'Desconto', 'Área Terreno (m²)', 'Área Privativa (m²)', 'Quartos', 'Andar']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(convert_br_to_float)

        # Converter colunas inteiras
        int_cols = ['Quartos', 'Andar']
        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')  # Int64 permite NaN

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

# ==================== HEADER ====================

st.title("📊 Dashboard Caixa Econômica")
st.markdown("**Análise em Tempo Real** | Imóveis para Leilão")

# Carrega dados
df = load_data()

if df is not None and len(df) > 0:

    # ==================== FILTROS ====================

    st.sidebar.header("🔍 Filtros")

    # ===== LOCALIZAÇÃO =====
    with st.sidebar.expander("📍 Localização", expanded=True):
        # Estado
        estados = sorted(df['UF'].dropna().unique().tolist())
        estados_selecionados = st.multiselect(
            "Estado (UF)",
            estados,
            default=st.session_state.get("estados_selecionados", estados),
            key="multiselect_uf"
        )
        st.session_state.estados_selecionados = estados_selecionados

        # Cidade (dinâmica baseado no estado)
        if len(estados_selecionados) > 0:
            df_estado = df[df['UF'].isin(estados_selecionados)]
            cidades = sorted(df_estado['Cidade'].dropna().unique().tolist())
        else:
            cidades = sorted(df['Cidade'].dropna().unique().tolist())

        # Garantir que seleção anterior é válida para a lista atual
        cidades_default = st.session_state.get("cidades_selecionadas", cidades)
        cidades_default = [c for c in cidades_default if c in cidades]  # Filtrar valores válidos
        if not cidades_default:
            cidades_default = cidades  # Se vazio, usar todos

        cidades_selecionadas = st.multiselect(
            "Cidade",
            cidades,
            default=cidades_default,
            key="multiselect_cidade"
        )
        st.session_state.cidades_selecionadas = cidades_selecionadas

        # Bairro (dinâmico baseado em estado + cidade)
        if len(estados_selecionados) > 0 and len(cidades_selecionadas) > 0:
            df_estado_cidade = df[(df['UF'].isin(estados_selecionados)) &
                                  (df['Cidade'].isin(cidades_selecionadas))]
            bairros = sorted([b for b in df_estado_cidade['Bairro'].dropna().unique().tolist() if b != ""])
        elif len(estados_selecionados) > 0:
            df_estado = df[df['UF'].isin(estados_selecionados)]
            bairros = sorted([b for b in df_estado['Bairro'].dropna().unique().tolist() if b != ""])
        else:
            bairros = sorted([b for b in df['Bairro'].dropna().unique().tolist() if b != ""])

        # Garantir que seleção anterior é válida para a lista atual
        bairros_default = st.session_state.get("bairros_selecionados", bairros)
        bairros_default = [b for b in bairros_default if b in bairros]  # Filtrar valores válidos
        if not bairros_default:
            bairros_default = bairros  # Se vazio, usar todos

        bairros_selecionados = st.multiselect(
            "Bairro",
            bairros,
            default=bairros_default,
            key="multiselect_bairro"
        )
        st.session_state.bairros_selecionados = bairros_selecionados

        st.divider()
        apenas_end_raro = st.checkbox(
            "Imóveis em Endereços Raros",
            value=st.session_state.get("apenas_end_raro", False),
            key="checkbox_endraro"
        )
        st.session_state.apenas_end_raro = apenas_end_raro
        end_raros_selecionados = ["Sim"] if apenas_end_raro else ["Sim", "Não"]

    # ===== ANÁLISE DE OPORTUNIDADE =====
    with st.sidebar.expander("🎯 Análise de Oportunidade", expanded=False):
        # Tier
        tiers = sorted([t for t in df['Tier'].dropna().unique().tolist() if t != ""])
        tiers_selecionados = st.multiselect(
            "Tier (JP)",
            tiers,
            default=st.session_state.get("tiers_selecionados", tiers),
            key="multiselect_tier"
        )
        st.session_state.tiers_selecionados = tiers_selecionados

        # Ação
        acoes = sorted([a for a in df['Ação'].dropna().unique().tolist() if a != ""])
        acoes_selecionadas = st.multiselect(
            "Ação",
            acoes,
            default=st.session_state.get("acoes_selecionadas", acoes),
            key="multiselect_acao"
        )
        st.session_state.acoes_selecionadas = acoes_selecionadas

    # ===== PREÇO & AVALIAÇÃO =====
    with st.sidebar.expander("💰 Preço & Avaliação", expanded=False):
        # Faixa de Preço
        faixas = sorted([f for f in df['Faixa Preço'].dropna().unique().tolist() if f != ""])
        faixas_selecionadas = st.multiselect(
            "Faixa de Preço",
            faixas,
            default=st.session_state.get("faixas_selecionadas", faixas),
            key="multiselect_faixa"
        )
        st.session_state.faixas_selecionadas = faixas_selecionadas

        # Preço (digitável)
        preco_min_geral = df['Preço'].dropna().min()
        preco_max_geral = df['Preço'].dropna().max()

        col_preco1, col_preco2 = st.columns(2)
        with col_preco1:
            preco_min_filtro = st.number_input(
                "Preço Mín (R$)",
                value=int(preco_min_geral),
                step=1000,
                key="preco_min"
            )
        with col_preco2:
            preco_max_filtro = st.number_input(
                "Preço Máx (R$)",
                value=int(preco_max_geral),
                step=1000,
                key="preco_max"
            )

        st.divider()

        # Avaliação (digitável)
        avaliacao_min_geral = df['Valor de avaliação'].dropna().min()
        avaliacao_max_geral = df['Valor de avaliação'].dropna().max()

        col_aval1, col_aval2 = st.columns(2)
        with col_aval1:
            avaliacao_min_filtro = st.number_input(
                "Avaliação Mín (R$)",
                value=int(avaliacao_min_geral),
                step=1000,
                key="aval_min"
            )
        with col_aval2:
            avaliacao_max_filtro = st.number_input(
                "Avaliação Máx (R$)",
                value=int(avaliacao_max_geral),
                step=1000,
                key="aval_max"
            )

    # ===== CARACTERÍSTICAS =====
    with st.sidebar.expander("🔧 Características", expanded=False):
        # Tipo
        tipos = sorted([t for t in df['Tipo'].dropna().unique().tolist() if t != ""])
        tipos_selecionados = st.multiselect(
            "Tipo de Imóvel",
            tipos,
            default=st.session_state.get("tipos_selecionados", tipos),
            key="multiselect_tipo"
        )
        st.session_state.tipos_selecionados = tipos_selecionados

        # Quartos
        quartos_list = sorted([q for q in df['Quartos'].dropna().unique().tolist()])
        quartos_selecionados = st.multiselect(
            "Quartos",
            quartos_list,
            default=st.session_state.get("quartos_selecionados", quartos_list),
            key="multiselect_quartos"
        )
        st.session_state.quartos_selecionados = quartos_selecionados

        # Andar
        andares_list = sorted([a for a in df['Andar'].dropna().unique().tolist()])
        andares_selecionados = st.multiselect(
            "Andar",
            andares_list,
            default=st.session_state.get("andares_selecionados", andares_list),
            key="multiselect_andar"
        )
        st.session_state.andares_selecionados = andares_selecionados

        # Varanda
        tem_varanda = st.checkbox(
            "Tem Varanda",
            value=st.session_state.get("tem_varanda", False),
            key="checkbox_varanda"
        )
        st.session_state.tem_varanda = tem_varanda
        varandas_selecionadas = ["Sim"] if tem_varanda else []

        # Vaga
        tem_vaga = st.checkbox(
            "Tem Vaga",
            value=st.session_state.get("tem_vaga", False),
            key="checkbox_vaga"
        )
        st.session_state.tem_vaga = tem_vaga
        vagas_selecionadas = ["Sim"] if tem_vaga else []

    # ===== MODALIDADE & PAGAMENTO =====
    with st.sidebar.expander("💳 Modalidade & Pagamento", expanded=False):
        # Modalidade de venda
        if 'Modalidade de venda' in df.columns:
            modalidades = sorted([m for m in df['Modalidade de venda'].dropna().unique().tolist() if m != ""])
            modalidades_selecionadas = st.multiselect(
                "Modalidade de Venda",
                modalidades,
                default=st.session_state.get("modalidades_selecionadas", modalidades),
                key="multiselect_modalidade"
            )
            st.session_state.modalidades_selecionadas = modalidades_selecionadas
        else:
            modalidades_selecionadas = []
            st.warning("⚠️ Coluna 'Modalidade de venda' não encontrada no Sheets")

        # Financiamento
        apenas_financiavel = st.checkbox(
            "Apenas Imóveis Financiáveis",
            value=st.session_state.get("apenas_financiavel", False),
            key="checkbox_financ"
        )
        st.session_state.apenas_financiavel = apenas_financiavel
        financiaveis_selecionados = ["Sim"] if apenas_financiavel else []

    # ==================== BOTÃO LIMPAR FILTROS ====================
    st.sidebar.divider()
    if st.sidebar.button("🔄 Limpar Todos os Filtros"):
        # Limpar todas as chaves de session_state
        keys_to_clear = [k for k in st.session_state.keys() if 'selecionados' in k or 'checkbox' in k or 'slider' in k]
        for key in keys_to_clear:
            del st.session_state[key]
        st.rerun()

    # ==================== APLICAR FILTROS ====================

    df_filtrado = df.copy()

    if len(tipos_selecionados) > 0:
        df_filtrado = df_filtrado[df_filtrado['Tipo'].isin(tipos_selecionados)]

    if len(estados_selecionados) > 0:
        df_filtrado = df_filtrado[df_filtrado['UF'].isin(estados_selecionados)]

    if len(cidades_selecionadas) > 0:
        df_filtrado = df_filtrado[df_filtrado['Cidade'].isin(cidades_selecionadas)]

    if len(bairros_selecionados) > 0:
        df_filtrado = df_filtrado[df_filtrado['Bairro'].isin(bairros_selecionados)]

    if len(acoes_selecionadas) > 0:
        df_filtrado = df_filtrado[df_filtrado['Ação'].isin(acoes_selecionadas)]

    if len(faixas_selecionadas) > 0:
        df_filtrado = df_filtrado[df_filtrado['Faixa Preço'].isin(faixas_selecionadas)]

    if len(tiers_selecionados) > 0:
        df_filtrado = df_filtrado[df_filtrado['Tier'].isin(tiers_selecionados)]

    if len(quartos_selecionados) > 0:
        df_filtrado = df_filtrado[df_filtrado['Quartos'].isin(quartos_selecionados)]

    if len(andares_selecionados) > 0:
        df_filtrado = df_filtrado[df_filtrado['Andar'].isin(andares_selecionados)]

    if len(varandas_selecionadas) > 0:
        df_filtrado = df_filtrado[df_filtrado['Varanda'].isin(varandas_selecionadas)]

    if len(vagas_selecionadas) > 0:
        df_filtrado = df_filtrado[df_filtrado['Vaga'].isin(vagas_selecionadas)]

    if len(modalidades_selecionadas) > 0:
        df_filtrado = df_filtrado[df_filtrado['Modalidade de venda'].isin(modalidades_selecionadas)]

    # Filtro de Preço
    df_filtrado = df_filtrado[(df_filtrado['Preço'] >= preco_min_filtro) & (df_filtrado['Preço'] <= preco_max_filtro)]

    # Filtro de Avaliação
    df_filtrado = df_filtrado[(df_filtrado['Valor de avaliação'] >= avaliacao_min_filtro) & (df_filtrado['Valor de avaliação'] <= avaliacao_max_filtro)]

    # Filtro de Endereço Raro
    if "Sim" in end_raros_selecionados and "Não" not in end_raros_selecionados:
        df_filtrado = df_filtrado[df_filtrado['Endereço Raro'] == 'Sim']
    elif "Não" in end_raros_selecionados and "Sim" not in end_raros_selecionados:
        df_filtrado = df_filtrado[df_filtrado['Endereço Raro'] != 'Sim']

    if len(financiaveis_selecionados) > 0:
        df_filtrado = df_filtrado[df_filtrado['Financiamento'].isin(financiaveis_selecionados)]

    st.sidebar.markdown(f"**Resultados: {len(df_filtrado):,} imóveis**")

    # ==================== ABAS ====================

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🌍 Geral", "🎯 Oportunidades", "🪟 Vitrine", "📋 Dados", "📚 Referência"])

    # ========== TAB 1: GERAL (VISÃO MACRO) ==========
    with tab1:
        st.subheader("📊 Visão Geral do Mercado")

        # Métricas gerais
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Imóveis", f"{len(df):,}")
        with col2:
            st.metric("Cidades Únicas", f"{df['Cidade'].nunique()}")
        with col3:
            st.metric("Endereços Raros", f"{(df['Endereço Raro'] == 'Sim').sum():,}")

        st.divider()

        # Cálculo correto de preços (filtrando valores válidos)
        preco_filtrado = df_filtrado['Preço'].dropna()
        preco_filtrado = preco_filtrado[preco_filtrado > 0]

        preco_medio = preco_filtrado.mean() if len(preco_filtrado) > 0 else 0
        preco_min = preco_filtrado.min() if len(preco_filtrado) > 0 else 0

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            aprofundar = (df_filtrado['Ação'] == 'aprofundar').sum()
            st.metric("Aprofundar", f"{aprofundar:,}")

        with col2:
            acompanhar = (df_filtrado['Ação'] == 'acompanhar').sum()
            st.metric("Acompanhar", f"{acompanhar:,}")

        with col3:
            st.metric("Preço Médio", f"R$ {preco_medio:,.0f}" if preco_medio > 0 else "N/A")

        with col4:
            st.metric("Preço Mínimo", f"R$ {preco_min:,.0f}" if preco_min > 0 else "N/A")

        st.divider()

        # Gráficos principais
        col1, col2 = st.columns(2)

        with col1:
            acao_counts = df_filtrado['Ação'].value_counts()
            fig_acao = px.pie(
                values=acao_counts.values,
                names=acao_counts.index,
                title="Distribuição por Ação",
                color_discrete_map={'aprofundar': '#00cc96', 'acompanhar': '#ffa15a'}
            )
            st.plotly_chart(fig_acao, width='stretch')

        with col2:
            tipo_counts = df_filtrado['Tipo'].value_counts()
            fig_tipo = px.bar(
                x=tipo_counts.index,
                y=tipo_counts.values,
                title="Distribuição por Tipo",
                labels={'x': 'Tipo', 'y': 'Quantidade'},
                color=tipo_counts.index,
                color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'],
                text_auto=True
            )
            fig_tipo.update_layout(showlegend=False)
            st.plotly_chart(fig_tipo, width='stretch')

        st.divider()

        # Cidades com filtro dinâmico
        st.subheader("📍 Distribuição por Cidade")
        top_n = st.selectbox("Mostrar Top N cidades", [30, 50, 100], index=0)

        col1, col2 = st.columns(2)

        with col1:
            cidade_counts = df_filtrado['Cidade'].value_counts().head(top_n)
            fig_cidades = px.bar(
                x=cidade_counts.values,
                y=cidade_counts.index,
                orientation='h',
                title=f"Top {top_n} Cidades",
                labels={'x': 'Quantidade', 'y': 'Cidade'},
                color=cidade_counts.values,
                color_continuous_scale='Viridis',
                text_auto=True
            )
            fig_cidades.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False)
            fig_cidades.update_traces(textposition='outside')
            st.plotly_chart(fig_cidades, width='stretch')

        with col2:
            # Distribuição por Faixa de Preço
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
            fig_faixa.update_layout(showlegend=False)
            st.plotly_chart(fig_faixa, width='stretch')

        # Tier (se houver)
        if 'Tier' in df_filtrado.columns and df_filtrado['Tier'].notna().any():
            tier_counts = df_filtrado[df_filtrado['Tier'] != '']['Tier'].value_counts()
            if len(tier_counts) > 0:
                fig_tier = px.pie(
                    values=tier_counts.values,
                    names=tier_counts.index,
                    title="Distribuição de Tiers (João Pessoa)"
                )
                st.plotly_chart(fig_tier, width='stretch')

    # ========== TAB 2: OPORTUNIDADES ==========
    with tab2:
        st.subheader("🎯 Análise de Oportunidades - Aprofundar")

        # Resumo de Aprofundar
        aprofundar_df = df_filtrado[df_filtrado['Ação'] == 'aprofundar'].copy()

        # Cálculo correto de preços para aprofundar
        preco_aprofundar = aprofundar_df['Preço'].dropna()
        preco_aprofundar = preco_aprofundar[preco_aprofundar > 0]

        aprofundar_df = aprofundar_df.sort_values('Preço')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Imóveis para Aprofundar", f"{len(aprofundar_df):,}")
        with col2:
            if len(preco_aprofundar) > 0:
                preco_medio_aprofundar = preco_aprofundar.mean()
                st.metric("Preço Médio", f"R$ {preco_medio_aprofundar:,.0f}")
        with col3:
            if len(preco_aprofundar) > 0:
                preco_max_aprofundar = preco_aprofundar.max()
                st.metric("Preço Máximo", f"R$ {preco_max_aprofundar:,.0f}")

        st.divider()

        if len(aprofundar_df) > 0:
            # Seleção dinâmica de colunas
            colunas_padroes = ['N° do imóvel', 'Cidade', 'Tipo', 'Quartos', 'Andar', 'Área Terreno (m²)', 'Área Privativa (m²)', 'Preço', 'Varanda', 'Vaga', 'Endereço Prédio', 'Faixa Preço', 'Tier', 'Endereço Raro', 'Link de acesso']
            colunas_disponiveis = aprofundar_df.columns.tolist()
            colunas_selecionadas = st.multiselect(
                "Selecione colunas para exibir",
                colunas_disponiveis,
                default=[col for col in colunas_padroes if col in colunas_disponiveis],
                key="tab2_colunas"
            )

            # Ordenação
            col1, col2 = st.columns(2)
            with col1:
                ordenar_por = st.selectbox("Ordenar por",
                    ["Preço (menor)", "Preço (maior)", "Avaliação (maior)", "Avaliação (menor)", "Desconto (maior)"],
                    key="tab2_order"
                )

            if ordenar_por == "Preço (menor)":
                aprofundar_df = aprofundar_df.sort_values('Preço', ascending=True)
            elif ordenar_por == "Preço (maior)":
                aprofundar_df = aprofundar_df.sort_values('Preço', ascending=False)
            elif ordenar_por == "Avaliação (maior)":
                aprofundar_df = aprofundar_df.sort_values('Valor de avaliação', ascending=False)
            elif ordenar_por == "Avaliação (menor)":
                aprofundar_df = aprofundar_df.sort_values('Valor de avaliação', ascending=True)
            elif ordenar_por == "Desconto (maior)":
                aprofundar_df = aprofundar_df.sort_values('Desconto', ascending=False)

            if colunas_selecionadas:
                # Remover Link de acesso da exibição da tabela (será mostrado como botões)
                # Filtrar apenas colunas que existem no DataFrame
                colunas_display = [col for col in colunas_selecionadas if col != 'Link de acesso' and col in aprofundar_df.columns]

                if colunas_display:
                    st.dataframe(
                        aprofundar_df[colunas_display].head(100),
                        width='stretch',
                        height=600,
                        hide_index=True
                    )

                # Adicionar botões para abrir links (se Link está nas colunas e existe no DataFrame)
                if 'Link de acesso' in colunas_selecionadas and 'Link de acesso' in aprofundar_df.columns:
                    st.subheader("📂 Abrir Links dos Imóveis")
                    cols = st.columns(5)
                    for idx, (_, row) in enumerate(aprofundar_df[['N° do imóvel', 'Link de acesso']].head(100).iterrows()):
                        col = cols[idx % 5]
                        with col:
                            if pd.notna(row['Link de acesso']) and row['Link de acesso'] != '':
                                st.markdown(f"[🔗 #{row['N° do imóvel']}]({row['Link de acesso']})")

            # Gráfico de Quartos removido temporariamente (UI/UX em revisão)
        else:
            st.warning("❌ Nenhum imóvel encontrado com Ação = 'aprofundar'")

    # ========== TAB 3: VITRINE ==========
    with tab3:
        st.subheader("🪟 Vitrine de Oportunidades")

        col1, col2 = st.columns(2)

        # Top 30 imóveis mais baratos
        with col1:
            st.subheader("💰 Top 30 Imóveis Mais Baratos")

            df_baratos = df.copy()
            df_baratos = df_baratos.dropna(subset=['Preço'])
            df_baratos = df_baratos[df_baratos['Preço'] > 0].nsmallest(30, 'Preço')

            colunas_baratos = ['N° do imóvel', 'Cidade', 'Tipo', 'Área Privativa (m²)', 'Preço', 'Ação', 'Andar']
            colunas_display = [col for col in colunas_baratos if col in df_baratos.columns]

            st.dataframe(
                df_baratos[colunas_display],
                width='stretch',
                hide_index=True
            )

            # Botões para abrir links (se Link de acesso existe no DataFrame)
            if 'Link de acesso' in df_baratos.columns:
                st.markdown("**Abrir Links:**")
                cols_links = st.columns(5)
                for idx, (_, row) in enumerate(df_baratos[['N° do imóvel', 'Link de acesso']].iterrows()):
                    col = cols_links[idx % 5]
                    with col:
                        if pd.notna(row['Link de acesso']) and row['Link de acesso'] != '':
                            st.markdown(f"[🔗 #{row['N° do imóvel']}]({row['Link de acesso']})")

        # Top 30 imóveis financiáveis com maior desconto
        with col2:
            st.subheader("🎁 Top 30 Maior Desconto (Financiáveis)")

            df_desconto = df.copy()
            df_desconto = df_desconto[df_desconto['Financiamento'].notna()]
            df_desconto = df_desconto[df_desconto['Financiamento'] != '']
            df_desconto = df_desconto.dropna(subset=['Desconto'])
            df_desconto = df_desconto.nlargest(30, 'Desconto')

            colunas_desc = ['N° do imóvel', 'Cidade', 'Tipo', 'Área Privativa (m²)', 'Preço', 'Desconto', 'Financiamento']
            colunas_display_desc = [col for col in colunas_desc if col in df_desconto.columns]

            st.dataframe(
                df_desconto[colunas_display_desc],
                width='stretch',
                hide_index=True
            )

            # Botões para abrir links (se Link de acesso existe no DataFrame)
            if 'Link de acesso' in df_desconto.columns:
                st.markdown("**Abrir Links:**")
                cols_links = st.columns(5)
                for idx, (_, row) in enumerate(df_desconto[['N° do imóvel', 'Link de acesso']].iterrows()):
                    col = cols_links[idx % 5]
                    with col:
                        if pd.notna(row['Link de acesso']) and row['Link de acesso'] != '':
                            st.markdown(f"[🔗 #{row['N° do imóvel']}]({row['Link de acesso']})")

    # ========== TAB 4: DADOS ==========
    with tab4:
        st.subheader("📋 Tabela Completa (Filtrada)")

        # Filtro de colunas - usar default apenas com colunas que existem
        colunas_disponiveis = df_filtrado.columns.tolist()
        colunas_padrao_tab4 = ['N° do imóvel', 'Cidade', 'UF', 'Bairro', 'Tipo', 'Preço', 'Ação', 'Tier', 'Andar']
        colunas_default = [col for col in colunas_padrao_tab4 if col in colunas_disponiveis]

        todas_colunas = st.multiselect(
            "Selecione colunas para exibir",
            colunas_disponiveis,
            default=colunas_default,
            key="tab4_colunas"
        )

        # Ordenação
        if todas_colunas:
            ordenar_por = st.selectbox("Ordenar por",
                ["Preço (menor)", "Preço (maior)", "Avaliação (maior)", "Avaliação (menor)", "Desconto (maior)"],
                key="tab4_order"
            )

            df_tabela = df_filtrado.copy()
            if ordenar_por == "Preço (menor)":
                df_tabela = df_tabela.sort_values('Preço', ascending=True)
            elif ordenar_por == "Preço (maior)":
                df_tabela = df_tabela.sort_values('Preço', ascending=False)
            elif ordenar_por == "Avaliação (maior)":
                df_tabela = df_tabela.sort_values('Valor de avaliação', ascending=False)
            elif ordenar_por == "Avaliação (menor)":
                df_tabela = df_tabela.sort_values('Valor de avaliação', ascending=True)
            elif ordenar_por == "Desconto (maior)":
                df_tabela = df_tabela.sort_values('Desconto', ascending=False)

            # Remover Link de acesso da exibição se estiver selecionado (Link será mostrado como botões)
            # Filtrar apenas colunas que existem no DataFrame
            colunas_display = [col for col in todas_colunas if col != 'Link de acesso' and col in df_tabela.columns]

            if colunas_display:
                st.dataframe(
                    df_tabela[colunas_display].head(200),
                    width='stretch',
                    height=600,
                    hide_index=True
                )

            # Botões para abrir links (se Link de acesso existe no DataFrame e foi selecionado)
            if 'Link de acesso' in todas_colunas and 'Link de acesso' in df_tabela.columns:
                st.markdown("---")
                st.subheader("📂 Abrir Links dos Imóveis")
                cols_links = st.columns(10)
                for idx, (_, row) in enumerate(df_tabela[['N° do imóvel', 'Link de acesso']].head(200).iterrows()):
                    col = cols_links[idx % 10]
                    with col:
                        if pd.notna(row['Link de acesso']) and row['Link de acesso'] != '':
                            st.markdown(f"[🔗 #{row['N° do imóvel']}]({row['Link de acesso']})")

        # Download CSV
        csv = df_filtrado.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV (Filtrado)",
            data=csv,
            file_name=f"caixa_imoveis_{datetime.now().strftime('%d%m%Y')}.csv",
            mime="text/csv"
        )

    # ========== TAB 5: REFERÊNCIA ===========
    with tab5:
        st.title("📚 Documentação - Colunas do Sheets")
        st.markdown("**Versão 1.2 (Final)** | Última atualização: 15/04/2026")

        st.divider()

        # Quick Reference
        with st.expander("⚡ Quick Reference (Resumido)", expanded=True):
            st.markdown("""
            ### 25 Colunas Finais

            **Originais (1-12):**
            N° imóvel • UF • Cidade • Bairro • Endereço • Preço • Avaliação • Desconto • Financiamento • Descrição • Modalidade de venda • Link de acesso

            **Extraídas (13-25):**
            Faixa Preço • Tipo • Quartos • Varanda • Vaga • Nº Apto • Endereço Prédio • Andar • Área Terreno (m²) • Área Privativa (m²) • Endereço Raro • Tier • Ação
            """)

        # Colunas Originais
        with st.expander("📋 Colunas Originais (Dados Brutos do CSV)", expanded=False):
            st.markdown("""
            | # | Coluna | Tipo | Descrição | Exemplo |
            |---|--------|------|-----------|---------|
            | 1 | **N° do imóvel** | String | ID único do leilão | 9336845 |
            | 2 | **UF** | String | Estado (PB, SP, RJ...) | PB |
            | 3 | **Cidade** | String | Município **[SEM ACENTO]** | JOAO PESSOA |
            | 4 | **Bairro** | String | Bairro/Localidade | CENTRO |
            | 5 | **Endereço** | String | Rua/Avenida + número | RUA DAS FLORES, N. 170 |
            | 6 | **Preço** | Float | Valor base (R$) | 45000.00 |
            | 7 | **Valor de avaliação** | Float | Avaliação (R$) | 50000.00 |
            | 8 | **Desconto** | Float | Percentual 0-100% **[NÃO R$]** | 10.5 |
            | 9 | **Financiamento** | String | Sim/Não/vazio | Sim |
            | 10 | **Descrição** | String | Detalhes do imóvel | "3 quartos, 1 varanda..." |
            | 11 | **Modalidade de venda** | String | Tipo de venda | Leilão SFI - Edital Único |
            | 12 | **Link de acesso** | String | URL do imóvel | https://caixa.gov.br/... |
            """)

        # Colunas Extraídas
        with st.expander("🔍 Colunas Extraídas (Processadas via Regex)", expanded=False):
            st.markdown("""
            **Área e Medidas:**
            - **Área Terreno (m²)**: Tamanho total (float)
            - **Área Privativa (m²)**: Apto/Casa (float)

            **Estrutura do Imóvel:**
            - **Quartos**: Número inteiro (int)
            - **Varanda**: Sim/vazio (string)
            - **Vaga**: Número (Sheets) / Sim/Não (Dashboard)

            **Localização:**
            - **Nº Apto**: Número do apto (string)
            - **Endereço Prédio**: Sem número de apto

            **Classificação:**
            - **Faixa Preço**: 8 faixas de preço
            - **Tipo**: Apto / Casa / Terreno / Outros
            - **Andar**: Número inteiro (0=Térreo, >20="Checar")
            - **Endereço Raro**: "Sim" se count ≤ 5
            - **Tier**: tier 1/2/3 (apenas JP + PB + Endereço raro)
            - **Ação**: aprofundar / acompanhar
            """)

        # Regras de Negócio
        with st.expander("🎯 Regras de Negócio (Tier & Ação)", expanded=False):
            st.markdown("""
            ### TIER (Apenas: Apto + João Pessoa + PB + Endereço não batido)
            **Ordem: Tier 1 (melhor) > Tier 2 > Tier 3**

            - **Tier 1**: 3Q + Térreo
            - **Tier 2**: 3Q/1-2 andar com vaga + outras combos
            - **Tier 3**: 2Q/1Q + vaga/varanda + outras combos

            ### AÇÃO (Baseada em Tier + Preço)
            - **Tier 1**: Preço ≤ 80k → aprofundar | > 80k → acompanhar
            - **Tier 2**: Preço ≤ 70k → aprofundar | > 70k → acompanhar
            - **Tier 3**: Preço ≤ 60k → aprofundar | > 60k → acompanhar
            """)

        # Modalidades
        with st.expander("📋 Modalidade de Venda (Valores Possíveis)", expanded=False):
            st.markdown("""
            | Modalidade | Descrição |
            |-----------|-----------|
            | **Leilão SFI - Edital Único** | Leilão padrão Caixa |
            | **Licitação Aberta** | Processo de licitação aberta |
            | **Venda Direta Online** | Venda direta via plataforma |
            | **Venda Online** | Venda online (variação) |
            """)

        # Notas Importantes
        with st.expander("⚠️ Notas Importantes", expanded=False):
            st.markdown("""
            1. **Formato Brasileiro:** Cidades SEM ACENTO (JOAO PESSOA)
            2. **Desconto:** Percentual 0-100%, **NÃO valor em R$**
            3. **Endereço Prédio:** Remove número de APTO apenas
            4. **Vaga:** Sheets = número / Dashboard = Sim/Não (checkbox)
            5. **Andar "Checar":** Se > 20 ou < 0
            6. **Ação Vazia:** Imóveis sem Tier não recebem ação
            """)

        # Estatísticas
        with st.expander("📊 Estatísticas (14/04/2026)", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Imóveis", "30.189")
                st.metric("Aptos", "17.601 (58%)")
                st.metric("Casas", "11.157 (37%)")
            with col2:
                st.metric("Endereços não batidos", "8.511")
                st.metric("JP c/ End. raro (Tier 1)", "1")
                st.metric("JP c/ End. raro (Tier 2)", "91")

else:
    st.error("❌ Erro ao carregar dados. Verifique a conexão com Google Sheets.")

# ==================== FOOTER ====================

st.divider()
st.caption(f"Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
