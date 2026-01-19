# services/db_saver.py
import psycopg2
from configs.db import get_connection
from datetime import datetime
from zoneinfo import ZoneInfo

def salvar_lote_postgres(dados_lote):
    """
    Salva lote + itens no PostgreSQL.

    Regra: antes de inserir item, busca por (fornecedor + codigo_produto) usando JOIN:
      - se existir, atualiza o item (não recadastra)
      - se não existir, insere novo

    OBS: Não depende de coluna "fornecedor" em itens_processados (usa lote_id -> processamentos_lotes.id).
    """
    conn = None
    try:
        print("💾 Conectando ao banco para salvar dados...")
        conn = get_connection()
        cursor = conn.cursor()

        fornecedor = dados_lote.get("fornecedor") or dados_lote.get("fornecedror")

        # 1) Inserir o LOTE e pegar o ID gerado
        sql_lote = """
            INSERT INTO processamentos_lotes (fornecedor, data_processamento, total_itens)
            VALUES (%s, %s, %s)
            RETURNING id;
        """
        cursor.execute(sql_lote, (
            fornecedor,
            dados_lote["data_obj"],
            dados_lote["total_itens"]
        ))
        lote_id = cursor.fetchone()[0]

        # 2) Buscar item existente pelo (fornecedor + codigo_produto) via JOIN no lote
        sql_busca_item = """
            SELECT ip.id
            FROM itens_processados ip
            JOIN processamentos_lotes pl ON pl.id = ip.lote_id
            WHERE pl.fornecedor = %s
              AND ip.codigo_produto = %s
            LIMIT 1;
        """

        # 3) INSERT do item (quando não existe) - SEM coluna fornecedor em itens_processados
        sql_item_insert = """
            INSERT INTO itens_processados
            (lote_id, codigo_produto, nome_produto, marca, imagem_url,
             preco_unitario, qtd_solicitada, qtd_disponivel, valor_total,
             pode_comprar, status_texto, mensagem_erro)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """

        # 4) UPDATE do item (quando já existe)
        sql_item_update = """
            UPDATE itens_processados
            SET
                lote_id        = %s,
                nome_produto   = %s,
                marca          = %s,
                imagem_url     = %s,
                preco_unitario = %s,
                qtd_solicitada = %s,
                qtd_disponivel = %s,
                valor_total    = %s,
                pode_comprar   = %s,
                status_texto   = %s,
                mensagem_erro  = %s
            WHERE id = %s
            RETURNING id;
        """

        # 5) Regiões: remove e recria (evita duplicar)
        sql_delete_regioes = """
            DELETE FROM itens_detalhes_regionais
            WHERE item_id = %s;
        """

        sql_regiao_insert = """
            INSERT INTO itens_detalhes_regionais
            (item_id, uf, preco_regional, qtd_disponivel_regional, pode_comprar_regional)
            VALUES (%s, %s, %s, %s, %s);
        """

        # 6) Loop para salvar/atualizar itens
        for item in dados_lote["itens"]:
            codigo = item["codigo"]

            cursor.execute(sql_busca_item, (fornecedor, codigo))
            row = cursor.fetchone()

            if row:
                item_existente_id = row[0]
                cursor.execute(sql_item_update, (
                    lote_id,
                    item["nome"],
                    item["marca"],
                    item["imagem"],
                    item["preco_num"],
                    item["qtdSolicitada"],
                    item["qtdDisponivel"],
                    item["valor_total"],
                    item["podeComprar"],
                    item["status"],
                    item.get("mensagem"),
                    item_existente_id
                ))
                item_id = cursor.fetchone()[0]
            else:
                cursor.execute(sql_item_insert, (
                    lote_id,
                    codigo,
                    item["nome"],
                    item["marca"],
                    item["imagem"],
                    item["preco_num"],
                    item["qtdSolicitada"],
                    item["qtdDisponivel"],
                    item["valor_total"],
                    item["podeComprar"],
                    item["status"],
                    item.get("mensagem")
                ))
                item_id = cursor.fetchone()[0]

            # Regiões (sempre sincroniza com o payload atual)
            cursor.execute(sql_delete_regioes, (item_id,))

            regioes = item.get("regioes") or []
            for regiao in regioes:
                cursor.execute(sql_regiao_insert, (
                    item_id,
                    regiao["uf"],
                    regiao["preco_num"],
                    regiao["qtdDisponivel"],
                    regiao["podeComprar"]
                ))

        conn.commit()
        print(f"✅ Sucesso! Lote ID {lote_id} salvo com {len(dados_lote['itens'])} itens (insert/update).")
        return True

    except Exception as e:
        print(f"❌ Erro ao salvar no PostgreSQL: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def atualizar_ultimo_processamento(data_obj=None):
  
  

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Se não passou data, usa NOW() direto no SQL
        if data_obj is None:
            sql = """
                INSERT INTO controle_ultimo_processamento (id, ultima_data_processamento, atualizado_em)
                VALUES (1, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                SET ultima_data_processamento = EXCLUDED.ultima_data_processamento,
                    atualizado_em = NOW();
            """
            cursor.execute(sql)
            conn.commit()
            return True

        # Se passou datetime, garante timezone
        if isinstance(data_obj, datetime):
            if data_obj.tzinfo is None:
                data_obj = data_obj.replace(tzinfo=ZoneInfo("America/Fortaleza"))
        else:
            # Se veio algo diferente de datetime, cai para NOW()
            sql = """
                INSERT INTO controle_ultimo_processamento (id, ultima_data_processamento, atualizado_em)
                VALUES (1, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                SET ultima_data_processamento = EXCLUDED.ultima_data_processamento,
                    atualizado_em = NOW();
            """
            cursor.execute(sql)
            conn.commit()
            return True

        sql = """
            INSERT INTO controle_ultimo_processamento (id, ultima_data_processamento, atualizado_em)
            VALUES (1, %s, NOW())
            ON CONFLICT (id) DO UPDATE
            SET ultima_data_processamento = EXCLUDED.ultima_data_processamento,
                atualizado_em = NOW();
        """
        cursor.execute(sql, (data_obj,))
        conn.commit()
        return True

    except Exception as e:
        print(f"❌ Erro ao atualizar controle_ultimo_processamento: {e}")
        if conn:
            conn.rollback()
        return False

    finally:
        if conn:
            conn.close()



def limpar_banco_processamento():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            TRUNCATE TABLE
                itens_detalhes_regionais,
                itens_processados,
                processamentos_lotes
            RESTART IDENTITY CASCADE;
        """)

        cursor.execute("""
            INSERT INTO controle_ultimo_processamento (id, ultima_data_processamento, atualizado_em)
            VALUES (1, TIMESTAMPTZ '1970-01-01 00:00:00-03', NOW())
            ON CONFLICT (id) DO UPDATE
            SET ultima_data_processamento = EXCLUDED.ultima_data_processamento,
                atualizado_em = NOW();
        """)

        conn.commit()
        return {"success": True}

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Erro ao limpar banco de processamento: {e}")
        return {"success": False, "error": str(e)}

    finally:
        if conn:
            conn.close()
