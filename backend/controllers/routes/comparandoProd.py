# controllers/routes/comparandoProd.py
import psycopg2
from configs.db import get_connection

def comparar_precos_entre_fornecedores():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # QUERY INTELIGENTE:
        # 1. Junta os Itens com os Lotes (para saber o nome do fornecedor).
        # 2. Ordena por data para pegar sempre o preço mais recente caso tenha duplicatas.
        # 3. Filtra apenas preços maiores que 0.
        query = """
            SELECT 
                ip.codigo_produto,
                ip.nome_produto,
                ip.imagem_url,
                pl.fornecedor,
                ip.preco_unitario,
                ip.qtd_disponivel,
                pl.data_processamento
            FROM itens_processados ip
            JOIN processamentos_lotes pl ON ip.lote_id = pl.id
            WHERE ip.preco_unitario > 0
            ORDER BY ip.codigo_produto, pl.data_processamento DESC;
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        # Dicionário para organizar a comparação
        # Estrutura: { "CODIGO_123": { "dados_produto": ..., "ofertas": [...] } }
        produtos_map = {}

        for row in resultados:
            codigo = row[0]
            nome = row[1]
            imagem = row[2]
            fornecedor = row[3]
            preco = float(row[4])
            estoque = row[5]
            data = row[6]

            # Se o produto ainda não está no mapa, inicializa
            if codigo not in produtos_map:
                produtos_map[codigo] = {
                    "codigo": codigo,
                    "nome": nome,
                    "imagem": imagem,
                    "melhor_preco": float('inf'), # Infinito para começar
                    "fornecedor_vencedor": None,
                    "ofertas": []
                }

            # Verifica se essa oferta já foi processada para esse fornecedor 
            # (evita duplicidade se tivermos vários lotes do mesmo fornecedor, pegamos o primeiro pq ordenamos por data DESC)
            fornecedores_existentes = [o['fornecedor'] for o in produtos_map[codigo]['ofertas']]
            if fornecedor in fornecedores_existentes:
                continue

            # Adiciona a oferta na lista
            oferta = {
                "fornecedor": fornecedor,
                "preco": preco,
                "preco_formatado": f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "estoque": estoque,
                "data_atualizacao": data.strftime("%d/%m/%Y %H:%M")
            }
            produtos_map[codigo]['ofertas'].append(oferta)

            # Verifica se é o novo preço vencedor (menor preço)
            if preco < produtos_map[codigo]['melhor_preco']:
                produtos_map[codigo]['melhor_preco'] = preco
                produtos_map[codigo]['fornecedor_vencedor'] = fornecedor

        # Formatação final da lista
        lista_comparada = []
        for cod, dados in produtos_map.items():
            # Formata o melhor preço para string BR
            melhor_val = dados['melhor_preco']
            dados['melhor_preco_formatado'] = f"R$ {melhor_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            # Ordena as ofertas do menor para o maior preço dentro do produto
            dados['ofertas'].sort(key=lambda x: x['preco'])
            
            lista_comparada.append(dados)

        return {
            "success": True,
            "total_produtos_analisados": len(lista_comparada),
            "comparativo": lista_comparada
        }

    except Exception as e:
        print(f"❌ Erro ao comparar preços no banco: {e}")
        return {"success": False, "error": str(e)}
    
    finally:
        if conn:
            conn.close()