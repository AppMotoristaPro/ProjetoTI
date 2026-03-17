import io
import datetime
from flask import Blueprint, request, jsonify, send_file, render_template, make_response
from app.repositories.despesa_repository import DespesaRepository
from app.services.compressao_service import comprimir_arquivo
from app.services.notificacao_service import NotificacaoService

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
    self.addEventListener('install', (e) => { 
        console.log('🔍 [SW LOG] Service Worker Instalado (V2 - Anti-Cache)!');
        self.skipWaiting(); 
    });
    
    self.addEventListener('activate', (e) => { 
        console.log('🔍 [SW LOG] Service Worker Ativado (V2)!');
        e.waitUntil(clients.claim()); 
    });
    
    self.addEventListener('push', function(e) {
        console.log('🔍 [SW LOG] EVENTO PUSH RECEBIDO NO CELULAR!');
        
        let data = {title: 'Despesas T&I', body: 'Nova movimentação registrada!'};
        
        if (e.data) {
            try {
                data = e.data.json();
            } catch(err) {
                console.log('⚠️ [SW LOG] JSON Parse error, usando texto simples.');
                data.body = e.data.text();
            }
        }

        const options = {
            body: data.body,
            icon: '/static/icons/icone.png',
            badge: '/static/icons/icone.png',
            vibrate: [200, 100, 200, 100, 200, 100, 200]
        };
        
        e.waitUntil(self.registration.showNotification(data.title, options));
    });
    
    self.addEventListener('notificationclick', function(e) {
        e.notification.close();
        e.waitUntil(clients.openWindow('/'));
    });
    """
    
    response = make_response(js)
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

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
        tipo = dados.get('tipo_despesa', 'Variável')
        
        msg = f"{autor} adicionou uma conta {tipo}: {dados['descricao']} ({valor_f})"
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

# NOVAS ROTAS PARA AS MARCAÇÕES DO CALENDÁRIO
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

