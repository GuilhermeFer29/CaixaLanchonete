
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime

# --- Configuração do Banco de Dados ---
DATABASE_FILE = "lanchonete.db"

def inicializar_banco():
    """Cria a tabela de vendas se ela não existir."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_venda TEXT NOT NULL,
            valor_produtos REAL NOT NULL,
            taxa_entrega REAL DEFAULT 0.0,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
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
    description="API para registrar vendas e gerar relatórios.",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Inicializa o banco de dados na inicialização da aplicação."""
    inicializar_banco()

# --- Endpoints da API ---
@app.post("/vendas/estabelecimento", tags=["Vendas"])
async def registrar_venda_estabelecimento(venda: VendaEstabelecimento):
    """Registra uma nova venda realizada no estabelecimento."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO vendas (tipo_venda, valor_produtos) VALUES (?, ?)",
            ('estabelecimento', venda.valor)
        )
        conn.commit()
        conn.close()
        return {"mensagem": "Venda no estabelecimento registrada com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao registrar venda: {e}")

@app.post("/vendas/entrega", tags=["Vendas"])
async def registrar_venda_entrega(venda: VendaEntrega):
    """Registra uma nova venda por entrega."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO vendas (tipo_venda, valor_produtos, taxa_entrega) VALUES (?, ?, ?)",
            ('entrega', venda.valor_produtos, venda.taxa_entrega)
        )
        conn.commit()
        conn.close()
        return {"mensagem": "Venda por entrega registrada com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao registrar venda: {e}")

@app.get("/relatorio", tags=["Relatórios"])
async def gerar_relatorio():
    """Gera um relatório consolidado com as métricas de vendas."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Métricas de vendas no estabelecimento
        cursor.execute("SELECT SUM(valor_produtos) FROM vendas WHERE tipo_venda = 'estabelecimento'")
        total_vendas_estabelecimento = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT COUNT(id) FROM vendas WHERE tipo_venda = 'estabelecimento'")
        numero_vendas_estabelecimento = cursor.fetchone()[0] or 0

        # Métricas de vendas por entrega
        cursor.execute("SELECT SUM(valor_produtos) FROM vendas WHERE tipo_venda = 'entrega'")
        total_vendas_entrega_produtos = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT SUM(taxa_entrega) FROM vendas WHERE tipo_venda = 'entrega'")
        total_taxas_entrega = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT COUNT(id) FROM vendas WHERE tipo_venda = 'entrega'")
        numero_vendas_entrega = cursor.fetchone()[0] or 0

        conn.close()

        # Cálculo do valor total geral
        valor_total_geral = total_vendas_estabelecimento + total_vendas_entrega_produtos + total_taxas_entrega

        return {
            "total_vendas_estabelecimento": total_vendas_estabelecimento,
            "total_vendas_entrega_produtos": total_vendas_entrega_produtos,
            "total_taxas_entrega": total_taxas_entrega,
            "valor_total_geral": valor_total_geral,
            "numero_vendas_estabelecimento": numero_vendas_estabelecimento,
            "numero_vendas_entrega": numero_vendas_entrega
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {e}")
