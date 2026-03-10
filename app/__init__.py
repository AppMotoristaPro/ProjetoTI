from flask import Flask
from config import Config
from app.extensions import init_db

# Importando os blueprints
from app.rotas.despesas_bp import despesas_bp
from app.rotas.dashboard_bp import dashboard_bp
from app.rotas.push_bp import push_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db()

    @app.route('/ping')
    def ping():
        return {"status": "ok", "mensagem": "Gestão TI está online e respirando!"}

    # Registrando os blueprints no aplicativo
    app.register_blueprint(despesas_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(push_bp)

    return app

