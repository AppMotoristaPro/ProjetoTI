from pywebpush import webpush, WebPushException
import json
from config import Config
from app.repositories.despesa_repository import DespesaRepository

class NotificacaoService:
    @staticmethod
    def enviar_notificacao(usuario, titulo, mensagem):
        print(f"🔍 [PUSH LOG] Iniciando processo de envio para: {usuario}")
        inscricoes = DespesaRepository.obter_inscricoes(usuario)
        
        if not inscricoes:
            print(f"⚠️ [PUSH LOG] Nenhuma inscrição encontrada no banco para o usuário: {usuario}")
            return

        print(f"🔍 [PUSH LOG] Encontradas {len(inscricoes)} inscrições no banco para {usuario}. Preparando payload...")
        payload = json.dumps({"title": titulo, "body": mensagem})
        
        # O DETETIVE DE DUPLICATAS 🕵️‍♂️
        endpoints_processados = set()
        
        for inscricao in inscricoes:
            try:
                sub_info = inscricao['subscription_info']
                # Se o banco retornar string, converte pra dicionário
                if isinstance(sub_info, str):
                    sub_info = json.loads(sub_info)
                    
                endpoint = sub_info.get('endpoint')
                
                # --- SISTEMA DE AUTO-LIMPEZA ---
                if endpoint in endpoints_processados:
                    print(f"🧹 [PUSH LOG] Pulo de duplicata: Aparelho já recebeu. Removendo excesso (ID {inscricao['id']}) do banco.")
                    DespesaRepository.remover_inscricao_push(inscricao['id'])
                    continue
                    
                endpoints_processados.add(endpoint)
                # -------------------------------
                
                print(f"🔍 [PUSH LOG] Disparando para a inscrição ID: {inscricao['id']}")
                webpush(
                    subscription_info=sub_info,
                    data=payload,
                    vapid_private_key=Config.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": Config.VAPID_CLAIM_EMAIL}
                )
                print(f"✅ [PUSH LOG] Sucesso! Notificação enviada para {usuario} (ID: {inscricao['id']})")
                
            except WebPushException as e:
                print(f"❌ [PUSH LOG] Erro WebPushException ao enviar para {usuario}: {e}")
                if e.response is not None:
                    print(f"❌ [PUSH LOG] Código do erro: {e.response.status_code}")
                    if e.response.status_code in [410, 404]:
                        print(f"🧹 [PUSH LOG] Removendo inscrição inativa/expirada ID {inscricao['id']} do banco.")
                        DespesaRepository.remover_inscricao_push(inscricao['id'])
            except Exception as e:
                print(f"❌ [PUSH LOG] Erro geral de Python no push: {e}")

