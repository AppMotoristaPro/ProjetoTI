from flask import Blueprint, request, jsonify
from app.repositories.despesa_repository import DespesaRepository
from app.services.notificacao_service import NotificacaoService
import datetime

push_bp = Blueprint('push', __name__)

@push_bp.route('/api/push/subscribe', methods=['POST'])
def subscribe():
    dados = request.json
    usuario = dados.get('usuario')
    subscription = dados.get('subscription')
    
    if not usuario or not subscription:
        return jsonify({"erro": "Dados inválidos"}), 400
        
    sucesso = DespesaRepository.salvar_inscricao_push(usuario, subscription)
    if sucesso:
        return jsonify({"status": "Inscrição salva com sucesso!"}), 200
    return jsonify({"erro": "Erro ao salvar no banco"}), 500

# Rota Secreta: O Robô da Segunda-Feira
@push_bp.route('/api/push/cron/segunda', methods=['GET'])
def cron_segunda():
    contas = DespesaRepository.buscar_contas_proximos_7_dias()
    if not contas:
        return jsonify({"status": "Sem contas na semana."}), 200
        
    mensagem = "Vencimentos desta semana:\n"
    for c in contas:
        data_venc = str(c['data_vencimento'])
        partes = data_venc.split('-')
        data_br = f"{partes[2]}/{partes[1]}" if len(partes) == 3 else data_venc
        val = f"R$ {float(c['valor']):.2f}".replace('.', ',')
        
        mensagem += f"• {c['descricao']} ({val}) dia {data_br}\n"
        
    NotificacaoService.enviar_notificacao("Igor", "🗓️ Alerta de Contas", mensagem)
    NotificacaoService.enviar_notificacao("Thaynara", "🗓️ Alerta de Contas", mensagem)
    
    return jsonify({"status": "Avisos da semana enviados!"}), 200

# NOVA ROTA SECRETA: O Robô de Véspera (Acordar todo dia para checar amanhã)
@push_bp.route('/api/push/cron/amanha', methods=['GET'])
def cron_amanha():
    contas = DespesaRepository.buscar_contas_vencendo_amanha()
    if not contas:
        return jsonify({"status": "Sem contas para amanhã."}), 200
        
    mensagem = "Atenção para as contas que vencem amanhã:\n"
    for c in contas:
        val = f"R$ {float(c['valor']):.2f}".replace('.', ',')
        mensagem += f"• {c['descricao']} ({val}) - Paga por: {c['responsavel_pagamento']}\n"
        
    NotificacaoService.enviar_notificacao("Igor", "⏰ Vence Amanhã!", mensagem)
    NotificacaoService.enviar_notificacao("Thaynara", "⏰ Vence Amanhã!", mensagem)
    
    return jsonify({"status": "Avisos de amanhã enviados!"}), 200

# Rota Secreta: O Robô do Dia 1 (Lembrar Rendas)
@push_bp.route('/api/push/cron/dia1', methods=['GET'])
def cron_dia1():
    hoje = datetime.date.today()
    # if hoje.day != 1: return jsonify({"status": "Ainda não é dia 1"}), 200
        
    tem_renda = DespesaRepository.checar_rendas_mes(hoje.month, hoje.year)
    if not tem_renda:
        msg = "Viramos o mês! Não se esqueçam de lançar as entradas para atualizar o cálculo do Saldo Livre. 💸"
        NotificacaoService.enviar_notificacao("Igor", "Novo Mês!", msg)
        NotificacaoService.enviar_notificacao("Thaynara", "Novo Mês!", msg)
        return jsonify({"status": "Aviso de rendas enviado!"}), 200
        
    return jsonify({"status": "As rendas já estão preenchidas."}), 200

