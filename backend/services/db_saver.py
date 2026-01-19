# services/db_saver.py
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from configs.db import get_connection

# SQLite = 1 writer por vez. Esse lock evita concorrência de escrita entre fornecedores/controllers.
_sqlite_write_lock = threading.Lock()


def salvar_lote_sqlite(dados_lote):
    """
    Salva lote + itens no SQLite (websrc.db).

    Regra: antes de inserir item, busca por (fornecedor + codigo_produto) usando JOIN:
      - se existir, atualiza o item (não recadastra)
      - se não existir, insere novo

    OBS: Não depende de coluna "fornecedor" em itens_processados (usa lote_id -> processamentos_lotes.id).
    """
    conn = None
    try:
        print("💾 Conectando ao SQLite para salvar dados...")
        conn = get_connection()
        cursor = conn.cursor()

        fornecedor = dados_lote.get("fornecedor") or dados_lote.get("fornecedror")

        # 1) Inserir o LOTE e pegar o ID gerado
        sql_lote = """
            INSERT INTO processamentos_lotes (fornecedor, data_processamento, total_itens)
            VALUES (?, ?, ?);
        """

        # 2) Buscar item existente pelo (fornecedor + codigo_produto) via JOIN no lote
        sql_busca_item = """
            SELECT ip.id
            FROM itens_processados ip
            JOIN processamentos_lotes pl ON pl.id = ip.lote_id
            WHERE pl.fornecedor = ?
              AND ip.codigo_produto = ?
            LIMIT 1;
        """

        # 3) INSERT do item (quando não existe)
        sql_item_insert = """
            INSERT INTO itens_processados
            (lote_id, codigo_produto, nome_produto, marca, imagem_url,
             preco_unitario, qtd_solicitada, qtd_disponivel, valor_total,
             pode_comprar, status_texto, mensagem_erro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        # 4) UPDATE do item (quando já existe)
        sql_item_update = """
            UPDATE itens_processados
            SET
                lote_id        = ?,
                nome_produto   = ?,
                marca          = ?,
                imagem_url     = ?,
                preco_unitario = ?,
                qtd_solicitada = ?,
                qtd_disponivel = ?,
                valor_total    = ?,
                pode_comprar   = ?,
                status_texto   = ?,
                mensagem_erro  = ?
            WHERE id = ?;
        """

        # 5) Regiões: remove e recria (evita duplicar)
        sql_delete_regioes = """
            DELETE FROM itens_detalhes_regionais
            WHERE item_id = ?;
        """

        sql_regiao_insert = """
            INSERT INTO itens_detalhes_regionais
            (item_id, uf, preco_regional, qtd_disponivel_regional, pode_comprar_regional)
            VALUES (?, ?, ?, ?, ?);
        """

        itens = dados_lote.get("itens") or []
        if not itens:
            print("⚠️ Nenhum item para salvar.")
            return True

        # ✅ Escrita no SQLite deve ser serializada
        with _sqlite_write_lock:
            # ✅ Transação gerenciada automaticamente (evita BEGIN dentro de BEGIN)
            with conn:
                # 1) Lote
                cursor.execute(sql_lote, (
                    fornecedor,
                    dados_lote["data_obj"],
                    dados_lote["total_itens"]
                ))
                lote_id = cursor.lastrowid

                # 2) Itens
                for item in itens:
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
                        item_id = item_existente_id
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
                        item_id = cursor.lastrowid

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

        print(f"✅ Sucesso! Lote ID {lote_id} salvo com {len(itens)} itens (insert/update).")
        return True

    except Exception as e:
        print(f"❌ Erro ao salvar no SQLite: {e}")
        # Com "with conn:" o rollback é automático se exception ocorrer dentro do bloco,
        # mas aqui mantemos por segurança quando erro acontece fora do bloco.
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False

    finally:
        if conn:
            conn.close()


def atualizar_ultimo_processamento(data_obj=None):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Se não passou data, usa CURRENT_TIMESTAMP
        if data_obj is None:
            sql = """
                INSERT INTO controle_ultimo_processamento (id, ultima_data_processamento, atualizado_em)
                VALUES (1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    ultima_data_processamento = excluded.ultima_data_processamento,
                    atualizado_em = CURRENT_TIMESTAMP;
            """
            with _sqlite_write_lock:
                with conn:
                    cursor.execute(sql)
            return True

        # Se passou datetime, converte para ISO
        if isinstance(data_obj, datetime):
            if data_obj.tzinfo is None:
                data_obj = data_obj.replace(tzinfo=ZoneInfo("America/Fortaleza"))
            data_str = data_obj.isoformat()
        else:
            data_str = None

        if not data_str:
            sql = """
                INSERT INTO controle_ultimo_processamento (id, ultima_data_processamento, atualizado_em)
                VALUES (1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    ultima_data_processamento = excluded.ultima_data_processamento,
                    atualizado_em = CURRENT_TIMESTAMP;
            """
            with _sqlite_write_lock:
                with conn:
                    cursor.execute(sql)
            return True

        sql = """
            INSERT INTO controle_ultimo_processamento (id, ultima_data_processamento, atualizado_em)
            VALUES (1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                ultima_data_processamento = excluded.ultima_data_processamento,
                atualizado_em = CURRENT_TIMESTAMP;
        """

        with _sqlite_write_lock:
            with conn:
                cursor.execute(sql, (data_str,))
        return True

    except Exception as e:
        print(f"❌ Erro ao atualizar controle_ultimo_processamento (SQLite): {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False

    finally:
        if conn:
            conn.close()


def limpar_banco_processamento():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        with _sqlite_write_lock:
            with conn:
                cursor.execute("DELETE FROM itens_detalhes_regionais;")
                cursor.execute("DELETE FROM itens_processados;")
                cursor.execute("DELETE FROM processamentos_lotes;")

                # Reset de autoincrement (somente se existir sqlite_sequence)
                try:
                    cursor.execute("""
                        DELETE FROM sqlite_sequence
                        WHERE name IN ('itens_detalhes_regionais','itens_processados','processamentos_lotes');
                    """)
                except Exception:
                    # Se não existir sqlite_sequence (sem AUTOINCREMENT), ignora
                    pass

                cursor.execute("""
                    INSERT INTO controle_ultimo_processamento (id, ultima_data_processamento, atualizado_em)
                    VALUES (1, '1970-01-01T00:00:00-03:00', CURRENT_TIMESTAMP)
                    ON CONFLICT(id) DO UPDATE SET
                        ultima_data_processamento = excluded.ultima_data_processamento,
                        atualizado_em = CURRENT_TIMESTAMP;
                """)

        return {"success": True}

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"❌ Erro ao limpar banco (SQLite): {e}")
        return {"success": False, "error": str(e)}

    finally:
        if conn:
            conn.close()
