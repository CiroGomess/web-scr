# controllers/routes/comparandoProd.py
import json
from zoneinfo import ZoneInfo
from datetime import datetime

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


def _to_float(v, default=0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _parse_dt_sqlite(v):
    """
    SQLite normalmente retorna TEXT para datas.
    Aceita:
      - datetime (se algum adapter estiver convertendo)
      - str ISO (2026-01-19T14:29:19...)
      - str SQL (2026-01-19 14:29:19)
    """
    if v is None:
        return None
    if isinstance(v, datetime):
        return v

    if isinstance(v, str):
        s = v.strip()
        # tenta ISO
        try:
            return datetime.fromisoformat(s)
        except Exception:
            pass
        # tenta formato "YYYY-MM-DD HH:MM:SS"
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    return None


def comparar_precos_entre_fornecedores():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ============================================================================
        # ✅ SQLITE: Query "flat" (sem agregação JSON no SQL)
        # ============================================================================
        # Observação: aqui supomos que:
        # - processamentos_lotes.data_processamento existe
        # - itens_detalhes_regionais pode ter várias linhas por item_id
        # - preco_unitario > 0 é o filtro base
        query = """
            SELECT
                ip.id AS item_id,
                ip.codigo_produto,
                ip.nome_produto,
                ip.imagem_url,
                ip.marca,
                pl.fornecedor,
                ip.preco_unitario,
                ip.qtd_disponivel,
                pl.data_processamento,
                idr.id AS reg_id,
                idr.uf,
                idr.preco_regional,
                idr.qtd_disponivel_regional
            FROM itens_processados ip
            JOIN processamentos_lotes pl ON ip.lote_id = pl.id
            LEFT JOIN itens_detalhes_regionais idr ON ip.id = idr.item_id
            WHERE ip.preco_unitario > 0
            ORDER BY ip.codigo_produto, pl.data_processamento DESC;
        """

        cursor.execute(query)
        resultados = cursor.fetchall()

        # ============================================================================
        # 0) Monta estrutura temporária por "chave de oferta"
        #    (codigo + fornecedor) para agregar regiões corretamente
        # ============================================================================
        ofertas_por_chave = {}
        # Estrutura:
        # ofertas_por_chave[(codigo, fornecedor)] = {
        #   base do item/oferta,
        #   regioes_dict por UF (para não duplicar)
        # }

        for row in resultados:
            # sqlite3.Row permite index e nome
            item_id = row[0]
            codigo = row[1]
            nome = row[2]
            imagem = row[3]
            marca = row[4]
            fornecedor = row[5]
            preco = _to_float(row[6], 0.0)
            estoque = row[7]
            data_raw = row[8]

            reg_id = row[9]
            uf = row[10]
            preco_regional = _to_float(row[11], 0.0)
            estoque_regional = row[12]

            if preco <= 0:
                continue

            dt = _parse_dt_sqlite(data_raw)
            data_formatada = dt.strftime("%d/%m/%Y") if dt else ""

            chave = (codigo, fornecedor)

            if chave not in ofertas_por_chave:
                ofertas_por_chave[chave] = {
                    "codigo": codigo,
                    "nome": nome,
                    "imagem": imagem,
                    "marca": marca,
                    "fornecedor": fornecedor,
                    "preco": preco,
                    "preco_formatado": _brl(preco),
                    "estoque": estoque,
                    "data_atualizacao": data_formatada,
                    "regioes_dict": {}  # uf -> obj
                }

            # agrega região se existir
            if reg_id is not None and uf:
                # evita duplicar UF
                if uf not in ofertas_por_chave[chave]["regioes_dict"]:
                    ofertas_por_chave[chave]["regioes_dict"][uf] = {
                        "uf": uf,
                        "preco": preco_regional,
                        "preco_formatado": _brl(preco_regional),
                        "estoque": estoque_regional
                    }

        # ============================================================================
        # 1) Monta o mapa "flat" por código exato (como você já fazia)
        # ============================================================================
        itens_por_codigo = {}

        for (codigo, fornecedor), oferta_base in ofertas_por_chave.items():
            # regiões ordenadas por UF
            regioes_formatadas = list(oferta_base["regioes_dict"].values())
            regioes_formatadas.sort(key=lambda x: (x.get("uf") or ""))

            # Inicializa o item no mapa se não existir
            if codigo not in itens_por_codigo:
                itens_por_codigo[codigo] = {
                    "codigo": codigo,
                    "nome": oferta_base["nome"],
                    "imagem": oferta_base["imagem"],
                    "marca": oferta_base["marca"],
                    "melhor_preco": float("inf"),
                    "fornecedor_vencedor": None,
                    "ofertas": []
                }

            oferta = {
                "fornecedor": fornecedor,
                "preco": oferta_base["preco"],
                "preco_formatado": oferta_base["preco_formatado"],
                "estoque": oferta_base["estoque"],
                "data_atualizacao": oferta_base["data_atualizacao"],
                "regioes": regioes_formatadas
            }

            itens_por_codigo[codigo]["ofertas"].append(oferta)

            # Define vencedor (menor preço)
            if oferta_base["preco"] < itens_por_codigo[codigo]["melhor_preco"]:
                itens_por_codigo[codigo]["melhor_preco"] = oferta_base["preco"]
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
        # 2) Agrupa por código pai e coloca variações dentro (igual ao seu)
        # ============================================================================
        grupos_por_pai = {}

        for codigo, item in itens_por_codigo.items():
            pai = _codigo_pai(codigo)

            if pai not in grupos_por_pai:
                grupos_por_pai[pai] = {
                    "codigo": pai,
                    "nome": None,
                    "imagem": None,
                    "marca": None,
                    "tem_item_pai": False,
                    "item_pai": None,
                    "variacoes": [],
                    "melhor_preco": float("inf"),
                    "melhor_preco_formatado": _brl(0.0),
                    "fornecedor_vencedor": None,
                }

            if codigo == pai:
                grupos_por_pai[pai]["tem_item_pai"] = True
                grupos_por_pai[pai]["item_pai"] = item
                grupos_por_pai[pai]["nome"] = item.get("nome")
                grupos_por_pai[pai]["imagem"] = item.get("imagem")
                grupos_por_pai[pai]["marca"] = item.get("marca")
            else:
                grupos_por_pai[pai]["variacoes"].append(item)

                if not grupos_por_pai[pai]["nome"]:
                    grupos_por_pai[pai]["nome"] = item.get("nome")
                if not grupos_por_pai[pai]["imagem"]:
                    grupos_por_pai[pai]["imagem"] = item.get("imagem")
                if not grupos_por_pai[pai]["marca"]:
                    grupos_por_pai[pai]["marca"] = item.get("marca")

        # ============================================================================
        # 3) Promoção: variação única vira principal (igual ao seu)
        # ============================================================================
        for pai_key in list(grupos_por_pai.keys()):
            grupo = grupos_por_pai[pai_key]
            if not grupo["tem_item_pai"] and len(grupo["variacoes"]) == 1:
                unica_variacao = grupo["variacoes"][0]

                grupo["codigo"] = unica_variacao["codigo"]
                grupo["nome"] = unica_variacao["nome"]
                grupo["imagem"] = unica_variacao["imagem"]
                grupo["marca"] = unica_variacao["marca"]

                grupo["item_pai"] = unica_variacao
                grupo["variacoes"] = []
                grupo["tem_item_pai"] = False

        # ============================================================================
        # 4) Calcula melhor preço do grupo (igual ao seu)
        # ============================================================================
        for pai, grupo in grupos_por_pai.items():
            candidatos = []

            if grupo["item_pai"]:
                candidatos.append(grupo["item_pai"])
            candidatos.extend(grupo["variacoes"])

            for item in candidatos:
                mp = _to_float(item.get("melhor_preco"), 0.0)
                if mp > 0 and mp < grupo["melhor_preco"]:
                    grupo["melhor_preco"] = mp
                    grupo["fornecedor_vencedor"] = item.get("fornecedor_vencedor")

            if grupo["melhor_preco"] == float("inf"):
                grupo["melhor_preco"] = 0.0

            grupo["melhor_preco_formatado"] = _brl(grupo["melhor_preco"])
            grupo["variacoes"].sort(key=lambda x: _to_float(x.get("melhor_preco"), 0.0))

        # Lista final
        lista_comparada = list(grupos_por_pai.values())
        lista_comparada.sort(key=lambda g: (g["codigo"] or ""))

        # ============================================================================
        # 5) Metadados finais (SQLite: provável TEXT)
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
            dt = _parse_dt_sqlite(row_last[0])
            if dt:
                br_tz = ZoneInfo("America/Fortaleza")
                # se vier sem tz, seta tz BR
                if dt.tzinfo is None:
                    dt_br = dt.replace(tzinfo=br_tz)
                else:
                    dt_br = dt.astimezone(br_tz)

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
        print(f"❌ Erro ao comparar preços no banco (SQLite): {e}")
        return {"success": False, "error": str(e)}

    finally:
        if conn:
            conn.close()
