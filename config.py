import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (útil para quando você for testar no Termux)
load_dotenv()

class Config:
    # 1. Configurações Básicas
    SECRET_KEY = os.environ.get("SECRET_KEY", "chave-super-secreta-gestao-ti")
    
    # 2. Banco de Dados
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    # 3. Chaves para a Notificação Push (Web Push API)
    # Lendo apenas das variáveis de ambiente para proteção contra vazamentos
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
    VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:igor@despesasti.com")
    
    # 4. Segurança de Upload
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

