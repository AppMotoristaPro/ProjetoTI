import io
import datetime
from flask import Blueprint, request, jsonify, send_file, render_template
from app.repositories.despesa_repository import DespesaRepository
from app.services.compressao_service import comprimir_arquivo

despesas_bp = Blueprint('despesas', __name__)

# ==========================================
# 🖥️ ROTAS DE TELA (HTML)
# ==========================================

@despesas_bp.route('/nova-conta', methods=['GET'])
def tela_nova_conta():
    return render_template('despesas/nova_conta.html')

@despesas_bp.route('/historico', methods=['GET'])
def tela_historico():
    return render_template('despesas/historico.html')

# ==========================================
# ⚙️ ROTAS DE API (O CÉREBRO)
# ==========================================

@despesas_bp.route('/api/despesas/nova', methods=['POST'])
def nova_despesa():
    dados = request.form.to_dict()
    arquivo = request.files.get('comprovante')
    
    comprovante_binario = None
    mimetype = None
    
    if arquivo and arquivo.filename:
        comprovante_binario, mimetype = comprimir_arquivo(arquivo)
        
    dados['pago'] = True if request.form.get('pago') == 'true' else False
        
    sucesso = DespesaRepository.criar(dados, comprovante_binario, mimetype)
    
    if sucesso:
        return jsonify({"status": "sucesso", "mensagem": "Despesa(s) salvas com sucesso!"}), 201
    else:
        return jsonify({"status": "erro", "mensagem": "Erro ao salvar despesa no banco."}), 500

@despesas_bp.route('/api/despesas', methods=['GET'])
def listar():
    mes = request.args.get('mes')
    ano = request.args.get('ano')
    
    if mes and ano:
        despesas = DespesaRepository.listar_por_mes(int(mes), int(ano))
    else:
        despesas = DespesaRepository.listar_todas()
        
    return jsonify(despesas), 200

@despesas_bp.route('/api/resumo', methods=['GET'])
def resumo():
    hoje = datetime.date.today()
    mes = int(request.args.get('mes', hoje.month))
    ano = int(request.args.get('ano', hoje.year))
    
    dados = DespesaRepository.obter_resumo(mes, ano)
    return jsonify(dados), 200

@despesas_bp.route('/api/rendas', methods=['POST'])
def atualizar_renda():
    dados = request.json
    usuario = dados.get('usuario')
    mes = dados.get('mes')
    ano = dados.get('ano')
    valor = dados.get('valor')
    
    sucesso = DespesaRepository.salvar_renda(usuario, mes, ano, valor)
    if sucesso:
        return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/api/despesas/<int:despesa_id>/pagar', methods=['POST'])
def pagar_despesa(despesa_id):
    """Nova versão turbinada: agora aceita receber a foto do comprovante direto do Dashboard!"""
    arquivo = request.files.get('comprovante')
    comprovante_binario = None
    mimetype = None
    
    if arquivo and arquivo.filename:
        comprovante_binario, mimetype = comprimir_arquivo(arquivo)
        
    sucesso = DespesaRepository.marcar_paga(despesa_id, comprovante_binario, mimetype)
    
    if sucesso:
        return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/comprovante/<int:despesa_id>', methods=['GET'])
def ver_comprovante(despesa_id):
    bytes_dados, mimetype = DespesaRepository.obter_comprovante(despesa_id)
    if not bytes_dados:
        return "Comprovante não encontrado", 404
        
    return send_file(
        io.BytesIO(bytes_dados),
        mimetype=mimetype,
        as_attachment=False
    )

