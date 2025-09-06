
import streamlit as st
import requests
from datetime import datetime, date

# --- Configuração da Aplicação ---
API_URL = "https://caixalanchonete-2.onrender.com"

st.set_page_config(
    page_title="Caixa da Lanchonete",
    page_icon="🍔",
    layout="wide"
)

# --- Funções de Lógica e API ---
def get_estado_caixa():
    """Busca o status atual do caixa na API."""
    try:
        response = requests.get(f"{API_URL}/caixa/status")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão com a API: {e}")
        return {"status": "erro"}

def exibir_relatorio(relatorio_data):
    """Exibe os dados de um relatório na tela principal."""
    st.subheader("Visão Geral Financeira")
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Valor Total Geral", f"R$ {relatorio_data['valor_total_geral']:.2f}")
    col2.metric("🏪 Vendas no Local", f"R$ {relatorio_data['total_vendas_estabelecimento']:.2f}")
    col3.metric("🛵 Produtos (Entrega)", f"R$ {relatorio_data['total_vendas_entrega_produtos']:.2f}")
    st.metric("💸 Total Taxas de Entrega", f"R$ {relatorio_data['total_taxas_entrega']:.2f}")

    st.subheader("Contagem de Vendas")
    col_count1, col_count2 = st.columns(2)
    col_count1.metric("Nº de Vendas no Local", relatorio_data['numero_vendas_estabelecimento'])
    col_count2.metric("Nº de Entregas", relatorio_data['numero_vendas_entrega'])

# --- Inicialização e Gerenciamento de Estado ---
if 'caixa_status' not in st.session_state:
    st.session_state.caixa_status = get_estado_caixa()

st.title("🍔 Sistema de Caixa da Lanchonete")

# --- Interface Principal ---
status_info = st.session_state.caixa_status

# SE O CAIXA ESTIVER ABERTO
if status_info.get("status") == "aberto":
    data_abertura_str = datetime.fromisoformat(status_info['data_abertura']).strftime('%d/%m/%Y às %H:%M:%S')
    st.success(f"🟢 Caixa Aberto desde {data_abertura_str}")

    # Ações na Sidebar
    st.sidebar.header("Ações do Caixa")
    if st.sidebar.button("Fechar Caixa e Gerar Relatório", type="primary"):
        try:
            response = requests.post(f"{API_URL}/caixa/fechar")
            response.raise_for_status()
            st.session_state.relatorio_sessao = response.json()
            st.session_state.caixa_status = get_estado_caixa() # Atualiza o status para 'fechado'
            st.rerun()
        except requests.exceptions.RequestException as e:
            st.sidebar.error(f"Erro ao fechar o caixa: {e.response.json()['detail']}")

    st.sidebar.divider()
    st.sidebar.header("Registrar Nova Venda")

    # Formulário de Venda no Estabelecimento
    with st.sidebar.form("venda_local_form", clear_on_submit=True):
        st.subheader("Venda no Estabelecimento")
        valor_local = st.number_input("Valor da Venda (R$)", min_value=0.01, format="%.2f")
        if st.form_submit_button("Registrar Venda Local"):
            try:
                response = requests.post(f"{API_URL}/vendas/estabelecimento", json={"valor": valor_local})
                response.raise_for_status()
                st.sidebar.success("Venda local registrada!")
            except requests.exceptions.RequestException as e:
                st.sidebar.error(f"Erro: {e.response.json()['detail']}")

    # Formulário de Venda por Entrega
    with st.sidebar.form("venda_entrega_form", clear_on_submit=True):
        st.subheader("Venda por Entrega (Delivery)")
        valor_produtos = st.number_input("Valor dos Produtos (R$)", min_value=0.01, format="%.2f")
        taxa_entrega = st.number_input("Taxa de Entrega (R$)", min_value=0.0, format="%.2f")
        if st.form_submit_button("Registrar Entrega"):
            try:
                response = requests.post(f"{API_URL}/vendas/entrega", json={"valor_produtos": valor_produtos, "taxa_entrega": taxa_entrega})
                response.raise_for_status()
                st.sidebar.success("Entrega registrada!")
            except requests.exceptions.RequestException as e:
                st.sidebar.error(f"Erro: {e.response.json()['detail']}")

# SE O CAIXA ESTIVER FECHADO
else:
    st.warning("🔴 Caixa Fechado")
    st.sidebar.header("Ações do Caixa")
    if st.sidebar.button("Abrir Caixa"):
        try:
            response = requests.post(f"{API_URL}/caixa/abrir")
            response.raise_for_status()
            st.session_state.caixa_status = get_estado_caixa() # Atualiza o status para 'aberto'
            st.session_state.pop('relatorio_sessao', None) # Limpa o relatório da sessão anterior
            st.rerun()
        except requests.exceptions.RequestException as e:
            st.sidebar.error(f"Erro ao abrir o caixa: {e.response.json()['detail']}")
    
    # Exibe o relatório da última sessão fechada, se existir
    if 'relatorio_sessao' in st.session_state:
        st.header("📊 Relatório da Última Sessão")
        exibir_relatorio(st.session_state.relatorio_sessao)

st.divider()

# --- Seção de Relatórios Históricos ---
st.header("🗓️ Relatório Histórico por Período")

col1, col2 = st.columns(2)
hoje = date.today()
data_inicio = col1.date_input("Data de Início", hoje)
data_fim = col2.date_input("Data de Fim", hoje)

if st.button("Gerar Relatório por Período"):
    if data_inicio > data_fim:
        st.error("A data de início não pode ser posterior à data de fim.")
    else:
        try:
            params = {"data_inicio": str(data_inicio), "data_fim": str(data_fim)}
            response = requests.get(f"{API_URL}/relatorio", params=params)
            response.raise_for_status()
            relatorio_periodo = response.json()
            st.subheader(f"Relatório de {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
            exibir_relatorio(relatorio_periodo)
        except requests.exceptions.RequestException as e:
            st.error(f"Erro ao buscar o relatório: {e}")
