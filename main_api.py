
import sqlite3
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, date

# --- Configuração do Banco de Dados ---
DATABASE_FILE = "lanchonete.db"

def inicializar_banco():
    """Cria as tabelas de vendas e sessões se elas não existirem."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # Tabela de Vendas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_venda TEXT NOT NULL,
            valor_produtos REAL NOT NULL,
            taxa_entrega REAL DEFAULT 0.0,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Tabela de Sessões do Caixa
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessoes_caixa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_abertura DATETIME NOT NULL,
            data_fechamento DATETIME,
            status TEXT NOT NULL -- 'aberto' ou 'fechado'
        );
    """)
    conn.commit()
    conn.close()

# --- Modelos de Dados (Pydantic) ---
class VendaEstabelecimento(BaseModel):
    valor: float

class VendaEntrega(BaseModel):
    valor_produtos: float
    taxa_entrega: float

# --- Aplicação FastAPI ---
app = FastAPI(
    title="API da Lanchonete",
    description="API para gerenciar sessões de caixa, registrar vendas e gerar relatórios.",
    version="2.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Inicializa o banco de dados na inicialização da aplicação."""
    inicializar_banco()

# --- Funções Auxiliares ---
def _calcular_relatorio_por_periodo(cursor, data_inicio, data_fim):
    """Função auxiliar para calcular e retornar as métricas de um período."""
    params = (data_inicio, data_fim)
    
    # Métricas de vendas no estabelecimento
    cursor.execute("SELECT SUM(valor_produtos) FROM vendas WHERE tipo_venda = 'estabelecimento' AND data_hora BETWEEN ? AND ?", params)
    total_vendas_estabelecimento = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT COUNT(id) FROM vendas WHERE tipo_venda = 'estabelecimento' AND data_hora BETWEEN ? AND ?", params)
    numero_vendas_estabelecimento = cursor.fetchone()[0] or 0

    # Métricas de vendas por entrega
    cursor.execute("SELECT SUM(valor_produtos) FROM vendas WHERE tipo_venda = 'entrega' AND data_hora BETWEEN ? AND ?", params)
    total_vendas_entrega_produtos = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(taxa_entrega) FROM vendas WHERE tipo_venda = 'entrega' AND data_hora BETWEEN ? AND ?", params)
    total_taxas_entrega = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT COUNT(id) FROM vendas WHERE tipo_venda = 'entrega' AND data_hora BETWEEN ? AND ?", params)
    numero_vendas_entrega = cursor.fetchone()[0] or 0

    valor_total_geral = total_vendas_estabelecimento + total_vendas_entrega_produtos + total_taxas_entrega

    return {
        "total_vendas_estabelecimento": total_vendas_estabelecimento,
        "total_vendas_entrega_produtos": total_vendas_entrega_produtos,
        "total_taxas_entrega": total_taxas_entrega,
        "valor_total_geral": valor_total_geral,
        "numero_vendas_estabelecimento": numero_vendas_estabelecimento,
        "numero_vendas_entrega": numero_vendas_entrega
    }
@app.get("/", tags=["Health Check"])
async def root():
    """Endpoint raiz para a verificação de saúde do Render."""
    return {"status": "API da Lanchonete está no ar!"}

# --- Endpoints de Gerenciamento do Caixa ---
@app.get("/caixa/status", tags=["Caixa"])
async def get_status_caixa():
    """Verifica e retorna o status atual do caixa (aberto ou fechado)."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT data_abertura FROM sessoes_caixa WHERE status = 'aberto' ORDER BY id DESC LIMIT 1")
    sessao_aberta = cursor.fetchone()
    conn.close()
    if sessao_aberta:
        return {"status": "aberto", "data_abertura": sessao_aberta[0]}
    return {"status": "fechado"}

@app.post("/caixa/abrir", tags=["Caixa"])
async def abrir_caixa():
    """Abre uma nova sessão de caixa."""
    status = await get_status_caixa()
    if status["status"] == "aberto":
        raise HTTPException(status_code=400, detail="Já existe um caixa aberto.")
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessoes_caixa (data_abertura, status) VALUES (?, ?)", (datetime.now(), 'aberto'))
    conn.commit()
    conn.close()
    return {"mensagem": "Caixa aberto com sucesso!"}

@app.post("/caixa/fechar", tags=["Caixa"])
async def fechar_caixa():
    """Fecha a sessão de caixa atual e gera um relatório para o período."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, data_abertura FROM sessoes_caixa WHERE status = 'aberto' ORDER BY id DESC LIMIT 1")
    sessao_aberta = cursor.fetchone()

    if not sessao_aberta:
        conn.close()
        raise HTTPException(status_code=400, detail="Nenhum caixa aberto para fechar.")

    sessao_id, data_abertura = sessao_aberta
    data_fechamento = datetime.now()

    cursor.execute("UPDATE sessoes_caixa SET data_fechamento = ?, status = ? WHERE id = ?", (data_fechamento, 'fechado', sessao_id))
    
    relatorio_sessao = _calcular_relatorio_por_periodo(cursor, data_abertura, data_fechamento)
    
    conn.commit()
    conn.close()
    
    return relatorio_sessao

