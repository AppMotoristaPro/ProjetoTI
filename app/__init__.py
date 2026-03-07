from flask import Flask
from config import Config
from app.extensions import init_db

def create_app():
    # Inicializa o Flask
    app = Flask(__name__)
    
    # Carrega as senhas do config.py
    app.config.from_object(Config)

    # Cria as tabelas no Supabase assim que o app liga
    init_db()

    # Rota de teste rápida para sabermos se o app está vivo
    @app.route('/ping')
    def ping():
        return {"status": "ok", "mensagem": "Gestão TI está online e respirando!"}

    # As rotas oficias dos Blueprints vão entrar aqui no próximo passo!
from flask import Flask
from config import Config
from app.extensions import init_db

# Importando o blueprint
from app.rotas.despesas_bp import despesas_bp
from app.rotas.dashboard_bp import dashboard_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db()

    @app.route('/ping')
    def ping():
        return {"status": "ok", "mensagem": "Gestão TI está online e respirando!"}

    # Registrando o blueprint no aplicativo
    app.register_blueprint(despesas_bp)
    app.register_blueprint(dashboard_bp)

    return app

    return app

