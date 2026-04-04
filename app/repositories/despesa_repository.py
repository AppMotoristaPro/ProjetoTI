import datetime
import uuid
import json
from app.extensions import get_db_connection

class DespesaRepository:

    # Força o Python a usar sempre UTC-3 (São Paulo)
    @staticmethod
    def _hoje():
        return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).date()

    @staticmethod
    def _somar_meses(data_original, meses_a_somar):
        if not data_original: return None
        mes = data_original.month - 1 + meses_a_somar
        ano = data_original.year + mes // 12
        mes = mes % 12 + 1
        dia = min(data_original.day, [31, 29 if ano % 4 == 0 and (not ano % 100 == 0 or ano % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
        return datetime.date(ano, mes, dia)

    @staticmethod
    def _garantir_tabelas():
        conn = get_db_connection()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dias_marcados (
                    id SERIAL PRIMARY KEY,
                    data_marcada DATE,
                    usuario VARCHAR(50),
                    tipo VARCHAR(50)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rotas_mensal (
                    id SERIAL PRIMARY KEY,
                    mes INT NOT NULL,
                    ano INT NOT NULL,
                    dias JSONB DEFAULT '{}',
                    UNIQUE(mes, ano)
                );
                CREATE TABLE IF NOT EXISTS rotas_config (
                    id SERIAL PRIMARY KEY,
                    config JSONB DEFAULT '{}'
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS metas_mensais (
                    id SERIAL PRIMARY KEY,
                    mes INT NOT NULL,
                    ano INT NOT NULL,
                    metas JSONB DEFAULT '{}',
                    UNIQUE(mes, ano)
                );
            """)
            conn.commit()
        except Exception as e: print(e)
        finally: conn.close()

    @staticmethod
    def listar_dias_marcados(mes, ano):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            cur.execute("SELECT data_marcada, usuario, tipo FROM dias_marcados WHERE EXTRACT(MONTH FROM data_marcada) = %s AND EXTRACT(YEAR FROM data_marcada) = %s", (mes, ano))
            return [{"data": d[0].strftime('%Y-%m-%d'), "usuario": d[1], "tipo": d[2]} for d in cur.fetchall()]
        except Exception: return []
        finally: conn.close()

    @staticmethod
    def marcar_dia(data, usuario, tipo):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT id, tipo FROM dias_marcados WHERE data_marcada = %s AND usuario = %s", (data, usuario))
            marcacoes_existentes = cur.fetchall()
            
            grupo_novo = tipo.split('_')[0] if tipo and '_' in tipo else tipo
            
            for m_id, m_tipo in marcacoes_existentes:
                grupo_existente = m_tipo.split('_')[0] if m_tipo and '_' in m_tipo else m_tipo
                
                if not tipo or grupo_existente == grupo_novo:
                    if usuario == 'Thaynara' and m_tipo.startswith('morato_reembolsado'):
                        partes = m_tipo.split('|')
                        data_ref = partes[1] if len(partes) == 2 else data
                        try: DespesaRepository.salvar_renda('Thaynara', 'Ajuda de Custo', data_ref, -139.00)
                        except: pass
                            
                    if usuario == 'Igor' and m_tipo.startswith('shopee_trabalhado'):
                        partes = m_tipo.split('|')
                        data_ref = partes[1] if len(partes) == 2 else data
                        try: DespesaRepository.salvar_renda('Igor', 'Shopee', data_ref, -245.00)
                        except: pass
                    
                    cur.execute("DELETE FROM dias_marcados WHERE id = %s", (m_id,))
            
            if tipo:
                if usuario == 'Thaynara' and tipo.startswith('morato_reembolsado'):
                    partes_novo = tipo.split('|')
                    data_ref = partes_novo[1] if len(partes_novo) == 2 else data
                    try: DespesaRepository.salvar_renda('Thaynara', 'Ajuda de Custo', data_ref, 139.00)
                    except: pass
                        
                if usuario == 'Igor' and tipo.startswith('shopee_trabalhado'):
                    partes_novo = tipo.split('|')
                    data_ref = partes_novo[1] if len(partes_novo) == 2 else data
                    try: DespesaRepository.salvar_renda('Igor', 'Shopee', data_ref, 245.00)
                    except: pass
                        
                cur.execute("INSERT INTO dias_marcados (data_marcada, usuario, tipo) VALUES (%s, %s, %s)", (data, usuario, tipo))
            
            conn.commit()
            return True
        except Exception as e: 
            print(f"Erro no marcar_dia: {e}")
            return False
        finally: 
            conn.close()

    @staticmethod
    def salvar_inscricao_push(usuario, sub_info):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            endpoint = sub_info.get('endpoint')
            sub_str = json.dumps(sub_info)
            cur.execute("DELETE FROM inscricoes_push WHERE subscription_info->>'endpoint' = %s", (endpoint,))
            cur.execute("INSERT INTO inscricoes_push (usuario, subscription_info) VALUES (%s, %s)", (usuario, sub_str))
            conn.commit()
            return True
        except Exception as e: 
            print(e)
            return False
        finally: conn.close()

    @staticmethod
    def obter_inscricoes(usuario):
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, subscription_info FROM inscricoes_push WHERE usuario = %s", (usuario,))
            return [{'id': r[0], 'subscription_info': r[1]} for r in cur.fetchall()]
        except Exception: return []
        finally: conn.close()

    @staticmethod
    def remover_inscricao_push(id_inscricao):
        conn = get_db_connection()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM inscricoes_push WHERE id = %s", (id_inscricao,))
            conn.commit()
        except: pass
        finally: conn.close()

    @staticmethod
    def buscar_contas_proximos_7_dias():
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            cur.execute("SELECT descricao, valor, data_vencimento FROM despesas WHERE pago = FALSE AND data_vencimento BETWEEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')::date AND (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')::date + INTERVAL '7 days' AND tipo_despesa IN ('Fixa', 'Variável') ORDER BY data_vencimento ASC")
            colunas = [desc[0] for desc in cur.description]
            return [dict(zip(colunas, [str(r[i]) if i==2 else r[i] for i in range(len(r))])) for r in cur.fetchall()]
        except Exception: return []
        finally: conn.close()

    @staticmethod
    def buscar_contas_vencendo_amanha():
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            cur.execute("SELECT descricao, valor, responsavel_pagamento FROM despesas WHERE pago = FALSE AND data_vencimento = (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')::date + INTERVAL '1 day' AND tipo_despesa IN ('Fixa', 'Variável')")
            colunas = [desc[0] for desc in cur.description]
            return [dict(zip(colunas, row)) for row in cur.fetchall()]
        except Exception: return []
        finally: conn.close()

    @staticmethod
    def obter_por_id(despesa_id):
        conn = get_db_connection()
        if not conn: return None
        try:
            cur = conn.cursor()
            cur.execute("SELECT descricao, valor, responsavel_pagamento FROM despesas WHERE id = %s", (despesa_id,))
            linha = cur.fetchone()
            if linha: return {"descricao": linha[0], "valor": float(linha[1]), "responsavel_pagamento": linha[2]}
            return None
        except Exception: return None
        finally: conn.close()

    @staticmethod
    def criar(dados, comprovante_binario, mimetype):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            tipo_despesa = dados.get('tipo_despesa', 'Variável')
            grupo_id = str(uuid.uuid4())
            recorrente = str(dados.get('recorrente', 'false')).lower() == 'true'
            repetir_previsao = str(dados.get('repetir_previsao', 'false')).lower() == 'true'
            parcela_inicial = int(dados.get('parcela_atual', 1))
            total_parcelas = int(dados.get('total_parcelas', 1))
            
            if tipo_despesa == 'Fixa':
                recorrente = True; parcela_inicial = 1; total_parcelas = 60
            elif tipo_despesa == 'Diária':
                recorrente = False; total_parcelas = 1
            
            data_vencimento = datetime.datetime.strptime(dados.get('data_vencimento'), '%Y-%m-%d').date()
            data_pretensao = datetime.datetime.strptime(dados.get('data_pretensao'), '%Y-%m-%d').date() if dados.get('data_pretensao') else None
            parcelas_a_criar = total_parcelas - parcela_inicial + 1
            if not recorrente or parcelas_a_criar < 1: parcelas_a_criar = 1

            for i in range(parcelas_a_criar):
                nova_data_venc = DespesaRepository._somar_meses(data_vencimento, i)
                nova_data_pret = DespesaRepository._somar_meses(data_pretensao, i) if (i == 0 or repetir_previsao) else None
                p_atual = parcela_inicial + i
                comp_bin = comprovante_binario if i == 0 else None
                comp_mime = mimetype if i == 0 else None
                status_pago = str(dados.get('pago', 'false')).lower() == 'true' if i == 0 else False
                
                data_pagamento = DespesaRepository._hoje() if status_pago else None
                
                cur.execute("""INSERT INTO despesas (descricao, valor, data_vencimento, data_pretensao, responsavel_pagamento, categoria, pago, comprovante_dados, comprovante_mimetype, recorrente, parcela_atual, total_parcelas, observacao, icone_svg, fonte_pagamento, tipo_despesa, grupo_id, data_pagamento) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (dados.get('descricao'), dados.get('valor'), nova_data_venc, nova_data_pret, dados.get('responsavel_pagamento'), dados.get('categoria', 'Geral'), status_pago, comp_bin, comp_mime, recorrente, p_atual, total_parcelas, dados.get('observacao', ''), dados.get('icone_svg', 'geral'), dados.get('fonte_pagamento'), tipo_despesa, grupo_id, data_pagamento))
            conn.commit()
            return True
        except Exception as e: print(e); return False
        finally: conn.close()

    @staticmethod
    def listar_por_mes(mes, ano):
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, descricao, valor, data_vencimento, data_pretensao, data_pagamento, responsavel_pagamento, categoria, pago, recorrente, parcela_atual, total_parcelas, observacao, icone_svg, fonte_pagamento, tipo_despesa, grupo_id, (comprovante_dados IS NOT NULL) as tem_comprovante FROM despesas WHERE EXTRACT(MONTH FROM data_vencimento) = %s AND EXTRACT(YEAR FROM data_vencimento) = %s ORDER BY data_vencimento ASC", (mes, ano))
            colunas = [desc[0] for desc in cur.description]
            resultados = []
            for row in cur.fetchall():
                d = dict(zip(colunas, row))
                if d.get('data_vencimento'): d['data_vencimento'] = d['data_vencimento'].strftime('%Y-%m-%d')
                if d.get('data_pretensao'): d['data_pretensao'] = d['data_pretensao'].strftime('%Y-%m-%d')
                if d.get('data_pagamento'): d['data_pagamento'] = d['data_pagamento'].strftime('%Y-%m-%d')
                resultados.append(d)
            return resultados
        finally: conn.close()

    @staticmethod
    def listar_rendas_detalhadas(mes, ano):
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, usuario, fonte, valor, data_recebimento FROM rendas WHERE mes=%s AND ano=%s ORDER BY data_recebimento ASC NULLS LAST, id ASC", (mes, ano))
            colunas = [desc[0] for desc in cur.description]
            resultados = []
            for row in cur.fetchall():
                d = dict(zip(colunas, row))
                if d.get('data_recebimento'): d['data_recebimento'] = d['data_recebimento'].strftime('%Y-%m-%d')
                resultados.append(d)
            return resultados
        finally: conn.close()

    @staticmethod
    def salvar_renda(usuario, fonte, data_recebimento, valor, mes_forcado=None, ano_forcado=None):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            if data_recebimento:
                data_obj = datetime.datetime.strptime(data_recebimento, '%Y-%m-%d').date()
                mes = mes_forcado or data_obj.month
                ano = ano_forcado or data_obj.year
            else:
                hoje = DespesaRepository._hoje()
                mes = mes_forcado or hoje.month
                ano = ano_forcado or hoje.year
                data_recebimento = hoje.strftime('%Y-%m-%d')
            
            agrupar_mensal = fonte in ['Uber', 'Ajuda de Custo']
            
            if agrupar_mensal:
                cur.execute("SELECT id FROM rendas WHERE usuario=%s AND fonte=%s AND mes=%s AND ano=%s ORDER BY id ASC", (usuario, fonte, mes, ano))
            else:
                cur.execute("SELECT id FROM rendas WHERE usuario=%s AND fonte=%s AND data_recebimento=%s ORDER BY id ASC", (usuario, fonte, data_recebimento))
            
            linhas = cur.fetchall()
            
            if linhas: 
                primeiro_id = linhas[0][0]
                cur.execute("UPDATE rendas SET valor = valor + %s, data_recebimento = %s WHERE id=%s RETURNING valor", (valor, data_recebimento, primeiro_id))
                novo_val = cur.fetchone()[0]
                
                if len(linhas) > 1:
                    for l in linhas[1:]:
                        cur.execute("UPDATE rendas SET valor = valor + (SELECT valor FROM rendas WHERE id=%s) WHERE id=%s", (l[0], primeiro_id))
                        cur.execute("DELETE FROM rendas WHERE id=%s", (l[0],))
                        
                    cur.execute("SELECT valor FROM rendas WHERE id=%s", (primeiro_id,))
                    novo_val = cur.fetchone()[0]

                if float(novo_val) <= 0:
                    cur.execute("DELETE FROM rendas WHERE id=%s", (primeiro_id,))
            else: 
                if float(valor) > 0:
                    cur.execute("INSERT INTO rendas (usuario, fonte, mes, ano, valor, data_recebimento) VALUES (%s, %s, %s, %s, %s, %s)", (usuario, fonte, mes, ano, valor, data_recebimento))
            
            conn.commit()
            return True
        except Exception as e: 
            print(f"❌ Erro ao salvar renda: {e}")
            return False
        finally: 
            conn.close()

    @staticmethod
    def atualizar_renda(renda_id, valor, data_recebimento=None):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            if data_recebimento:
                data_obj = datetime.datetime.strptime(data_recebimento, '%Y-%m-%d').date()
                cur.execute("UPDATE rendas SET valor=%s, data_recebimento=%s, mes=%s, ano=%s WHERE id=%s", (valor, data_recebimento, data_obj.month, data_obj.year, renda_id))
            else:
                cur.execute("UPDATE rendas SET valor=%s WHERE id=%s", (valor, renda_id))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def excluir_renda(renda_id):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM rendas WHERE id=%s", (renda_id,))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def salvar_metas_categorias(mes, ano, metas_json):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM metas_mensais WHERE mes = %s AND ano = %s", (mes, ano))
            if cur.fetchone():
                cur.execute("UPDATE metas_mensais SET metas = %s WHERE mes = %s AND ano = %s", (json.dumps(metas_json), mes, ano))
            else:
                cur.execute("INSERT INTO metas_mensais (mes, ano, metas) VALUES (%s, %s, %s)", (mes, ano, json.dumps(metas_json)))
            conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao salvar metas: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def obter_resumo(mes, ano):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        if not conn: return {}
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT metas FROM metas_mensais WHERE mes = %s AND ano = %s", (mes, ano))
            row_metas = cur.fetchone()
            metas_categorias = row_metas[0] if row_metas else {}
            
            primeiro_dia_atual = datetime.date(ano, mes, 1)
            ultimo_dia_ant = primeiro_dia_atual - datetime.timedelta(days=1)
            
            cur.execute("""
                SELECT SUM(valor) FROM rendas 
                WHERE data_recebimento <= %s 
                OR (data_recebimento IS NULL AND (ano < %s OR (ano = %s AND mes <= %s)))
            """, (ultimo_dia_ant, ultimo_dia_ant.year, ultimo_dia_ant.year, ultimo_dia_ant.month))
            res_rendas_ant = cur.fetchone()
            tot_rendas_ant = float(res_rendas_ant[0]) if res_rendas_ant and res_rendas_ant[0] else 0.0

            cur.execute("""
                SELECT SUM(valor) FROM despesas 
                WHERE COALESCE(data_pretensao, data_vencimento) <= %s
            """, (ultimo_dia_ant,))
            res_desp_ant = cur.fetchone()
            tot_desp_ant = float(res_desp_ant[0]) if res_desp_ant and res_desp_ant[0] else 0.0

            saldo_mes_anterior = tot_rendas_ant - tot_desp_ant

            cur.execute("SELECT usuario, fonte, valor FROM rendas WHERE mes = %s AND ano = %s", (mes, ano))
            rendas_detalhadas = {'Igor': {}, 'Thaynara': {}}
            for row in cur.fetchall():
                if row[0] in rendas_detalhadas: 
                    rendas_detalhadas[row[0]][row[1]] = rendas_detalhadas[row[0]].get(row[1], 0) + float(row[2])
            
            renda_igor = sum(rendas_detalhadas['Igor'].values())
            renda_thaynara = sum(rendas_detalhadas['Thaynara'].values())
            total_renda = renda_igor + renda_thaynara
            
            cur.execute("SELECT responsavel_pagamento, SUM(valor) FROM despesas WHERE EXTRACT(MONTH FROM data_vencimento) = %s AND EXTRACT(YEAR FROM data_vencimento) = %s AND pago = FALSE GROUP BY responsavel_pagamento", (mes, ano))
            pendentes = {row[0]: float(row[1]) for row in cur.fetchall()}
            total_pendente = pendentes.get('Igor', 0.0) + pendentes.get('Thaynara', 0.0)
            
            cur.execute("SELECT SUM(valor) FROM despesas WHERE EXTRACT(MONTH FROM data_vencimento) = %s AND EXTRACT(YEAR FROM data_vencimento) = %s", (mes, ano))
            res_desp = cur.fetchone()
            total_todas_despesas_mes = float(res_desp[0]) if res_desp and res_desp[0] else 0.0
            
            saldo_final = total_renda - total_todas_despesas_mes
            
            return { 
                "renda_igor": renda_igor, "renda_thaynara": renda_thaynara, 
                "detalhes_igor": rendas_detalhadas['Igor'], "detalhes_thaynara": rendas_detalhadas['Thaynara'],
                "total_renda": total_renda, "total_pendente": total_pendente,
                "total_despesas_mes": total_todas_despesas_mes,
                "total_caixinhas_mes": 0.0,
                "saldo_mes_anterior": saldo_mes_anterior, 
                "saldo_final": saldo_final,
                "metas_categorias": metas_categorias 
            }
        finally: conn.close()

    @staticmethod
    def obter_comprovante(despesa_id):
        conn = get_db_connection()
        if not conn: return (None, None)
        try:
            cur = conn.cursor()
            cur.execute("SELECT comprovante_dados, comprovante_mimetype FROM despesas WHERE id = %s", (despesa_id,))
            resultado = cur.fetchone()
            return (resultado[0], resultado[1]) if resultado and resultado[0] else (None, None)
        finally: conn.close()

    @staticmethod
    def marcar_paga(despesa_id, comprovante_binario=None, mimetype=None):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            if comprovante_binario: cur.execute("UPDATE despesas SET pago = TRUE, data_pagamento = (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')::date, comprovante_dados = %s, comprovante_mimetype = %s WHERE id = %s", (comprovante_binario, mimetype, despesa_id))
            else: cur.execute("UPDATE despesas SET pago = TRUE, data_pagamento = (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')::date WHERE id = %s", (despesa_id,))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def desfazer_pagamento(despesa_id):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            cur.execute("UPDATE despesas SET pago = FALSE, data_pagamento = NULL, comprovante_dados = NULL, comprovante_mimetype = NULL WHERE id = %s", (despesa_id,))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    # LOGICA DE EDICAO EM LOTE IMPLEMENTADA AQUI
    @staticmethod
    def atualizar(despesa_id, dados):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT grupo_id, fonte_pagamento FROM despesas WHERE id = %s", (despesa_id,))
            row = cur.fetchone()
            grupo_id = row[0] if row else None
            fonte_atual = row[1] if row else None
            
            fonte_pagamento = dados.get('fonte_pagamento', fonte_atual)
            categoria = dados.get('categoria')

            if dados.get('data_pretensao') and dados.get('data_pretensao') != '': 
                cur.execute("UPDATE despesas SET descricao=%s, valor=%s, data_vencimento=%s, data_pretensao=%s, responsavel_pagamento=%s, fonte_pagamento=%s WHERE id=%s", 
                            (dados.get('descricao'), dados.get('valor'), dados.get('data_vencimento'), dados.get('data_pretensao'), dados.get('responsavel_pagamento'), fonte_pagamento, despesa_id))
            else: 
                cur.execute("UPDATE despesas SET descricao=%s, valor=%s, data_vencimento=%s, data_pretensao=NULL, responsavel_pagamento=%s, fonte_pagamento=%s WHERE id=%s", 
                            (dados.get('descricao'), dados.get('valor'), dados.get('data_vencimento'), dados.get('responsavel_pagamento'), fonte_pagamento, despesa_id))
            
            if categoria:
                if grupo_id:
                    cur.execute("UPDATE despesas SET categoria=%s WHERE grupo_id=%s", (categoria, grupo_id))
                else:
                    cur.execute("UPDATE despesas SET categoria=%s WHERE id=%s", (categoria, despesa_id))
                    
            conn.commit()
            return True
        except Exception as e: print(e); return False
        finally: conn.close()

    @staticmethod
    def excluir(despesa_id, excluir_todas=False):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            if excluir_todas:
                cur.execute("SELECT descricao, valor, grupo_id FROM despesas WHERE id = %s", (despesa_id,))
                ref = cur.fetchone()
                if ref: cur.execute("DELETE FROM despesas WHERE (descricao = %s AND valor = %s AND total_parcelas > 1 AND pago = FALSE) OR (grupo_id = %s AND pago = FALSE)", (ref[0], ref[1], ref[2]))
            else: cur.execute("DELETE FROM despesas WHERE id = %s", (despesa_id,))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def obter_pacotao_dashboard(mes, ano, mes_ant, ano_ant):
        return {
            "resumo": DespesaRepository.obter_resumo(mes, ano),
            "despesas": DespesaRepository.listar_por_mes(mes, ano),
            "marcacoes": DespesaRepository.listar_dias_marcados(mes_ant, ano_ant) + DespesaRepository.listar_dias_marcados(mes, ano),
            "rendas": DespesaRepository.listar_rendas_detalhadas(mes, ano)
        }

    @staticmethod
    def obter_pacotao_rotas(mes, ano):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        if not conn: return {}
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT config FROM rotas_config ORDER BY id DESC LIMIT 1")
            row_config = cur.fetchone()
            config = row_config[0] if row_config else {
                "preco_km": 1.39,
                "preco_comb": 5.50,
                "Itupeva": {"km_emp": 48.0, "km_real": 60.0},
                "Cabreuva": {"km_emp": 58.7, "km_real": 86.7},
                "Morato": {"km_emp": 100.0, "km_real": 97.0}
            }
            
            cur.execute("SELECT dias FROM rotas_mensal WHERE mes = %s AND ano = %s", (mes, ano))
            row_dias = cur.fetchone()
            dias = row_dias[0] if row_dias else {"Itupeva": 0, "Cabreuva": 0, "Morato": 0}
            
            return {"config": config, "dias": dias}
        except Exception as e:
            print(e)
            return {}
        finally:
            conn.close()

    @staticmethod
    def salvar_rotas_config(config_json):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO rotas_config (config) VALUES (%s)", (json.dumps(config_json),))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def salvar_rotas_dias(mes, ano, dias_json):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM rotas_mensal WHERE mes = %s AND ano = %s", (mes, ano))
            if cur.fetchone():
                cur.execute("UPDATE rotas_mensal SET dias = %s WHERE mes = %s AND ano = %s", (json.dumps(dias_json), mes, ano))
            else:
                cur.execute("INSERT INTO rotas_mensal (mes, ano, dias) VALUES (%s, %s, %s)", (mes, ano, json.dumps(dias_json)))
            conn.commit()
            return True
        except Exception as e:
            print(f"Erro salvar_rotas_dias: {e}")
            return False
        finally:
            conn.close()

