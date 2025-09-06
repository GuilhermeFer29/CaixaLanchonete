
import streamlit as st
import requests
import pandas as pd

# --- Configuração da Aplicação ---
API_URL = "https://caixalanchonete-2.onrender.com"

st.set_page_config(
    page_title="Caixa da Lanchonete",
    page_icon="🍔",
    layout="wide"
)

# --- Interface do Usuário ---
st.title("🍔 Sistema de Caixa da Lanchonete")

# --- Sidebar para Registro de Vendas ---
st.sidebar.header("Registrar Nova Venda")

# Formulário de Venda no Estabelecimento
with st.sidebar.form("venda_local_form", clear_on_submit=True):
    st.subheader("Venda no Estabelecimento")
    valor_local = st.number_input("Valor da Venda (R$)", min_value=0.0, format="%.2f")
    submitted_local = st.form_submit_button("Registrar Venda Local")
    if submitted_local:
        if valor_local > 0:
            try:
                response = requests.post(
                    f"{API_URL}/vendas/estabelecimento",
                    json={"valor": valor_local}
                )
                response.raise_for_status()
                st.success("Venda local registrada com sucesso!")
            except requests.exceptions.RequestException as e:
                st.error(f"Erro ao registrar venda: {e}")
        else:
            st.warning("O valor da venda deve ser maior que zero.")

# Formulário de Venda por Entrega
with st.sidebar.form("venda_entrega_form", clear_on_submit=True):
    st.subheader("Venda por Entrega (Delivery)")
    valor_produtos_entrega = st.number_input("Valor dos Produtos (R$)", min_value=0.0, format="%.2f", key="produtos_entrega")
    taxa_entrega = st.number_input("Taxa de Entrega (R$)", min_value=0.0, format="%.2f", key="taxa_entrega")
    submitted_entrega = st.form_submit_button("Registrar Entrega")
    if submitted_entrega:
        if valor_produtos_entrega > 0:
            try:
                response = requests.post(
                    f"{API_URL}/vendas/entrega",
                    json={"valor_produtos": valor_produtos_entrega, "taxa_entrega": taxa_entrega}
                )
                response.raise_for_status()
                st.success("Venda por entrega registrada com sucesso!")
            except requests.exceptions.RequestException as e:
                st.error(f"Erro ao registrar entrega: {e}")
        else:
            st.warning("O valor dos produtos deve ser maior que zero.")


# --- Área Principal para Relatório ---
st.header("📊 Relatório de Caixa")

if st.button("Gerar e Atualizar Relatório"):
    try:
        response = requests.get(f"{API_URL}/relatorio")
        response.raise_for_status()
        relatorio = response.json()

        st.subheader("Visão Geral Financeira")
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Valor Total Geral", f"R$ {relatorio['valor_total_geral']:.2f}")
        col2.metric("🏪 Vendas no Local", f"R$ {relatorio['total_vendas_estabelecimento']:.2f}")
        col3.metric("🛵 Produtos (Entrega)", f"R$ {relatorio['total_vendas_entrega_produtos']:.2f}")
        st.metric("💸 Total Taxas de Entrega", f"R$ {relatorio['total_taxas_entrega']:.2f}")

        st.subheader("Contagem de Vendas")
        col_count1, col_count2 = st.columns(2)
        col_count1.metric("Nº de Vendas no Local", relatorio['numero_vendas_estabelecimento'])
        col_count2.metric("Nº de Entregas", relatorio['numero_vendas_entrega'])

    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar o relatório: {e}")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")
