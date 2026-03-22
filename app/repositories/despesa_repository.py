import datetime
import uuid
import json
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
    def _garantir_tabelas():
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dias_marcados (
                    id SERIAL PRIMARY KEY,
                    data_marcada DATE,
                    usuario VARCHAR(50),
                    tipo VARCHAR(50)
                );
                CREATE TABLE IF NOT EXISTS sandero_config (
                    id SERIAL PRIMARY KEY,
                    consumo FLOAT DEFAULT 0,
                    preco_combustivel FLOAT DEFAULT 0,
                    financiamento FLOAT DEFAULT 0,
                    seguro FLOAT DEFAULT 0,
                    ipva FLOAT DEFAULT 0,
                    pneus_valor FLOAT DEFAULT 0,
                    pneus_km INT DEFAULT 40000,
                    revisao_valor FLOAT DEFAULT 0,
                    reserva FLOAT DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS sandero_diario (
                    id SERIAL PRIMARY KEY,
                    data_registro DATE,
                    km_rodado FLOAT,
                    ganho FLOAT,
                    custo_calculado FLOAT,
                    lucro_real FLOAT
                );
            """)
            conn.commit()
        except Exception: pass
        finally: conn.close()

    @staticmethod
    def listar_dias_marcados(mes, ano):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
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
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT tipo FROM dias_marcados WHERE data_marcada = %s AND usuario = %s", (data, usuario))
            linha = cur.fetchone()
            tipo_anterior = linha[0] if linha else None
            
            try:
                data_obj = datetime.datetime.strptime(data, '%Y-%m-%d').date()
                mes_cal = data_obj.month
                ano_cal = data_obj.year
            except:
                mes_cal = datetime.date.today().month
                ano_cal = datetime.date.today().year

            if usuario == 'Thaynara':
                if tipo == 'morato_reembolsado' and tipo_anterior != 'morato_reembolsado':
                    DespesaRepository.salvar_renda('Thaynara', 'Ajuda de Custo', mes_cal, ano_cal, 139.00)
                elif tipo_anterior == 'morato_reembolsado' and tipo != 'morato_reembolsado':
                    DespesaRepository.salvar_renda('Thaynara', 'Ajuda de Custo', mes_cal, ano_cal, -139.00)
            
            if usuario == 'Igor':
                if tipo_anterior and tipo_anterior.startswith('shopee_trabalhado|'):
                    if not tipo or tipo == 'carro_parado' or not tipo.startswith('shopee_trabalhado|'):
                        partes_ant = tipo_anterior.split('|')
                        if len(partes_ant) == 2:
                            try:
                                dp_obj_ant = datetime.datetime.strptime(partes_ant[1], '%Y-%m-%d').date()
                                DespesaRepository.salvar_renda('Igor', 'Shopee', dp_obj_ant.month, dp_obj_ant.year, -245.00)
                            except: pass
                
                if tipo and tipo.startswith('shopee_trabalhado|'):
                    partes_novo = tipo.split('|')
                    if len(partes_novo) == 2:
                        try:
                            dp_obj_novo = datetime.datetime.strptime(partes_novo[1], '%Y-%m-%d').date()
                            DespesaRepository.salvar_renda('Igor', 'Shopee', dp_obj_novo.month, dp_obj_novo.year, 245.00)
                        except: pass
            
            cur.execute("DELETE FROM dias_marcados WHERE data_marcada = %s AND usuario = %s", (data, usuario))
            if tipo:
                cur.execute("INSERT INTO dias_marcados (data_marcada, usuario, tipo) VALUES (%s, %s, %s)", (data, usuario, tipo))
            
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def salvar_inscricao_push(usuario, sub_info):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            endpoint = sub_info.get('endpoint')
            sub_str = json.dumps(sub_info)
            cur.execute("SELECT id FROM inscricoes_push WHERE usuario = %s AND subscription_info->>'endpoint' = %s", (usuario, endpoint))
            linha = cur.fetchone()
            if linha: cur.execute("UPDATE inscricoes_push SET subscription_info = %s WHERE id = %s", (sub_str, linha[0]))
            else: cur.execute("INSERT INTO inscricoes_push (usuario, subscription_info) VALUES (%s, %s)", (usuario, sub_str))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def obter_inscricoes(usuario):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, subscription_info FROM inscricoes_push WHERE usuario = %s", (usuario,))
            return [{'id': r[0], 'subscription_info': r[1]} for r in cur.fetchall()]
        except Exception: return []
        finally: conn.close()

    @staticmethod
    def remover_inscricao_push(id_inscricao):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM inscricoes_push WHERE id = %s", (id_inscricao,))
            conn.commit()
        except: pass
        finally: conn.close()

    @staticmethod
    def buscar_contas_proximos_7_dias():
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT descricao, valor, data_vencimento FROM despesas WHERE pago = FALSE AND data_vencimento BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days' AND tipo_despesa IN ('Fixa', 'Variável') ORDER BY data_vencimento ASC")
            colunas = [desc[0] for desc in cur.description]
            return [dict(zip(colunas, [str(r[i]) if i==2 else r[i] for i in range(len(r))])) for r in cur.fetchall()]
        except Exception: return []
        finally: conn.close()

    @staticmethod
    def buscar_contas_vencendo_amanha():
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT descricao, valor, responsavel_pagamento FROM despesas WHERE pago = FALSE AND data_vencimento = CURRENT_DATE + INTERVAL '1 day' AND tipo_despesa IN ('Fixa', 'Variável')")
            colunas = [desc[0] for desc in cur.description]
            return [dict(zip(colunas, row)) for row in cur.fetchall()]
        except Exception: return []
        finally: conn.close()

    # --- NOVO: Lê os dados da conta antes de editar, pagar ou excluir ---
    @staticmethod
    def obter_por_id(despesa_id):
        conn = get_db_connection()
        if not conn: return None
        try:
            cur = conn.cursor()
            cur.execute("SELECT descricao, valor, responsavel_pagamento FROM despesas WHERE id = %s", (despesa_id,))
            linha = cur.fetchone()
            if linha:
                return {"descricao": linha[0], "valor": float(linha[1]), "responsavel_pagamento": linha[2]}
            return None
        except Exception: return None
        finally: conn.close()
    # --------------------------------------------------------------------

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
                data_pagamento = datetime.date.today() if status_pago else None
                
                cur.execute("""INSERT INTO despesas (descricao, valor, data_vencimento, data_pretensao, responsavel_pagamento, categoria, pago, comprovante_dados, comprovante_mimetype, recorrente, parcela_atual, total_parcelas, observacao, icone_svg, fonte_pagamento, tipo_despesa, grupo_id, data_pagamento) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (dados.get('descricao'), dados.get('valor'), nova_data_venc, nova_data_pret, dados.get('responsavel_pagamento'), dados.get('categoria', 'Geral'), status_pago, comp_bin, comp_mime, recorrente, p_atual, total_parcelas, dados.get('observacao', ''), dados.get('icone_svg', 'geral'), dados.get('fonte_pagamento'), tipo_despesa, grupo_id, data_pagamento))
            conn.commit()
            return True
        except Exception: return False
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
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, usuario, fonte, valor FROM rendas WHERE mes=%s AND ano=%s ORDER BY id", (mes, ano))
            colunas = [desc[0] for desc in cur.description]
            return [dict(zip(colunas, row)) for row in cur.fetchall()]
        finally: conn.close()

    @staticmethod
    def salvar_renda(usuario, fonte, mes, ano, valor):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM rendas WHERE usuario=%s AND fonte=%s AND mes=%s AND ano=%s", (usuario, fonte, mes, ano))
            linha = cur.fetchone()
            if linha: cur.execute("UPDATE rendas SET valor = valor + %s WHERE id=%s", (valor, linha[0]))
            else: cur.execute("INSERT INTO rendas (usuario, fonte, mes, ano, valor) VALUES (%s, %s, %s, %s, %s)", (usuario, fonte, mes, ano, valor))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def atualizar_renda(renda_id, valor):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE rendas SET valor=%s WHERE id=%s", (valor, renda_id))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def excluir_renda(renda_id):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM rendas WHERE id=%s", (renda_id,))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def obter_resumo(mes, ano):
        conn = get_db_connection()
        if not conn: return {}
        try:
            cur = conn.cursor()
            cur.execute("SELECT usuario, fonte, valor FROM rendas WHERE mes = %s AND ano = %s", (mes, ano))
            rendas_detalhadas = {'Igor': {}, 'Thaynara': {}}
            for row in cur.fetchall():
                if row[0] in rendas_detalhadas: rendas_detalhadas[row[0]][row[1]] = float(row[2])
            
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
                "saldo_final": saldo_final
            }
        finally: conn.close()

    @staticmethod
    def obter_comprovante(despesa_id):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT comprovante_dados, comprovante_mimetype FROM despesas WHERE id = %s", (despesa_id,))
            resultado = cur.fetchone()
            return (resultado[0], resultado[1]) if resultado and resultado[0] else (None, None)
        finally: conn.close()

    @staticmethod
    def marcar_paga(despesa_id, comprovante_binario=None, mimetype=None):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            if comprovante_binario: cur.execute("UPDATE despesas SET pago = TRUE, data_pagamento = CURRENT_DATE, comprovante_dados = %s, comprovante_mimetype = %s WHERE id = %s", (comprovante_binario, mimetype, despesa_id))
            else: cur.execute("UPDATE despesas SET pago = TRUE, data_pagamento = CURRENT_DATE WHERE id = %s", (despesa_id,))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def desfazer_pagamento(despesa_id):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE despesas SET pago = FALSE, data_pagamento = NULL, comprovante_dados = NULL, comprovante_mimetype = NULL WHERE id = %s", (despesa_id,))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def atualizar(despesa_id, dados):
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            if dados.get('data_pretensao') and dados.get('data_pretensao') != '': cur.execute("UPDATE despesas SET descricao=%s, valor=%s, data_vencimento=%s, data_pretensao=%s, responsavel_pagamento=%s, fonte_pagamento=%s WHERE id=%s", (dados.get('descricao'), dados.get('valor'), dados.get('data_vencimento'), dados.get('data_pretensao'), dados.get('responsavel_pagamento'), dados.get('fonte_pagamento'), despesa_id))
            else: cur.execute("UPDATE despesas SET descricao=%s, valor=%s, data_vencimento=%s, data_pretensao=NULL, responsavel_pagamento=%s, fonte_pagamento=%s WHERE id=%s", (dados.get('descricao'), dados.get('valor'), dados.get('data_vencimento'), dados.get('responsavel_pagamento'), dados.get('fonte_pagamento'), despesa_id))
            conn.commit()
            return True
        except Exception as e: print(e); return False
        finally: conn.close()

    @staticmethod
    def excluir(despesa_id, excluir_todas=False):
        conn = get_db_connection()
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
            "marcacoes": DespesaRepository.listar_dias_marcados(mes_ant, ano_ant) + DespesaRepository.listar_dias_marcados(mes, ano)
        }

    @staticmethod
    def obter_pacotao_carro(mes, ano):
        return {
            "config": DespesaRepository.obter_sandero_config(),
            "marcacoes": DespesaRepository.listar_dias_marcados(mes, ano),
            "despesas": DespesaRepository.listar_por_mes(mes, ano),
            "diario": DespesaRepository.listar_sandero_diario(mes, ano)
        }

    @staticmethod
    def obter_sandero_config():
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT consumo, preco_combustivel, financiamento, seguro, ipva, pneus_valor, pneus_km, revisao_valor, reserva FROM sandero_config ORDER BY id DESC LIMIT 1")
            linha = cur.fetchone()
            if not linha: return {"consumo": 10, "preco_combustivel": 5, "financiamento": 0, "seguro": 0, "ipva": 0, "pneus_valor": 0, "pneus_km": 40000, "revisao_valor": 0, "reserva": 0}
            colunas = [desc[0] for desc in cur.description]
            return dict(zip(colunas, linha))
        except Exception: return {}
        finally: conn.close()

    @staticmethod
    def salvar_sandero_config(dados):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM sandero_config LIMIT 1")
            linha = cur.fetchone()
            if linha:
                cur.execute("UPDATE sandero_config SET consumo=%s, preco_combustivel=%s, financiamento=%s, seguro=%s, ipva=%s, pneus_valor=%s, pneus_km=%s, revisao_valor=%s, reserva=%s WHERE id=%s", (dados.get('consumo', 10), dados.get('preco_combustivel', 5), dados.get('financiamento', 0), dados.get('seguro', 0), dados.get('ipva', 0), dados.get('pneus_valor', 0), dados.get('pneus_km', 40000), dados.get('revisao_valor', 0), dados.get('reserva', 0), linha[0]))
            else:
                cur.execute("INSERT INTO sandero_config (consumo, preco_combustivel, financiamento, seguro, ipva, pneus_valor, pneus_km, revisao_valor, reserva) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (dados.get('consumo', 10), dados.get('preco_combustivel', 5), dados.get('financiamento', 0), dados.get('seguro', 0), dados.get('ipva', 0), dados.get('pneus_valor', 0), dados.get('pneus_km', 40000), dados.get('revisao_valor', 0), dados.get('reserva', 0)))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def listar_sandero_diario(mes, ano):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, data_registro, km_rodado, ganho, custo_calculado, lucro_real FROM sandero_diario WHERE EXTRACT(MONTH FROM data_registro) = %s AND EXTRACT(YEAR FROM data_registro) = %s ORDER BY data_registro DESC", (mes, ano))
            colunas = [desc[0] for desc in cur.description]
            resultados = []
            for row in cur.fetchall():
                d = dict(zip(colunas, row))
                d['data_registro'] = d['data_registro'].strftime('%Y-%m-%d')
                resultados.append(d)
            return resultados
        except Exception: return []
        finally: conn.close()

    @staticmethod
    def salvar_sandero_diario(dados):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO sandero_diario (data_registro, km_rodado, ganho, custo_calculado, lucro_real) VALUES (%s, %s, %s, %s, %s)", (dados.get('data_registro'), dados.get('km_rodado'), dados.get('ganho'), dados.get('custo_calculado'), dados.get('lucro_real')))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def excluir_sandero_diario(diario_id):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM sandero_diario WHERE id = %s", (diario_id,))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

    @staticmethod
    def atualizar_sandero_diario(diario_id, dados):
        DespesaRepository._garantir_tabelas()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE sandero_diario
                SET data_registro = %s, km_rodado = %s, ganho = %s, custo_calculado = %s, lucro_real = %s
                WHERE id = %s
            """, (dados.get('data_registro'), dados.get('km_rodado'), dados.get('ganho'), dados.get('custo_calculado'), dados.get('lucro_real'), diario_id))
            conn.commit()
            return True
        except Exception: return False
        finally: conn.close()

