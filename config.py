import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "chave-super-secreta-gestao-ti")
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    # Chaves para a Notificação Push (Web Push API)
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "BBN1tLnB8VQRegpxtWOXIcWzCKGDdI2Zvxu93Bdt64Tur25vnp_JnQw3vhN6pmyyxPMS8DBhrMuB4xajBF6b4Ps")
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "blGtF9rkYMmE_8dYLkmm1w8CeG0yVJRhmCHrA2J6q7Q")
    VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:igor@despesasti.com")
    
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

