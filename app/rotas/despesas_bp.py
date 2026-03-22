import io
import datetime
import json
from decimal import Decimal
from flask import Blueprint, request, jsonify, send_file, render_template, make_response
from app.repositories.despesa_repository import DespesaRepository
from app.services.compressao_service import comprimir_arquivo
from app.services.notificacao_service import NotificacaoService

# --- ENSINANDO O PYTHON A LER DINHEIRO ANTES DE EMPACOTAR ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)
# ------------------------------------------------------------

despesas_bp = Blueprint('despesas', __name__)

def hoje_br():
    return (datetime.datetime.utcnow() - datetime.timedelta(hours=3)).date()

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
    js = """
    self.addEventListener('install', (e) => { self.skipWaiting(); });
    self.addEventListener('activate', (e) => { e.waitUntil(clients.claim()); });
    self.addEventListener('push', function(e) {
        let data = {title: 'Despesas T&I', body: 'Nova movimentação registrada!'};
        if (e.data) { try { data = e.data.json(); } catch(err) { data.body = e.data.text(); } }
        const options = { body: data.body, icon: '/static/icons/icone.png', badge: '/static/icons/icone.png', vibrate: [200, 100, 200] };
        e.waitUntil(self.registration.showNotification(data.title, options));
    });
    self.addEventListener('notificationclick', function(e) {
        e.notification.close(); e.waitUntil(clients.openWindow('/'));
    });
    """
    response = make_response(js)
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

# --- MAGICA DA INJEÇÃO DIRETA (SSR) COM O ENCODER CORRETO ---
@despesas_bp.route('/', methods=['GET'])
def home(): 
    hoje = hoje_br()
    mes_atual = hoje.month
    ano_atual = hoje.year
    mes_ant = mes_atual - 1
    ano_ant = ano_atual
    if mes_ant == 0:
        mes_ant = 12
        ano_ant -= 1
    
    # Prepara o pacotão no backend antes de entregar a tela
    pacotao = DespesaRepository.obter_pacotao_dashboard(mes_atual, ano_atual, mes_ant, ano_ant)
    pacotao['mes_atual'] = mes_atual
    pacotao['ano_atual'] = ano_atual
    
    # Passa o pacotão como JSON (usando o DecimalEncoder que criamos)
    pacotao_json = json.dumps(pacotao, cls=DecimalEncoder)
    return render_template('dashboard/index.html', pacotao_inicial=pacotao_json)
# ------------------------------------------------------------

@despesas_bp.route('/historico', methods=['GET'])
def tela_historico(): return render_template('despesas/historico.html')
@despesas_bp.route('/carro', methods=['GET'])
def tela_carro(): return render_template('dashboard/carro.html')
@despesas_bp.route('/entradas', methods=['GET'])
def tela_entradas(): return render_template('dashboard/entradas.html')
@despesas_bp.route('/fixas', methods=['GET'])
def tela_fixas(): return render_template('despesas/fixas.html')
@despesas_bp.route('/variaveis', methods=['GET'])
def tela_variaveis(): return render_template('despesas/variaveis.html')

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
    if sucesso:
        autor = dados.get('autor_criacao', 'Igor')
        outro_usuario = "Thaynara" if autor == "Igor" else "Igor"
        valor_f = f"R$ {float(dados['valor']):.2f}".replace('.', ',')
        msg = f"{autor} adicionou uma conta {dados.get('tipo_despesa', 'Variável')}: {dados['descricao']} ({valor_f})"
        NotificacaoService.enviar_notificacao(outro_usuario, "💸 Nova Despesa Lançada!", msg)
        return jsonify({"status": "sucesso"}), 201
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

@despesas_bp.route('/api/calendario/marcacoes', methods=['GET'])
def listar_marcacoes():
    mes = request.args.get('mes'); ano = request.args.get('ano')
    if mes and ano: return jsonify(DespesaRepository.listar_dias_marcados(int(mes), int(ano))), 200
    return jsonify([]), 200

@despesas_bp.route('/api/calendario/marcar', methods=['POST'])
def marcar_dia():
    dados = request.json
    sucesso = DespesaRepository.marcar_dia(dados.get('data'), dados.get('usuario'), dados.get('tipo'))
    if sucesso: return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/api/dashboard/iniciar', methods=['GET'])
def iniciar_dashboard():
    hoje = hoje_br()
    mes = int(request.args.get('mes', hoje.month))
    ano = int(request.args.get('ano', hoje.year))
    mes_ant = mes - 1
    ano_ant = ano
    if mes_ant == 0:
        mes_ant = 12
        ano_ant -= 1
    pacotao = DespesaRepository.obter_pacotao_dashboard(mes, ano, mes_ant, ano_ant)
    return jsonify(pacotao), 200

@despesas_bp.route('/api/carro/iniciar', methods=['GET'])
def iniciar_carro():
    hoje = hoje_br()
    mes = int(request.args.get('mes', hoje.month))
    ano = int(request.args.get('ano', hoje.year))
    pacotao = DespesaRepository.obter_pacotao_carro(mes, ano)
    return jsonify(pacotao), 200

@despesas_bp.route('/api/sandero/config', methods=['GET', 'POST'])
def gerenciar_sandero_config():
    if request.method == 'GET':
        return jsonify(DespesaRepository.obter_sandero_config()), 200
    else:
        sucesso = DespesaRepository.salvar_sandero_config(request.json)
        return jsonify({"status": "sucesso" if sucesso else "erro"}), 200 if sucesso else 500

@despesas_bp.route('/api/sandero/diario', methods=['GET', 'POST'])
def gerenciar_sandero_diario():
    if request.method == 'GET':
        mes = request.args.get('mes'); ano = request.args.get('ano')
        return jsonify(DespesaRepository.listar_sandero_diario(int(mes), int(ano))), 200
    else:
        sucesso = DespesaRepository.salvar_sandero_diario(request.json)
        return jsonify({"status": "sucesso" if sucesso else "erro"}), 200 if sucesso else 500

@despesas_bp.route('/api/sandero/diario/<int:diario_id>', methods=['PUT', 'DELETE'])
def alterar_sandero_diario(diario_id):
    if request.method == 'DELETE':
        sucesso = DespesaRepository.excluir_sandero_diario(diario_id)
        return jsonify({"status": "sucesso" if sucesso else "erro"}), 200 if sucesso else 500
    else:
        sucesso = DespesaRepository.atualizar_sandero_diario(diario_id, request.json)
        return jsonify({"status": "sucesso" if sucesso else "erro"}), 200 if sucesso else 500

