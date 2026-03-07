import datetime
from app.extensions import get_db_connection

class DespesaRepository:

    @staticmethod
    def _somar_meses(data_original, meses_a_somar):
        """Inteligência para pular meses no calendário lidando com anos bissextos e viradas de ano"""
        if not data_original:
            return None
        mes = data_original.month - 1 + meses_a_somar
        ano = data_original.year + mes // 12
        mes = mes % 12 + 1
        dia = min(data_original.day, [31, 29 if ano % 4 == 0 and (not ano % 100 == 0 or ano % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
        return datetime.date(ano, mes, dia)

    @staticmethod
    def criar(dados, comprovante_binario, mimetype):
        conn = get_db_connection()
        if not conn:
            raise Exception("Sem conexão com o banco de dados")
            
        try:
            cur = conn.cursor()
            
            recorrente = str(dados.get('recorrente', 'false')).lower() == 'true'
            parcela_inicial = int(dados.get('parcela_atual', 1))
            total_parcelas = int(dados.get('total_parcelas', 1))
            
            data_vencimento = datetime.datetime.strptime(dados.get('data_vencimento'), '%Y-%m-%d').date()
            data_pretensao = datetime.datetime.strptime(dados.get('data_pretensao'), '%Y-%m-%d').date() if dados.get('data_pretensao') else None
            
            # Se não for recorrente ou as parcelas estiverem erradas, cria só 1 vez
            parcelas_a_criar = total_parcelas - parcela_inicial + 1
            if not recorrente or parcelas_a_criar < 1:
                parcelas_a_criar = 1

            for i in range(parcelas_a_criar):
                nova_data_venc = DespesaRepository._somar_meses(data_vencimento, i)
                nova_data_pret = DespesaRepository._somar_meses(data_pretensao, i)
                p_atual = parcela_inicial + i
                
                # Identifica visualmente qual é a parcela na listagem
                descricao_final = dados.get('descricao')
                if recorrente and total_parcelas > 1:
                    descricao_final = f"{dados.get('descricao')} ({p_atual}/{total_parcelas})"
                
                # Só anexa o comprovante (e marca como paga) na primeira parcela inserida
                comp_bin = comprovante_binario if i == 0 else None
                comp_mime = mimetype if i == 0 else None
                status_pago = dados.get('pago', False) if i == 0 else False
                
                query = """
                    INSERT INTO despesas 
                    (descricao, valor, data_vencimento, data_pretensao, responsavel_pagamento, categoria, pago, 
                     comprovante_dados, comprovante_mimetype, recorrente, parcela_atual, total_parcelas)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cur.execute(query, (
                    descricao_final, dados.get('valor'), nova_data_venc, nova_data_pret,
                    dados.get('responsavel_pagamento'), dados.get('categoria', 'Geral'),
                    status_pago, comp_bin, comp_mime, recorrente, p_atual, total_parcelas
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
    def listar_por_mes(mes, ano):
        """Busca contas filtradas exatamente pelo mês e ano escolhido no celular"""
        conn = get_db_connection()
        if not conn:
            return []
            
        try:
            cur = conn.cursor()
            query = """
                SELECT id, descricao, valor, data_vencimento, data_pretensao, 
                       responsavel_pagamento, categoria, pago, recorrente, parcela_atual, total_parcelas,
                       (comprovante_dados IS NOT NULL) as tem_comprovante 
                FROM despesas 
                WHERE EXTRACT(MONTH FROM data_vencimento) = %s AND EXTRACT(YEAR FROM data_vencimento) = %s
                ORDER BY data_vencimento ASC
            """
            cur.execute(query, (mes, ano))
            colunas = [desc[0] for desc in cur.description]
            resultados = [dict(zip(colunas, row)) for row in cur.fetchall()]
            cur.close()
            return resultados
        finally:
            conn.close()

    @staticmethod
    def listar_todas():
        """Mantido como backup, mas o ideal é sempre usar listar_por_mes"""
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            query = "SELECT id, descricao, valor, data_vencimento, responsavel_pagamento, categoria, pago, (comprovante_dados IS NOT NULL) as tem_comprovante FROM despesas ORDER BY data_vencimento ASC"
            cur.execute(query)
            colunas = [desc[0] for desc in cur.description]
            return [dict(zip(colunas, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def salvar_renda(usuario, mes, ano, valor):
        """Salva ou atualiza o salário do Igor ou Thaynara para aquele mês específico"""
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            query = """
                INSERT INTO rendas (usuario, mes, ano, valor) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (usuario, mes, ano) 
                DO UPDATE SET valor = EXCLUDED.valor
            """
            cur.execute(query, (usuario, mes, ano, valor))
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            print(f"Erro ao salvar renda: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def obter_resumo(mes, ano):
        """O Cérebro Matemático: Soma salários e subtrai contas pendentes"""
        conn = get_db_connection()
        if not conn: return {}
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT usuario, valor FROM rendas WHERE mes = %s AND ano = %s", (mes, ano))
            rendas = {row[0]: float(row[1]) for row in cur.fetchall()}
            renda_igor = rendas.get('Igor', 0.0)
            renda_thaynara = rendas.get('Thaynara', 0.0)
            
            cur.execute("""
                SELECT responsavel_pagamento, SUM(valor) 
                FROM despesas 
                WHERE EXTRACT(MONTH FROM data_vencimento) = %s AND EXTRACT(YEAR FROM data_vencimento) = %s AND pago = FALSE
                GROUP BY responsavel_pagamento
            """, (mes, ano))
            
            pendentes = {row[0]: float(row[1]) for row in cur.fetchall()}
            pendente_igor = pendentes.get('Igor', 0.0)
            pendente_thaynara = pendentes.get('Thaynara', 0.0)
            
            total_renda = renda_igor + renda_thaynara
            total_pendente = pendente_igor + pendente_thaynara
            saldo_final = total_renda - total_pendente
            
            cur.close()
            return {
                "renda_igor": renda_igor,
                "renda_thaynara": renda_thaynara,
                "pendente_igor": pendente_igor,
                "pendente_thaynara": pendente_thaynara,
                "total_renda": total_renda,
                "total_pendente": total_pendente,
                "saldo_final": saldo_final
            }
        finally:
            conn.close()

    @staticmethod
    def obter_comprovante(despesa_id):
        conn = get_db_connection()
        if not conn: return None, None
        try:
            cur = conn.cursor()
            cur.execute("SELECT comprovante_dados, comprovante_mimetype FROM despesas WHERE id = %s", (despesa_id,))
            resultado = cur.fetchone()
            cur.close()
            if resultado and resultado[0]: return resultado[0], resultado[1]
            return None, None
        finally:
            conn.close()

    @staticmethod
    def marcar_paga(despesa_id, comprovante_binario=None, mimetype=None):
        """Marca a conta como paga e anexa o comprovante se ele for enviado!"""
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            
            if comprovante_binario:
                cur.execute("""
                    UPDATE despesas 
                    SET pago = TRUE, comprovante_dados = %s, comprovante_mimetype = %s 
                    WHERE id = %s
                """, (comprovante_binario, mimetype, despesa_id))
            else:
                cur.execute("UPDATE despesas SET pago = TRUE WHERE id = %s", (despesa_id,))
                
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            print(f"Erro ao marcar paga: {e}")
            return False
        finally:
            conn.close()

