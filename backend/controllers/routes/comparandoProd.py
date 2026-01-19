# controllers/routes/comparandoProd.py
import psycopg2
import json
from zoneinfo import ZoneInfo
from configs.db import get_connection


def _brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _codigo_pai(codigo: str) -> str:
    """
    Regra:
    - Se tiver '.', considera pai = antes do ponto (ex: '14354.3' -> '14354')
    - Caso contrário, o próprio código é o pai.
    """
    if not codigo:
        return ""
    if "." in codigo:
        return codigo.split(".", 1)[0]
    return codigo


def comparar_precos_entre_fornecedores():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ============================================================================
        # 🧠 QUERY INTELIGENTE COM AGREGAÇÃO JSON
        # ============================================================================
        # Adicionado ip.marca no SELECT e no GROUP BY
        query = """
            SELECT 
                ip.codigo_produto,
                ip.nome_produto,
                ip.imagem_url,
                ip.marca,
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
            GROUP BY ip.id, pl.id, ip.codigo_produto, ip.nome_produto, ip.imagem_url, ip.marca, pl.fornecedor, ip.preco_unitario, ip.qtd_disponivel, pl.data_processamento
            ORDER BY ip.codigo_produto, pl.data_processamento DESC;
        """

        cursor.execute(query)
        resultados = cursor.fetchall()

        # ============================================================================
        # 1) Monta o mapa "flat" por código exato
        # ============================================================================
        itens_por_codigo = {}

        for row in resultados:
            codigo = row[0]
            nome = row[1]
            imagem = row[2]
            marca = row[3]       # ✅ Novo campo Marca
            fornecedor = row[4]  # Índices deslocados +1
            preco = float(row[5]) if row[5] is not None else 0.0
            estoque = row[6]
            data = row[7]        
            regioes_raw = row[8] 

            if preco <= 0:
                continue

            data_formatada = data.strftime("%d/%m/%Y") if data else ""

            # Processa e formata os preços das regiões para o padrão BRL
            regioes_formatadas = []
            if regioes_raw:
                for reg in regioes_raw:
                    p_reg = float(reg.get("preco") or 0.0)
                    regioes_formatadas.append({
                        "uf": reg.get("uf"),
                        "preco": p_reg,
                        "preco_formatado": _brl(p_reg),
                        "estoque": reg.get("estoque"),
                    })

            # Inicializa o item no mapa se não existir
            if codigo not in itens_por_codigo:
                itens_por_codigo[codigo] = {
                    "codigo": codigo,
                    "nome": nome,
                    "imagem": imagem,
                    "marca": marca,  # ✅ Armazena a marca
                    "melhor_preco": float("inf"),
                    "fornecedor_vencedor": None,
                    "ofertas": []
                }

            # Evita duplicidade de fornecedor (mantém o mais recente)
            fornecedores_existentes = {o["fornecedor"] for o in itens_por_codigo[codigo]["ofertas"]}
            if fornecedor in fornecedores_existentes:
                continue

            oferta = {
                "fornecedor": fornecedor,
                "preco": preco,
                "preco_formatado": _brl(preco),
                "estoque": estoque,
                "data_atualizacao": data_formatada,
                "regioes": regioes_formatadas
            }

            itens_por_codigo[codigo]["ofertas"].append(oferta)

            # Define vencedor (menor preço)
            if preco < itens_por_codigo[codigo]["melhor_preco"]:
                itens_por_codigo[codigo]["melhor_preco"] = preco
                itens_por_codigo[codigo]["fornecedor_vencedor"] = fornecedor

        # Normaliza (formatos e ordenação interna)
        for cod, dados in itens_por_codigo.items():
            melhor_val = dados["melhor_preco"]
            if melhor_val == float("inf"):
                melhor_val = 0.0
            dados["melhor_preco"] = melhor_val
            dados["melhor_preco_formatado"] = _brl(melhor_val)
            dados["ofertas"].sort(key=lambda x: x["preco"])

        # ============================================================================
        # 2) Agrupa por código pai e coloca variações dentro
        # ============================================================================
        grupos_por_pai = {}

        for codigo, item in itens_por_codigo.items():
            pai = _codigo_pai(codigo)

            if pai not in grupos_por_pai:
                grupos_por_pai[pai] = {
                    "codigo": pai,
                    "nome": None,
                    "imagem": None,
                    "marca": None, # ✅ Campo marca no grupo
                    "tem_item_pai": False,
                    "item_pai": None, 
                    "variacoes": [],
                    "melhor_preco": float("inf"),
                    "melhor_preco_formatado": _brl(0.0),
                    "fornecedor_vencedor": None,
                }

            if codigo == pai:
                # É o pai real
                grupos_por_pai[pai]["tem_item_pai"] = True
                grupos_por_pai[pai]["item_pai"] = item
                grupos_por_pai[pai]["nome"] = item.get("nome")
                grupos_por_pai[pai]["imagem"] = item.get("imagem")
                grupos_por_pai[pai]["marca"] = item.get("marca") # ✅ Pega marca do pai real
            else:
                # É variação
                grupos_por_pai[pai]["variacoes"].append(item)
                
                # Fallback de nome/imagem/marca se o grupo ainda estiver vazio (pai virtual)
                if not grupos_por_pai[pai]["nome"]:
                    grupos_por_pai[pai]["nome"] = item.get("nome")
                if not grupos_por_pai[pai]["imagem"]:
                    grupos_por_pai[pai]["imagem"] = item.get("imagem")
                if not grupos_por_pai[pai]["marca"]:
                    grupos_por_pai[pai]["marca"] = item.get("marca") # ✅ Fallback da marca

        # ============================================================================
        # 3) LÓGICA DE PROMOÇÃO: VARIAÇÃO ÚNICA VIRA PRINCIPAL
        # ============================================================================
        for pai_key in list(grupos_por_pai.keys()):
            grupo = grupos_por_pai[pai_key]

            # SE não tem pai real (é virtual) E tem apenas 1 variação
            if not grupo["tem_item_pai"] and len(grupo["variacoes"]) == 1:
                unica_variacao = grupo["variacoes"][0]

                # Promove os dados da variação para o nível do grupo
                grupo["codigo"] = unica_variacao["codigo"] 
                grupo["nome"] = unica_variacao["nome"]
                grupo["imagem"] = unica_variacao["imagem"]
                grupo["marca"] = unica_variacao["marca"] # ✅ Marca promovida
                
                # Coloca a variação no slot 'item_pai'
                grupo["item_pai"] = unica_variacao
                
                # Esvazia a lista de variações
                grupo["variacoes"] = []
                grupo["tem_item_pai"] = False

        # ============================================================================
        # 4) Calcula melhor preço do grupo
        # ============================================================================
        for pai, grupo in grupos_por_pai.items():
            candidatos = []

            if grupo["item_pai"]:
                candidatos.append(grupo["item_pai"])

            candidatos.extend(grupo["variacoes"])

            for item in candidatos:
                mp = float(item.get("melhor_preco") or 0.0)
                if mp > 0 and mp < grupo["melhor_preco"]:
                    grupo["melhor_preco"] = mp
                    grupo["fornecedor_vencedor"] = item.get("fornecedor_vencedor")

            if grupo["melhor_preco"] == float("inf"):
                grupo["melhor_preco"] = 0.0

            grupo["melhor_preco_formatado"] = _brl(grupo["melhor_preco"])
            grupo["variacoes"].sort(key=lambda x: float(x.get("melhor_preco") or 0.0))

        # Lista final
        lista_comparada = list(grupos_por_pai.values())
        lista_comparada.sort(key=lambda g: (g["codigo"] or ""))

        # ============================================================================
        # 5) Metadados finais
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
            if getattr(dt, "tzinfo", None) is not None and dt.tzinfo is not None:
                dt_br = dt.astimezone(br_tz)
            else:
                dt_br = dt.replace(tzinfo=br_tz)

            ultima_data_br_formatada = dt_br.strftime("%d/%m/%Y %H:%M:%S")
            ultima_data_br_iso = dt_br.isoformat()

        return {
            "success": True,
            "total_produtos_analisados": len(lista_comparada),
            "ultima_data_processamento": ultima_data_br_formatada,
            "ultima_data_processamento_iso": ultima_data_br_iso,
            "comparativo": lista_comparada
        }

    except Exception as e:
        print(f"❌ Erro ao comparar preços no banco: {e}")
        return {"success": False, "error": str(e)}

    finally:
        if conn:
            conn.close()