# --- Endpoints de Vendas ---
@app.post("/vendas/estabelecimento", tags=["Vendas"])
async def registrar_venda_estabelecimento(venda: VendaEstabelecimento):
    """Registra uma nova venda realizada no estabelecimento."""
    status = await get_status_caixa()
    if status["status"] == "fechado":
        raise HTTPException(status_code=400, detail="O caixa está fechado. Abra o caixa para registrar vendas.")
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO vendas (tipo_venda, valor_produtos, data_hora) VALUES (?, ?, ?)",
        ('estabelecimento', venda.valor, datetime.now())
    )
    conn.commit()
    conn.close()
    return {"mensagem": "Venda no estabelecimento registrada com sucesso!"}

@app.post("/vendas/entrega", tags=["Vendas"])
async def registrar_venda_entrega(venda: VendaEntrega):
    """Registra uma nova venda por entrega."""
    status = await get_status_caixa()
    if status["status"] == "fechado":
        raise HTTPException(status_code=400, detail="O caixa está fechado. Abra o caixa para registrar vendas.")

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO vendas (tipo_venda, valor_produtos, taxa_entrega, data_hora) VALUES (?, ?, ?, ?)",
        ('entrega', venda.valor_produtos, venda.taxa_entrega, datetime.now())
    )
    conn.commit()
    conn.close()
    return {"mensagem": "Venda por entrega registrada com sucesso!"}

# --- Endpoint de Relatório ---
@app.get("/relatorio", tags=["Relatórios"])
async def gerar_relatorio(data_inicio: date = None, data_fim: date = None):
    """Gera um relatório de vendas, opcionalmente filtrado por data."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    if data_inicio and data_fim:
        # Adiciona a hora para cobrir o dia inteiro
        dt_inicio = datetime.combine(data_inicio, datetime.min.time())
        dt_fim = datetime.combine(data_fim, datetime.max.time())
        query_filter = " WHERE data_hora BETWEEN ? AND ?"
        params = (dt_inicio, dt_fim)
    else:
        query_filter = ""
        params = ()

    # Métricas de vendas no estabelecimento
    cursor.execute(f"SELECT SUM(valor_produtos) FROM vendas WHERE tipo_venda = 'estabelecimento'{query_filter.replace('WHERE', 'AND') if query_filter else ''}", params)
    total_vendas_estabelecimento = cursor.fetchone()[0] or 0.0
    cursor.execute(f"SELECT COUNT(id) FROM vendas WHERE tipo_venda = 'estabelecimento'{query_filter.replace('WHERE', 'AND') if query_filter else ''}", params)
    numero_vendas_estabelecimento = cursor.fetchone()[0] or 0

    # Métricas de vendas por entrega
    cursor.execute(f"SELECT SUM(valor_produtos) FROM vendas WHERE tipo_venda = 'entrega'{query_filter.replace('WHERE', 'AND') if query_filter else ''}", params)
    total_vendas_entrega_produtos = cursor.fetchone()[0] or 0.0
    cursor.execute(f"SELECT SUM(taxa_entrega) FROM vendas WHERE tipo_venda = 'entrega'{query_filter.replace('WHERE', 'AND') if query_filter else ''}", params)
    total_taxas_entrega = cursor.fetchone()[0] or 0.0
    cursor.execute(f"SELECT COUNT(id) FROM vendas WHERE tipo_venda = 'entrega'{query_filter.replace('WHERE', 'AND') if query_filter else ''}", params)
    numero_vendas_entrega = cursor.fetchone()[0] or 0
    
    conn.close()

    valor_total_geral = total_vendas_estabelecimento + total_vendas_entrega_produtos + total_taxas_entrega

    return {
        "total_vendas_estabelecimento": total_vendas_estabelecimento,
        "total_vendas_entrega_produtos": total_vendas_entrega_produtos,
        "total_taxas_entrega": total_taxas_entrega,
        "valor_total_geral": valor_total_geral,
        "numero_vendas_estabelecimento": numero_vendas_estabelecimento,
        "numero_vendas_entrega": numero_vendas_entrega
    }
