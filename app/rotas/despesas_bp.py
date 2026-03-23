import io
import datetime
import json
from decimal import Decimal
from flask import Blueprint, request, jsonify, send_file, render_template, make_response
from app.repositories.despesa_repository import DespesaRepository
from app.services.compressao_service import comprimir_arquivo
from app.services.notificacao_service import NotificacaoService

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

despesas_bp = Blueprint('despesas', __name__)

def hoje_br():
    return (datetime.datetime.utcnow() - datetime.timedelta(hours=3)).date()

def obter_usuario_atual():
    usuario_header = request.headers.get('X-Usuario-Atual')
    if usuario_header: return usuario_header
    
    if request.is_json and request.json:
        return request.json.get('autor_criacao') or request.json.get('usuario')
    if request.form:
        return request.form.get('autor_criacao') or request.form.get('usuario')
        
    return 'Igor' 

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
        const options = { 
            body: data.body, 
            icon: '/static/icons/icone.png', 
            badge: '/static/icons/badge_cifrao.png', 
            vibrate: [200, 100, 200] 
        };
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
    
    pacotao = DespesaRepository.obter_pacotao_dashboard(mes_atual, ano_atual, mes_ant, ano_ant)
    pacotao['mes_atual'] = mes_atual
    pacotao['ano_atual'] = ano_atual
    
    pacotao_json = json.dumps(pacotao, cls=DecimalEncoder)
    return render_template('dashboard/index.html', pacotao_inicial=pacotao_json)

@despesas_bp.route('/historico', methods=['GET'])
def tela_historico(): return render_template('despesas/historico.html')

@despesas_bp.route('/rotas', methods=['GET'])
def tela_rotas(): return render_template('dashboard/rotas.html')

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
        autor = obter_usuario_atual()
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
    
    data_rec = dados.get('data_recebimento')
    if not data_rec:
        mes = dados.get('mes', hoje_br().month)
        ano = dados.get('ano', hoje_br().year)
        data_rec = f"{ano}-{str(mes).zfill(2)}-01"
        
    sucesso = DespesaRepository.salvar_renda(dados.get('usuario'), dados.get('fonte', 'Geral'), data_rec, dados.get('valor'))
    if sucesso:
        autor = obter_usuario_atual()
        outro_usuario = "Thaynara" if autor == "Igor" else "Igor"
        valor_f = f"R$ {float(dados.get('valor', 0)):.2f}".replace('.', ',')
        quem_recebeu = dados.get('usuario')
        msg = f"💰 {autor} lançou: {dados.get('fonte', 'Geral')} para {quem_recebeu} ({valor_f})"
        NotificacaoService.enviar_notificacao(outro_usuario, "💰 Nova Entrada Registrada!", msg)
        return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/api/rendas/<int:renda_id>', methods=['DELETE', 'PUT'])
def alterar_renda(renda_id):
    autor = obter_usuario_atual()
    outro_usuario = "Thaynara" if autor == "Igor" else "Igor"
    
    if request.method == 'DELETE':
        if DespesaRepository.excluir_renda(renda_id): 
            NotificacaoService.enviar_notificacao(outro_usuario, "🗑️ Receita Excluída", f"{autor} apagou um registro de receita.")
            return jsonify({"status": "sucesso"}), 200
    else:
        dados = request.json
        if DespesaRepository.atualizar_renda(renda_id, dados.get('valor'), dados.get('data_recebimento')): 
            NotificacaoService.enviar_notificacao(outro_usuario, "✏️ Receita Alterada", f"{autor} modificou o valor de uma receita.")
            return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/api/despesas/<int:despesa_id>/pagar', methods=['POST'])
def pagar_despesa(despesa_id):
    arquivo = request.files.get('comprovante')
    comprovante_binario = None; mimetype = None
    if arquivo and arquivo.filename and arquivo.filename != '':
        try: comprovante_binario, mimetype = comprimir_arquivo(arquivo)
        except Exception: arquivo.seek(0); comprovante_binario = arquivo.read(); mimetype = arquivo.mimetype
    
    despesa = DespesaRepository.obter_por_id(despesa_id)
    sucesso = DespesaRepository.marcar_paga(despesa_id, comprovante_binario, mimetype)
    
    if sucesso:
        if despesa:
            autor = obter_usuario_atual()
            outro_usuario = "Thaynara" if autor == "Igor" else "Igor"
            valor_f = f"R$ {float(despesa['valor']):.2f}".replace('.', ',')
            msg = f"✅ {autor} pagou a conta: {despesa['descricao']} ({valor_f})"
            NotificacaoService.enviar_notificacao(outro_usuario, "✅ Conta Paga!", msg)
        return jsonify({"status": "sucesso"}), 200
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
    despesa = DespesaRepository.obter_por_id(despesa_id)
    sucesso = DespesaRepository.excluir(despesa_id, excluir_todas=lote)
    
    if sucesso:
        if despesa:
            autor = obter_usuario_atual()
            outro_usuario = "Thaynara" if autor == "Igor" else "Igor"
            valor_f = f"R$ {float(despesa['valor']):.2f}".replace('.', ',')
            msg = f"🗑️ {autor} excluiu a conta: {despesa['descricao']} ({valor_f})"
            NotificacaoService.enviar_notificacao(outro_usuario, "🗑️ Conta Excluída", msg)
        return jsonify({"status": "sucesso"}), 200
    return jsonify({"status": "erro"}), 500

@despesas_bp.route('/api/despesas/<int:despesa_id>/editar', methods=['PUT'])
def editar_despesa(despesa_id):
    despesa_antiga = DespesaRepository.obter_por_id(despesa_id)
    sucesso = DespesaRepository.atualizar(despesa_id, request.json)
    
    if sucesso:
        if despesa_antiga:
            autor = obter_usuario_atual()
            outro_usuario = "Thaynara" if autor == "Igor" else "Igor"
            msg = f"✏️ {autor} alterou a conta: {despesa_antiga['descricao']}"
            NotificacaoService.enviar_notificacao(outro_usuario, "✏️ Conta Alterada", msg)
        return jsonify({"status": "sucesso"}), 200
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

@despesas_bp.route('/api/rotas/iniciar', methods=['GET'])
def iniciar_rotas():
    hoje = hoje_br()
    mes = int(request.args.get('mes', hoje.month))
    ano = int(request.args.get('ano', hoje.year))
    pacotao = DespesaRepository.obter_pacotao_rotas(mes, ano)
    return jsonify(pacotao), 200

@despesas_bp.route('/api/rotas/dias', methods=['POST'])
def salvar_rotas_dias():
    dados = request.json
    mes = dados.get('mes'); ano = dados.get('ano'); dias = dados.get('dias')
    sucesso = DespesaRepository.salvar_rotas_dias(mes, ano, dias)
    return jsonify({"status": "sucesso" if sucesso else "erro"}), 200 if sucesso else 500

@despesas_bp.route('/api/rotas/config', methods=['POST'])
def salvar_rotas_config():
    sucesso = DespesaRepository.salvar_rotas_config(request.json)
    return jsonify({"status": "sucesso" if sucesso else "erro"}), 200 if sucesso else 500

