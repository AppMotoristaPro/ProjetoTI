from app.extensions import get_db_connection

class DespesaRepository:
    
    @staticmethod
    def criar(dados, comprovante_binario, mimetype):
        conn = get_db_connection()
        if not conn:
            raise Exception("Sem conexão com o banco de dados")
            
        try:
            cur = conn.cursor()
            query = """
                INSERT INTO despesas 
                (descricao, valor, data_vencimento, data_pretensao, responsavel_pagamento, categoria, comprovante_dados, comprovante_mimetype)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(query, (
                dados.get('descricao'),
                dados.get('valor'),
                dados.get('data_vencimento'),
                dados.get('data_pretensao'),
                dados.get('responsavel_pagamento'),
                dados.get('categoria', 'Geral'),
                comprovante_binario,
                mimetype
            ))
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            print(f"Erro no Repositório (Criar): {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def listar_todas():
        conn = get_db_connection()
        if not conn:
            return []
            
        try:
            cur = conn.cursor()
            # Traz tudo ordenado do vencimento mais próximo ao mais distante.
            # NOTA: Não trazemos o comprovante_dados aqui para o app não ficar lento carregando fotos atoa.
            query = """
                SELECT id, descricao, valor, data_vencimento, data_pretensao, 
                       responsavel_pagamento, categoria, pago, 
                       (comprovante_dados IS NOT NULL) as tem_comprovante 
                FROM despesas 
                ORDER BY data_vencimento ASC
            """
            cur.execute(query)
            
            # Transforma a resposta do banco em uma lista de dicionários para o Python entender fácil
            colunas = [desc[0] for desc in cur.description]
            resultados = [dict(zip(colunas, row)) for row in cur.fetchall()]
            
            cur.close()
            return resultados
        finally:
            conn.close()

    @staticmethod
    def obter_comprovante(despesa_id):
        """Busca os bytes da imagem/pdf para mostrar na tela"""
        conn = get_db_connection()
        if not conn:
            return None, None
            
        try:
            cur = conn.cursor()
            cur.execute("SELECT comprovante_dados, comprovante_mimetype FROM despesas WHERE id = %s", (despesa_id,))
            resultado = cur.fetchone()
            cur.close()
            
            if resultado and resultado[0]:
                return resultado[0], resultado[1] # Retorna (bytes, mimetype)
            return None, None
        finally:
            conn.close()

    @staticmethod
    def marcar_paga(despesa_id):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE despesas SET pago = TRUE WHERE id = %s", (despesa_id,))
            conn.commit()
            cur.close()
            return True
        finally:
            conn.close()

