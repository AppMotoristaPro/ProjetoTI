from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # O Render usa a porta 10000 por padrão, e o Termux usa a que estiver livre (ex: 8080)
    port = int(os.environ.get('PORT', 8080))
    # host='0.0.0.0' é obrigatório para você conseguir acessar do navegador do celular
    app.run(host='0.0.0.0', port=port, debug=True)

