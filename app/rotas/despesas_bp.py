import io
from flask import Blueprint, request, jsonify, send_file, render_template
from app.repositories.despesa_repository import DespesaRepository
from app.services.compressao_service import comprimir_arquivo

# Criando o Blueprint das despesas
despesas_bp = Blueprint('despesas', __name__)

# ==========================================
# 🖥️ ROTAS DE TELA (HTML)
# ==========================================

@despesas_bp.route('/nova-conta', methods=['GET'])
def tela_nova_conta():
    """Renderiza a tela bonita com o formulário Glassmorphism"""
    return render_template('despesas/nova_conta.html')

@despesas_bp.route('/historico', methods=['GET'])
def tela_historico():
    """Renderiza a tela de histórico com a listagem dinâmica"""
    return render_template('despesas/historico.html')


# ==========================================
# ⚙️ ROTAS DE API (O CÉREBRO)
# ==========================================

@despesas_bp.route('/api/despesas/nova', methods=['POST'])
def nova_despesa():
    # Pega todos os dados de texto do formulário e transforma num dicionário
    dados = request.form.to_dict()
    arquivo = request.files.get('comprovante')
    
    comprovante_binario = None
    mimetype = None
    
    # Se o usuário mandou um arquivo, passa pelo nosso espremedor!
    if arquivo and arquivo.filename:
        comprovante_binario, mimetype = comprimir_arquivo(arquivo)
        
    # Verifica se a caixinha "Conta já está paga?" foi marcada
    dados['pago'] = True if request.form.get('pago') == 'true' else False
        
    # Manda para o repositório salvar no banco de dados
    sucesso = DespesaRepository.criar(dados, comprovante_binario, mimetype)
    
    if sucesso:
        return jsonify({"status": "sucesso", "mensagem": "Despesa salva com sucesso!"}), 201
    else:
        return jsonify({"status": "erro", "mensagem": "Erro ao salvar despesa no banco."}), 500

@despesas_bp.route('/api/despesas', methods=['GET'])
def listar():
    """Retorna todas as despesas para preencher o Dashboard e o Histórico"""
    despesas = DespesaRepository.listar_todas()
    return jsonify(despesas), 200

@despesas_bp.route('/api/despesas/<int:despesa_id>/pagar', methods=['POST'])
def pagar_despesa(despesa_id):
    """Marca uma conta existente como paga"""
    sucesso = DespesaRepository.marcar_paga(despesa_id)
    if sucesso:
        return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/comprovante/<int:despesa_id>', methods=['GET'])
def ver_comprovante(despesa_id):
    """Devolve a imagem ou PDF direto do banco para a tela do celular"""
    bytes_dados, mimetype = DespesaRepository.obter_comprovante(despesa_id)
    
    if not bytes_dados:
        return "Comprovante não encontrado", 404
        
    # O send_file pega o binário do banco e cospe de volta como arquivo real
    return send_file(
        io.BytesIO(bytes_dados),
        mimetype=mimetype,
        as_attachment=False # False = Abre na tela. True = Força o download.
    )

