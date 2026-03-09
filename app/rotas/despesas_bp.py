import io
import datetime
from flask import Blueprint, request, jsonify, send_file, render_template
from app.repositories.despesa_repository import DespesaRepository
from app.services.compressao_service import comprimir_arquivo

despesas_bp = Blueprint('despesas', __name__)

def hoje_br():
    return (datetime.datetime.utcnow() - datetime.timedelta(hours=3)).date()

# --- ARQUIVOS PWA (INSTALAÇÃO APP) ---
@despesas_bp.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "Despesas T&I",
        "short_name": "Despesas T&I",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f4f6f9",
        "theme_color": "#4f46e5",
        "icons": [{
            "src": "/static/icons/icone.png", 
            "sizes": "512x512", 
            "type": "image/png",
            "purpose": "any maskable"
        }]
    })

@despesas_bp.route('/sw.js')
def sw():
    js = "self.addEventListener('install', (e) => { self.skipWaiting(); }); self.addEventListener('fetch', (e) => { });"
    return send_file(io.BytesIO(js.encode('utf-8')), mimetype='application/javascript')

# --- TELAS V2.0 ---
@despesas_bp.route('/', methods=['GET'])
def home(): return render_template('dashboard/index.html')
@despesas_bp.route('/historico', methods=['GET'])
def tela_historico(): return render_template('despesas/historico.html')
@despesas_bp.route('/caixinhas', methods=['GET'])
def tela_caixinhas(): return render_template('dashboard/caixinhas.html')
@despesas_bp.route('/entradas', methods=['GET'])
def tela_entradas(): return render_template('dashboard/entradas.html')
@despesas_bp.route('/fixas', methods=['GET'])
def tela_fixas(): return render_template('despesas/fixas.html')
@despesas_bp.route('/variaveis', methods=['GET'])
def tela_variaveis(): return render_template('despesas/variaveis.html')

# --- DESPESAS API ---
@despesas_bp.route('/api/despesas/nova', methods=['POST'])
def nova_despesa():
    dados = request.form.to_dict()
    arquivo = request.files.get('comprovante')
    comprovante_binario = None
    mimetype = None
    if arquivo and arquivo.filename and arquivo.filename != '':
        try: comprovante_binario, mimetype = comprimir_arquivo(arquivo)
        except Exception: arquivo.seek(0); comprovante_binario = arquivo.read(); mimetype = arquivo.mimetype
        
    dados['pago'] = True if request.form.get('pago') == 'true' else False
    sucesso = DespesaRepository.criar(dados, comprovante_binario, mimetype)
    if sucesso: return jsonify({"status": "sucesso"}), 201
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/api/despesas', methods=['GET'])
def listar():
    mes = request.args.get('mes'); ano = request.args.get('ano')
    if mes and ano: return jsonify(DespesaRepository.listar_por_mes(int(mes), int(ano))), 200
    return jsonify([]), 200

@despesas_bp.route('/api/resumo', methods=['GET'])
def resumo():
    hoje = hoje_br()
    mes = int(request.args.get('mes', hoje.month)); ano = int(request.args.get('ano', hoje.year))
    return jsonify(DespesaRepository.obter_resumo(mes, ano)), 200

# --- RENDAS API ---
@despesas_bp.route('/api/rendas/lista', methods=['GET'])
def listar_rendas():
    mes = request.args.get('mes'); ano = request.args.get('ano')
    return jsonify(DespesaRepository.listar_rendas_detalhadas(int(mes), int(ano))), 200

@despesas_bp.route('/api/rendas', methods=['POST'])
def atualizar_renda():
    dados = request.json
    sucesso = DespesaRepository.salvar_renda(dados.get('usuario'), dados.get('fonte', 'Geral'), dados.get('mes'), dados.get('ano'), dados.get('valor'))
    if sucesso: return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/api/rendas/<int:renda_id>', methods=['DELETE', 'PUT'])
def alterar_renda(renda_id):
    if request.method == 'DELETE':
        if DespesaRepository.excluir_renda(renda_id): return jsonify({"status": "sucesso"}), 200
    else:
        if DespesaRepository.atualizar_renda(renda_id, request.json.get('valor')): return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

# --- CAIXINHAS API ---
@despesas_bp.route('/api/caixinhas', methods=['GET', 'POST'])
def gerenciar_caixinhas():
    if request.method == 'GET': return jsonify(DespesaRepository.listar_caixinhas()), 200
    else:
        dados = request.json
        if DespesaRepository.salvar_caixinha(dados.get('nome'), dados.get('valor'), dados.get('icone_svg', 'geral')): return jsonify({"status": "sucesso"}), 200
        return jsonify({"status": "erro"}), 500

@despesas_bp.route('/api/caixinhas/<int:caixinha_id>/depositar', methods=['POST'])
def depositar_caixinha(caixinha_id):
    if DespesaRepository.depositar_caixinha(caixinha_id, request.json.get('valor')): return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/api/caixinhas/<int:caixinha_id>', methods=['DELETE', 'PUT'])
def alterar_caixinha(caixinha_id):
    if request.method == 'DELETE':
        if DespesaRepository.excluir_caixinha(caixinha_id): return jsonify({"status": "sucesso"}), 200
    else:
        dados = request.json
        if DespesaRepository.atualizar_caixinha(caixinha_id, dados.get('nome'), dados.get('valor'), dados.get('icone_svg')): return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

# --- PAGAMENTOS API ---
@despesas_bp.route('/api/despesas/<int:despesa_id>/pagar', methods=['POST'])
def pagar_despesa(despesa_id):
    arquivo = request.files.get('comprovante')
    comprovante_binario = None; mimetype = None
    if arquivo and arquivo.filename and arquivo.filename != '':
        try: comprovante_binario, mimetype = comprimir_arquivo(arquivo)
        except Exception: arquivo.seek(0); comprovante_binario = arquivo.read(); mimetype = arquivo.mimetype
    sucesso = DespesaRepository.marcar_paga(despesa_id, comprovante_binario, mimetype)
    if sucesso: return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/api/despesas/<int:despesa_id>/desfazer', methods=['POST'])
def desfazer_pagamento(despesa_id):
    if DespesaRepository.desfazer_pagamento(despesa_id): return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/comprovante/<int:despesa_id>', methods=['GET'])
def ver_comprovante(despesa_id):
    bytes_dados, mimetype = DespesaRepository.obter_comprovante(despesa_id)
    if not bytes_dados: return "Não encontrado", 404
    return send_file(io.BytesIO(bytes_dados), mimetype=mimetype, as_attachment=False)

@despesas_bp.route('/api/despesas/<int:despesa_id>', methods=['DELETE'])
def deletar_despesa(despesa_id):
    lote = request.args.get('todas') == 'true'
    sucesso = DespesaRepository.excluir(despesa_id, excluir_todas=lote)
    if sucesso: return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/api/despesas/<int:despesa_id>/editar', methods=['PUT'])
def editar_despesa(despesa_id):
    if DespesaRepository.atualizar(despesa_id, request.json): return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

