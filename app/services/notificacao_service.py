from pywebpush import webpush, WebPushException
import json
from config import Config
from app.repositories.despesa_repository import DespesaRepository

class NotificacaoService:
    @staticmethod
    def enviar_notificacao(usuario, titulo, mensagem):
        inscricoes = DespesaRepository.obter_inscricoes(usuario)
        payload = json.dumps({"title": titulo, "body": mensagem})
        
        for inscricao in inscricoes:
            try:
                webpush(
                    subscription_info=inscricao['subscription_info'],
                    data=payload,
                    vapid_private_key=Config.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": Config.VAPID_CLAIM_EMAIL}
                )
            except WebPushException as e:
                print(f"⚠️ Erro ao enviar Push para {usuario}: {e}")
                # Se o celular bloqueou ou o token expirou (Erro 410), exclui do banco
                if e.response and e.response.status_code == 410:
                    DespesaRepository.remover_inscricao_push(inscricao['id'])
            except Exception as e:
                print(f"⚠️ Erro geral no push: {e}")

