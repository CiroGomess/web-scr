# controllers/routes/comparandoProd.py
import psycopg2
import json
from zoneinfo import ZoneInfo
from configs.db import get_connection

def comparar_precos_entre_fornecedores():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ============================================================================
        # 🧠 QUERY INTELIGENTE COM AGREGAÇÃO JSON
        # ============================================================================
        query = """
            SELECT 
                ip.codigo_produto,
                ip.nome_produto,
                ip.imagem_url,
                pl.fornecedor,
                ip.preco_unitario,
                ip.qtd_disponivel,
                pl.data_processamento,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'uf', idr.uf,
                            'preco', idr.preco_regional,
                            'estoque', idr.qtd_disponivel_regional
                        ) ORDER BY idr.uf ASC
                    ) FILTER (WHERE idr.id IS NOT NULL),
                    '[]'::json
                ) as regioes
            FROM itens_processados ip
            JOIN processamentos_lotes pl ON ip.lote_id = pl.id
            LEFT JOIN itens_detalhes_regionais idr ON ip.id = idr.item_id
            WHERE ip.preco_unitario > 0
            GROUP BY ip.id, pl.id, ip.codigo_produto, ip.nome_produto, ip.imagem_url, pl.fornecedor, ip.preco_unitario, ip.qtd_disponivel, pl.data_processamento
            ORDER BY ip.codigo_produto, pl.data_processamento DESC;
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        produtos_map = {}

        for row in resultados:
            codigo = row[0]
            nome = row[1]
            imagem = row[2]
            fornecedor = row[3]
            preco = float(row[4])
            estoque = row[5]
            data = row[6]        # datetime vindo do banco
            regioes_raw = row[7] # json/lista de dicts

            data_formatada = data.strftime('%d/%m/%Y') if data else ""

            # Processa e formata os preços das regiões para o padrão BRL
            regioes_formatadas = []
            if regioes_raw:
                for reg in regioes_raw:
                    p_reg = float(reg['preco']) if reg['preco'] else 0.0
                    regioes_formatadas.append({
                        "uf": reg['uf'],
                        "preco": p_reg,
                        "preco_formatado": f"R$ {p_reg:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                        "estoque": reg['estoque']
                    })

            # Inicializa o produto no mapa se não existir
            if codigo not in produtos_map:
                produtos_map[codigo] = {
                    "codigo": codigo,
                    "nome": nome,
                    "imagem": imagem,
                    "melhor_preco": float('inf'),
                    "fornecedor_vencedor": None,
                    "ofertas": []
                }

            # Evita duplicidade de fornecedor (mantém o mais recente)
            fornecedores_existentes = [o['fornecedor'] for o in produtos_map[codigo]['ofertas']]
            if fornecedor in fornecedores_existentes:
                continue

            oferta = {
                "fornecedor": fornecedor,
                "preco": preco,
                "preco_formatado": f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "estoque": estoque,
                "data_atualizacao": data_formatada,
                "regioes": regioes_formatadas
            }
            
            produtos_map[codigo]['ofertas'].append(oferta)

            # Define o vencedor (Menor Preço)
            if preco < produtos_map[codigo]['melhor_preco']:
                produtos_map[codigo]['melhor_preco'] = preco
                produtos_map[codigo]['fornecedor_vencedor'] = fornecedor

        # Formatação final da lista de retorno
        lista_comparada = []
        for cod, dados in produtos_map.items():
            melhor_val = dados['melhor_preco']
            if melhor_val == float('inf'):
                melhor_val = 0.0
                
            dados['melhor_preco_formatado'] = f"R$ {melhor_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            dados['ofertas'].sort(key=lambda x: x['preco'])
            lista_comparada.append(dados)

        # ============================================================================
        # ✅ NOVO: Buscar a última data de processamento (tabela de controle)
        # ============================================================================
        cursor.execute("""
            SELECT ultima_data_processamento
            FROM controle_ultimo_processamento
            WHERE id = 1
            LIMIT 1;
        """)
        row_last = cursor.fetchone()

        ultima_data_br_formatada = ""
        ultima_data_br_iso = ""

        if row_last and row_last[0]:
            dt = row_last[0]
            br_tz = ZoneInfo("America/Fortaleza")

            # Se vier timezone-aware, converte; se vier naive, assume BR
            if getattr(dt, "tzinfo", None) is not None and dt.tzinfo is not None:
                dt_br = dt.astimezone(br_tz)
            else:
                dt_br = dt.replace(tzinfo=br_tz)

            ultima_data_br_formatada = dt_br.strftime("%d/%m/%Y %H:%M:%S")
            ultima_data_br_iso = dt_br.isoformat()

        return {
            "success": True,
            "total_produtos_analisados": len(lista_comparada),
            "ultima_data_processamento": ultima_data_br_formatada,   # ex: 05/01/2026 14:32:10
            "ultima_data_processamento_iso": ultima_data_br_iso,     # opcional (útil pro front)
            "comparativo": lista_comparada
        }

    except Exception as e:
        print(f"❌ Erro ao comparar preços no banco: {e}")
        return {"success": False, "error": str(e)}
    
    finally:
        if conn:
            conn.close()
