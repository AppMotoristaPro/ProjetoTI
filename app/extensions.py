import pg8000.dbapi
import urllib.parse
import ssl
import queue
import threading
from config import Config

class PooledConnection:
    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn

    def cursor(self): return self._conn.cursor()
    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self): self._pool.put_conn(self._conn)
    def __getattr__(self, name): return getattr(self._conn, name)

class DbPool:
    def __init__(self, minconn=2, maxconn=15):
        self.maxconn = maxconn
        self.pool = queue.Queue(maxsize=maxconn)
        self.lock = threading.Lock()
        self.current_conns = 0
        for _ in range(minconn):
            conn = self._create_conn()
            if conn: self.pool.put(conn)

    def _create_conn(self):
        if not Config.DATABASE_URL: return None
        parsed = urllib.parse.urlparse(Config.DATABASE_URL)
        try:
            context = ssl.create_default_context()
            conn = pg8000.dbapi.connect(
                user=parsed.username, password=parsed.password,
                host=parsed.hostname, port=parsed.port or 5432,
                database=parsed.path.lstrip('/'), ssl_context=context,
                timeout=10 
            )
            
            cur = conn.cursor()
            cur.execute("SET TIME ZONE 'America/Sao_Paulo';")
            cur.execute("SET statement_timeout = 10000;") 
            cur.close()
            
            with self.lock: self.current_conns += 1
            return conn
        except Exception as e:
            print(f"❌ Erro ao criar conexão: {e}")
            return None

    def get_conn(self):
        real_conn = None
        try:
            real_conn = self.pool.get(block=False)
        except queue.Empty:
            with self.lock:
                if self.current_conns < self.maxconn:
                    new_conn = self._create_conn()
                    if new_conn: return PooledConnection(self, new_conn)
            try:
                real_conn = self.pool.get(block=True, timeout=5)
            except queue.Empty:
                return None
        
        try:
            cur = real_conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return PooledConnection(self, real_conn)
        except Exception:
            try: real_conn.close()
            except: pass
            with self.lock: self.current_conns -= 1
            new_conn = self._create_conn()
            return PooledConnection(self, new_conn) if new_conn else None

    def put_conn(self, conn):
        try:
            self.pool.put(conn, block=False)
        except queue.Full:
            try: conn.close()
            except: pass
            with self.lock: self.current_conns -= 1

_db_pool = None

def get_db_connection():
    global _db_pool
    if not _db_pool:
        _db_pool = DbPool(minconn=2, maxconn=15)
    return _db_pool.get_conn()

def init_db():
    conn = get_db_connection()
    if not conn: return
    
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

    try:
        cur = conn.cursor()
        cur.execute(query_usuarios)
        cur.execute(query_despesas)
        cur.execute(query_rendas)
        cur.execute(query_push)
        
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS recorrente BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS parcela_atual INT DEFAULT 1;")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS total_parcelas INT DEFAULT 1;")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS observacao TEXT;")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS icone_svg VARCHAR(50) DEFAULT 'geral';")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS fonte_pagamento VARCHAR(50);")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS tipo_despesa VARCHAR(20) DEFAULT 'Variável';")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS grupo_id VARCHAR(50);")
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS data_pagamento DATE;")
        
        cur.execute("ALTER TABLE rendas ADD COLUMN IF NOT EXISTS fonte VARCHAR(50) DEFAULT 'Geral';")
        cur.execute("ALTER TABLE rendas ADD COLUMN IF NOT EXISTS data_recebimento DATE;")
        
        conn.commit()
        cur.close()
    except Exception as e: print(f"❌ Erro: {e}")
    finally:
        if conn: conn.close()

