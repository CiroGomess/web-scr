# controllers/routes/comparandoProd.py
import psycopg2
import json
from zoneinfo import ZoneInfo
from configs.db import get_connection


def _brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _is_pai(codigo: str) -> bool:
    return bool(codigo) and ("." not in codigo)


def _codigo_pai(codigo: str) -> str:
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
            preco = float(row[4]) if row[4] is not None else 0.0
            estoque = row[5]
            data = row[6]
            regioes_raw = row[7]

            if preco <= 0:
                continue

            data_formatada = data.strftime("%d/%m/%Y") if data else ""

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

            if codigo not in produtos_map:
                produtos_map[codigo] = {
                    "codigo": codigo,
                    "nome": nome,
                    "imagem": imagem,
                    "melhor_preco": float("inf"),
                    "fornecedor_vencedor": None,
                    "ofertas": [],
                    # ✅ NOVO: chave sempre existe (compatibilidade)
                    "variacoes": []
                }

            # Evita duplicidade de fornecedor (mantém o mais recente por conta do ORDER BY data_processamento DESC)
            fornecedores_existentes = {o["fornecedor"] for o in produtos_map[codigo]["ofertas"]}
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

            produtos_map[codigo]["ofertas"].append(oferta)

            if preco < produtos_map[codigo]["melhor_preco"]:
                produtos_map[codigo]["melhor_preco"] = preco
                produtos_map[codigo]["fornecedor_vencedor"] = fornecedor

        # Normalização final por item (como era antes)
        lista_comparada = []
        for cod, dados in produtos_map.items():
            melhor_val = dados["melhor_preco"]
            if melhor_val == float("inf"):
                melhor_val = 0.0

            dados["melhor_preco"] = float(melhor_val)
            dados["melhor_preco_formatado"] = _brl(float(melhor_val))
            dados["ofertas"].sort(key=lambda x: x["preco"])

            # (variacoes permanece, vai ser preenchido depois só no pai)
            lista_comparada.append(dados)

        # ============================================================================
        # ✅ NOVO: Preencher variacoes APENAS dentro do PAI, sem mudar o retorno "flat"
        # ============================================================================
        # cria índice por código para inserir objetos completos nas variações
        idx_por_codigo = {p["codigo"]: p for p in lista_comparada}

        # mapeia pai -> lista de variações (objetos completos)
        variacoes_por_pai = {}
        for codigo, item in idx_por_codigo.items():
            if "." in codigo:
                pai = _codigo_pai(codigo)
                variacoes_por_pai.setdefault(pai, []).append(item)

        # injeta as variações dentro do item pai, mantendo o pai como destaque
        for pai_codigo, variacoes in variacoes_por_pai.items():
            pai_item = idx_por_codigo.get(pai_codigo)
            if not pai_item:
                # Se o pai NÃO existir no retorno atual, não inventa item novo (mantém "do jeito que estava").
                # Se você quiser criar "pai virtual", eu ajusto.
                continue

            # ordena variações pelo melhor preço (ou por código, se preferir)
            variacoes.sort(key=lambda x: float(x.get("melhor_preco") or 0.0))

            # garante que variações não carreguem variações dentro (evita recursão)
            for v in variacoes:
                v["variacoes"] = []

            pai_item["variacoes"] = variacoes

        # ============================================================================
        # ✅ Buscar a última data de processamento (tabela de controle)
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

        # mantém ordenação original (por código e data já veio do SQL; aqui não mexo além do sort opcional)
        lista_comparada.sort(key=lambda x: (x.get("codigo") or ""))

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
