from pywebpush import webpush, WebPushException
import json
import threading
from config import Config

class NotificacaoService:
    @staticmethod
    def enviar_notificacao(usuario, titulo, mensagem):
        # A MÁGICA DO SEGUNDO PLANO: Cria uma thread invisível para o envio do Push.
        # Assim, o celular não fica travado esperando o Google responder.
        thread = threading.Thread(target=NotificacaoService._processar_envio, args=(usuario, titulo, mensagem))
        thread.daemon = True
        thread.start()

    @staticmethod
    def _processar_envio(usuario, titulo, mensagem):
        # Importação feita aqui dentro para garantir que a thread tenha acesso ao banco
        from app.repositories.despesa_repository import DespesaRepository
        
        print(f"🚀 [PUSH ASYNC] Iniciando processo rápido para: {usuario}")
        try:
            inscricoes = DespesaRepository.obter_inscricoes(usuario)
            
            if not inscricoes:
                print(f"⚠️ [PUSH ASYNC] Nenhuma inscrição encontrada para {usuario}.")
                return

            payload = json.dumps({"title": titulo, "body": mensagem})
            endpoints_enviados = set()
            
            for inscricao in inscricoes:
                try:
                    sub_info = inscricao['subscription_info']
                    if isinstance(sub_info, str): 
                        sub_info = json.loads(sub_info)
                        
                    endpoint = sub_info.get('endpoint')
                    
                    if endpoint in endpoints_enviados: 
                        DespesaRepository.remover_inscricao_push(inscricao['id'])
                        continue
                        
                    endpoints_enviados.add(endpoint)
                    
                    # O timeout=10 evita que bibliotecas engasgadas travem tudo
                    webpush(
                        subscription_info=sub_info,
                        data=payload,
                        vapid_private_key=Config.VAPID_PRIVATE_KEY,
                        vapid_claims={"sub": Config.VAPID_CLAIM_EMAIL},
                        timeout=10 
                    )
                    print(f"✅ [PUSH ASYNC] Sucesso! Entregue para ID: {inscricao['id']}")
                    
                except WebPushException as e:
                    print(f"❌ [PUSH ASYNC] Erro WebPush (ID {inscricao['id']}): {e}")
                    if e.response is not None and e.response.status_code in [410, 404]:
                        print(f"🧹 [PUSH ASYNC] Limpando inscrição morta ID {inscricao['id']}.")
                        DespesaRepository.remover_inscricao_push(inscricao['id'])
                except Exception as e:
                    print(f"❌ [PUSH ASYNC] Erro geral ao disparar: {e}")
                    
        except Exception as e:
            print(f"❌ [PUSH ASYNC] Erro fatal na Thread de notificação: {e}")


