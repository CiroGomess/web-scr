# services/db_saver.py
import psycopg2
from configs.db import get_connection

def salvar_lote_postgres(dados_lote):
    """
    Função síncrona para salvar os dados no PostgreSQL usando psycopg2.
    """
    conn = None
    try:
        print("💾 Conectando ao banco para salvar dados...")
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Inserir na tabela de LOTES e pegar o ID gerado
        sql_lote = """
            INSERT INTO processamentos_lotes (fornecedor, data_processamento, total_itens)
            VALUES (%s, %s, %s)
            RETURNING id;
        """
        cursor.execute(sql_lote, (
            dados_lote["fornecedror"], 
            dados_lote["data_obj"],  # Passaremos o objeto datetime real
            dados_lote["total_itens"]
        ))
        lote_id = cursor.fetchone()[0] # Pega o ID retornado pelo PostgreSQL

        # SQL para os ITENS
        sql_item = """
            INSERT INTO itens_processados 
            (lote_id, codigo_produto, nome_produto, marca, imagem_url, 
             preco_unitario, qtd_solicitada, qtd_disponivel, valor_total, 
             pode_comprar, status_texto, mensagem_erro)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """

        # SQL para as REGIÕES
        sql_regiao = """
            INSERT INTO itens_detalhes_regionais
            (item_id, uf, preco_regional, qtd_disponivel_regional, pode_comprar_regional)
            VALUES (%s, %s, %s, %s, %s);
        """

        # 2. Loop para salvar os itens
        for item in dados_lote["itens"]:
            cursor.execute(sql_item, (
                lote_id,
                item["codigo"],
                item["nome"],
                item["marca"],
                item["imagem"],
                item["preco_num"],
                item["qtdSolicitada"],
                item["qtdDisponivel"],
                item["valor_total"],
                item["podeComprar"],
                item["status"],
                item.get("mensagem") # Usa .get caso não exista a chave
            ))
            item_id = cursor.fetchone()[0] # Pega o ID do item criado

            # 3. Loop para salvar as regiões (se houver)
            for regiao in item.get("regioes", []):
                cursor.execute(sql_regiao, (
                    item_id,
                    regiao["uf"],
                    regiao["preco_num"],
                    regiao["qtdDisponivel"],
                    regiao["podeComprar"]
                ))

        # Efetiva a transação no banco
        conn.commit()
        print(f"✅ Sucesso! Lote ID {lote_id} salvo com {len(dados_lote['itens'])} itens.")
        return True

    except Exception as e:
        print(f"❌ Erro ao salvar no PostgreSQL: {e}")
        if conn:
            conn.rollback() # Desfaz tudo se der erro
        return False
    finally:
        if conn:
            conn.close()