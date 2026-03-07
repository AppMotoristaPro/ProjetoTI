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
        context = ssl.create_default_context()
        conn = pg8000.dbapi.connect(
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            ssl_context=context
        )
        # Força o fuso horário de Brasília direto na conexão
        cur = conn.cursor()
        cur.execute("SET TIME ZONE 'America/Sao_Paulo';")
        cur.close()
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar no PostgreSQL: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        return

    query_usuarios = "CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, nome VARCHAR(50) UNIQUE NOT NULL, senha_hash VARCHAR(255) NOT NULL, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
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
    query_rendas = "CREATE TABLE IF NOT EXISTS rendas (id SERIAL PRIMARY KEY, usuario VARCHAR(50) NOT NULL, valor DECIMAL(10, 2) DEFAULT 0.00, mes INT NOT NULL, ano INT NOT NULL);"
    query_push = "CREATE TABLE IF NOT EXISTS inscricoes_push (id SERIAL PRIMARY KEY, usuario VARCHAR(50) NOT NULL, subscription_info JSONB NOT NULL, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
    query_caixinhas = "CREATE TABLE IF NOT EXISTS caixinhas (id SERIAL PRIMARY KEY, nome VARCHAR(100) UNIQUE NOT NULL, valor DECIMAL(10, 2) DEFAULT 0.00, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"

    try:
        cur = conn.cursor()
        cur.execute(query_usuarios)
        cur.execute(query_despesas)
        cur.execute(query_rendas)
        cur.execute(query_push)
        cur.execute(query_caixinhas)
        
        # Colunas premium injetadas
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS recorrente BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS parcela_atual INT DEFAULT 1;")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS total_parcelas INT DEFAULT 1;")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS observacao TEXT;")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS icone_svg VARCHAR(50) DEFAULT 'geral';")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS fonte_pagamento VARCHAR(50);")
        
        cur.execute("ALTER TABLE rendas ADD COLUMN IF NOT EXISTS fonte VARCHAR(50) DEFAULT 'Geral';")
        
        # O pulo do gato: Ícones para as caixinhas!
        cur.execute("ALTER TABLE caixinhas ADD COLUMN IF NOT EXISTS icone_svg VARCHAR(50) DEFAULT 'geral';")
        
        try:
            cur.execute("ALTER TABLE rendas DROP CONSTRAINT IF EXISTS rendas_usuario_mes_ano_key;")
            cur.execute("ALTER TABLE rendas ADD CONSTRAINT rendas_usuario_fonte_mes_ano_key UNIQUE (usuario, fonte, mes, ano);")
        except Exception as e:
            pass
        
        conn.commit()
        cur.close()
        print("✅ Estrutura Big Tech atualizada com sucesso no Neon!")
    except Exception as e:
        print(f"❌ Erro ao inicializar o banco: {e}")
    finally:
        conn.close()

