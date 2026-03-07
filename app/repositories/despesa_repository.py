import datetime
from app.extensions import get_db_connection

class DespesaRepository:

    @staticmethod
    def _somar_meses(data_original, meses_a_somar):
        if not data_original: return None
        mes = data_original.month - 1 + meses_a_somar
        ano = data_original.year + mes // 12
        mes = mes % 12 + 1
        dia = min(data_original.day, [31, 29 if ano % 4 == 0 and (not ano % 100 == 0 or ano % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
        return datetime.date(ano, mes, dia)

    @staticmethod
    def criar(dados, comprovante_binario, mimetype):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            recorrente = str(dados.get('recorrente', 'false')).lower() == 'true'
            parcela_inicial = int(dados.get('parcela_atual', 1))
            total_parcelas = int(dados.get('total_parcelas', 1))
            
            data_vencimento = datetime.datetime.strptime(dados.get('data_vencimento'), '%Y-%m-%d').date()
            data_pretensao = datetime.datetime.strptime(dados.get('data_pretensao'), '%Y-%m-%d').date() if dados.get('data_pretensao') else None
            
            parcelas_a_criar = total_parcelas - parcela_inicial + 1
            if not recorrente or parcelas_a_criar < 1: parcelas_a_criar = 1

            for i in range(parcelas_a_criar):
                nova_data_venc = DespesaRepository._somar_meses(data_vencimento, i)
                nova_data_pret = DespesaRepository._somar_meses(data_pretensao, i)
                p_atual = parcela_inicial + i
                
                # NOME PURO: Sem misturar as parcelas no nome da conta!
                descricao_final = dados.get('descricao')
                
                comp_bin = comprovante_binario if i == 0 else None
                comp_mime = mimetype if i == 0 else None
                status_pago = dados.get('pago', False) if i == 0 else False
                
                query = """
                    INSERT INTO despesas 
                    (descricao, valor, data_vencimento, data_pretensao, responsavel_pagamento, categoria, pago, 
                     comprovante_dados, comprovante_mimetype, recorrente, parcela_atual, total_parcelas, observacao, icone_svg, fonte_pagamento)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cur.execute(query, (
                    descricao_final, dados.get('valor'), nova_data_venc, nova_data_pret, dados.get('responsavel_pagamento'), 
                    dados.get('categoria', 'Geral'), status_pago, comp_bin, comp_mime, recorrente, p_atual, total_parcelas,
                    dados.get('observacao', ''), dados.get('icone_svg', 'geral'), dados.get('fonte_pagamento')
                ))
                
            conn.commit()
            cur.close()
            return True
        except Exception as e: return False
        finally: conn.close()

    @staticmethod
    def listar_por_mes(mes, ano):
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            query = """
                SELECT id, descricao, valor, data_vencimento, data_pretensao, 
                       responsavel_pagamento, categoria, pago, recorrente, parcela_atual, total_parcelas,
                       observacao, icone_svg, fonte_pagamento, (comprovante_dados IS NOT NULL) as tem_comprovante 
                FROM despesas 
                WHERE EXTRACT(MONTH FROM data_vencimento) = %s AND EXTRACT(YEAR FROM data_vencimento) = %s
                ORDER BY data_vencimento ASC
            """
            cur.execute(query, (mes, ano))
            colunas = [desc[0] for desc in cur.description]
            return [dict(zip(colunas, row)) for row in cur.fetchall()]
        finally: conn.close()

    @staticmethod
    def salvar_renda(usuario, fonte, mes, ano, valor):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            query = """
                INSERT INTO rendas (usuario, fonte, mes, ano, valor) 
                VALUES (%s, %s, %s, %s, %s) 
                ON CONFLICT (usuario, fonte, mes, ano) 
                DO UPDATE SET valor = EXCLUDED.valor
            """
            cur.execute(query, (usuario, fonte, mes, ano, valor))
            conn.commit()
            cur.close()
            return True
        except Exception as e: 
            print(f"Erro ao salvar renda: {e}")
            return False
        finally: conn.close()

    @staticmethod
    def obter_resumo(mes, ano):
        conn = get_db_connection()
        if not conn: return {}
        try:
            cur = conn.cursor()
            
            # Puxa rendas agrupando por usuário E fonte (Shopee, Uber, Salário, etc)
            cur.execute("SELECT usuario, fonte, valor FROM rendas WHERE mes = %s AND ano = %s", (mes, ano))
            rendas_detalhadas = {'Igor': {}, 'Thaynara': {}}
            for row in cur.fetchall():
                usr, fnt, val = row[0], row[1], float(row[2])
                if usr in rendas_detalhadas:
                    rendas_detalhadas[usr][fnt] = val
            
            renda_igor = sum(rendas_detalhadas['Igor'].values())
            renda_thaynara = sum(rendas_detalhadas['Thaynara'].values())
            
            cur.execute("SELECT responsavel_pagamento, SUM(valor) FROM despesas WHERE EXTRACT(MONTH FROM data_vencimento) = %s AND EXTRACT(YEAR FROM data_vencimento) = %s AND pago = FALSE GROUP BY responsavel_pagamento", (mes, ano))
            pendentes = {row[0]: float(row[1]) for row in cur.fetchall()}
            pendente_igor = pendentes.get('Igor', 0.0)
            pendente_thaynara = pendentes.get('Thaynara', 0.0)
            
            # Subtração das Caixinhas do Saldo Livre
            cur.execute("SELECT SUM(valor) FROM caixinhas")
            res_caixinha = cur.fetchone()
            total_caixinhas = float(res_caixinha[0]) if res_caixinha and res_caixinha[0] else 0.0
            
            total_renda = renda_igor + renda_thaynara
            total_pendente = pendente_igor + pendente_thaynara
            saldo_final = total_renda - total_pendente - total_caixinhas
            
            cur.close()
            return { 
                "renda_igor": renda_igor, 
                "renda_thaynara": renda_thaynara, 
                "detalhes_igor": rendas_detalhadas['Igor'],
                "detalhes_thaynara": rendas_detalhadas['Thaynara'],
                "pendente_igor": pendente_igor, 
                "pendente_thaynara": pendente_thaynara, 
                "total_renda": total_renda, 
                "total_pendente": total_pendente, 
                "saldo_final": saldo_final,
                "total_caixinhas": total_caixinhas
            }
        finally: conn.close()

    @staticmethod
    def obter_comprovante(despesa_id):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT comprovante_dados, comprovante_mimetype FROM despesas WHERE id = %s", (despesa_id,))
            resultado = cur.fetchone()
            cur.close()
            if resultado and resultado[0]: return resultado[0], resultado[1]
            return None, None
        finally: conn.close()

    @staticmethod
    def marcar_paga(despesa_id, comprovante_binario=None, mimetype=None):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            if comprovante_binario:
                cur.execute("UPDATE despesas SET pago = TRUE, comprovante_dados = %s, comprovante_mimetype = %s WHERE id = %s", (comprovante_binario, mimetype, despesa_id))
            else:
                cur.execute("UPDATE despesas SET pago = TRUE WHERE id = %s", (despesa_id,))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

    @staticmethod
    def atualizar(despesa_id, dados):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            query = "UPDATE despesas SET descricao = %s, valor = %s, data_vencimento = %s, responsavel_pagamento = %s, fonte_pagamento = %s WHERE id = %s"
            cur.execute(query, (dados.get('descricao'), dados.get('valor'), dados.get('data_vencimento'), dados.get('responsavel_pagamento'), dados.get('fonte_pagamento'), despesa_id))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

    @staticmethod
    def excluir(despesa_id):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM despesas WHERE id = %s", (despesa_id,))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

    # --- CRUD CAIXINHAS ---
    @staticmethod
    def listar_caixinhas():
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, nome, valor FROM caixinhas ORDER BY criado_em ASC")
            colunas = [desc[0] for desc in cur.description]
            return [dict(zip(colunas, row)) for row in cur.fetchall()]
        finally: conn.close()

    @staticmethod
    def salvar_caixinha(nome, valor):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            query = "INSERT INTO caixinhas (nome, valor) VALUES (%s, %s) ON CONFLICT (nome) DO UPDATE SET valor = EXCLUDED.valor"
            cur.execute(query, (nome, valor))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

