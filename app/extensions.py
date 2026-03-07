import pg8000.dbapi
import urllib.parse
import ssl
from config import Config

def get_db_connection():
    if not Config.DATABASE_URL:
        print("⚠️ Aviso: DATABASE_URL não configurada.")
        return None
    
    parsed = urllib.parse.urlparse(Config.DATABASE_URL)
    try:
        # O Neon EXIGE uma conexão segura. Isso cria o contexto SSL padrão.
        context = ssl.create_default_context()
        
        conn = pg8000.dbapi.connect(
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432, # Coloquei o 5432 como fallback de segurança
            database=parsed.path.lstrip('/'),
            ssl_context=context # <-- A mágica da segurança do Neon acontece aqui
        )
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar no PostgreSQL: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        return

    # Tabela de Usuários
    query_usuarios = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(50) UNIQUE NOT NULL,
        senha_hash VARCHAR(255) NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    # Tabela de Despesas (Adaptada para Neon)
    query_despesas = """
    CREATE TABLE IF NOT EXISTS despesas (
        id SERIAL PRIMARY KEY,
        descricao VARCHAR(255) NOT NULL,
        valor DECIMAL(10, 2) NOT NULL,
        data_vencimento DATE NOT NULL,
        data_pretensao DATE,
        responsavel_pagamento VARCHAR(50) NOT NULL,
        categoria VARCHAR(100),
        pago BOOLEAN DEFAULT FALSE,
        comprovante_dados BYTEA, 
        comprovante_mimetype VARCHAR(50),
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    # Tabela de Push
    query_push = """
    CREATE TABLE IF NOT EXISTS inscricoes_push (
        id SERIAL PRIMARY KEY,
        usuario VARCHAR(50) NOT NULL,
        subscription_info JSONB NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    try:
        cur = conn.cursor()
        cur.execute(query_usuarios)
        cur.execute(query_despesas)
        cur.execute(query_push)
        conn.commit()
        cur.close()
        print("✅ Tabelas do banco de dados verificadas/criadas com sucesso no Neon!")
    except Exception as e:
        print(f"❌ Erro ao inicializar o banco: {e}")
    finally:
        conn.close()

