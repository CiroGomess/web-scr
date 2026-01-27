# produtoController12.py

import asyncio
import re
from datetime import datetime

# ===================== IMPORTAÇÃO DO SERVIÇO DE BANCO ===================== #
try:
    from services.db_saver import salvar_lote_sqlite
except ImportError:
    print("⚠️ Aviso: 'services.db_saver' não encontrado. O salvamento no banco será pulado.")
    salvar_lote_sqlite = None

# ===================== AUXILIARES ===================== #
def clean_price(preco_str):
    if not preco_str:
        return 0.0
    preco = re.sub(r"[^\d,]", "", str(preco_str)).replace(",", ".")
    try:
        return float(preco)
    except:
        return 0.0

def format_brl(valor):
    if not valor:
        return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def clean_stock(stock_str):
    if not stock_str:
        return 0.0
    stock = re.sub(r"[^\d]", "", str(stock_str))
    try:
        return float(stock)
    except:
        return 0.0

# ===================== SAFE HELPERS ===================== #
async def safe_dom_ready(page, timeout=60000):
    """
    Takao é extremamente lento e inconsistente.
    Este helper garante estabilidade sem explodir timeout.
    """
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)
    except:
        pass

async def safe_reload(page, motivo=""):
    try:
        print(f"🔄 Reload seguro Takao {('— ' + motivo) if motivo else ''}")
        await page.reload(wait_until="domcontentloaded", timeout=90000)
        await safe_dom_ready(page)
        return True
    except:
        return False

# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        selector_busca = "input#inputSearch"

        # Takao é lento → timeout alto
        await page.wait_for_selector(selector_busca, state="visible", timeout=90000)

        campo = page.locator(selector_busca).first
        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.6)

        await campo.fill(str(codigo))
        await asyncio.sleep(1.2)

        print(f"⌛ Pesquisando {codigo}...")
        await page.keyboard.press("Enter")

        print("⏳ Aguardando cards (Takao é lento)...")
        try:
            await page.wait_for_selector("app-card-produto-home", timeout=90000)
            await asyncio.sleep(8)  # renderização final de preço/estoque
        except:
            print("ℹ️ Nenhum card encontrado para este código.")

    except:
        print(f"⚠️ Falha na busca Takao ({codigo}).")

# ===================== EXTRAÇÃO ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    card_selector = "app-card-produto-home"

    if await page.locator(card_selector).count() == 0:
        print(f"ℹ️ {codigo_solicitado} não encontrado.")
        return {
            "codigo": codigo_solicitado,
            "nome": None,
            "marca": "Takao",
            "imagem": None,
            "preco": "R$ 0,00",
            "preco_num": 0.0,
            "preco_formatado": "R$ 0,00",
            "valor_total": 0.0,
            "valor_total_formatado": "R$ 0,00",
            "uf": "RJ",
            "qtdSolicitada": quantidade_solicitada,
            "qtdDisponivel": 0,
            "podeComprar": False,
            "disponivel": False,
            "status": "Não encontrado",
            "regioes": []
        }

    card = page.locator(card_selector).first

    try:
        nome_el = card.locator("span.modelo b")
        nome_base = (await nome_el.inner_text()).strip() if await nome_el.count() > 0 else str(codigo_solicitado)

        try:
            desc_el = card.locator("div.descricao")
            descricao = (await desc_el.inner_text()).strip()
            nome = f"{nome_base} - {descricao}"
        except:
            nome = nome_base

        img_el = card.locator("img.image")
        imagem = await img_el.get_attribute("src") if await img_el.count() > 0 else None

        preco_raw = "0,00"
        try:
            preco_el = card.locator("span.preco").first
            await preco_el.wait_for(state="visible", timeout=8000)
            preco_raw = (await preco_el.inner_text()).split("\n")[0].strip()
        except:
            pass

        preco_num = clean_price(preco_raw)

        qtd_disponivel = 0.0
        try:
            linha = card.locator(".tabela-body .row").first
            cols = linha.locator("div[class*='col-']")
            for i in range(await cols.count() - 1, -1, -1):
                txt = await cols.nth(i).inner_text()
                val = clean_stock(txt)
                if val > 0:
                    qtd_disponivel = val
                    break
        except:
            pass

        btn_add = card.locator("button.btn-adicionar")
        tem_estoque = await btn_add.is_visible() and (preco_num > 0 or qtd_disponivel > 0)

    except:
        print(f"⚠️ Falha ao extrair dados do card Takao ({codigo_solicitado}).")
        return None

    valor_total = preco_num * quantidade_solicitada

    regiao = {
        "uf": "RJ",
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "podeComprar": tem_estoque,
        "mensagem": None if tem_estoque else "Indisponível",
        "disponivel": tem_estoque
    }

    item = {
        "codigo": nome_base,
        "nome": nome,
        "marca": "Takao",
        "imagem": imagem,
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "uf": "RJ",
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "podeComprar": tem_estoque,
        "mensagem": regiao["mensagem"],
        "disponivel": tem_estoque,
        "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao]
    }

    print(f"✅ TAKAO OK: {nome_base} | {format_brl(preco_num)} | Estoque: {qtd_disponivel}")
    return item

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Takao",
        "total_itens": len(itens),
        "itens": itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial12(login_data_ou_page, lista_produtos):
    itens = []

    page = login_data_ou_page[2] if isinstance(login_data_ou_page, (tuple, list)) else login_data_ou_page
    if not page:
        print("❌ Page inválida.")
        return []

    if not lista_produtos:
        lista_produtos = [{"codigo": "31968", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]
    else:
        lista_produtos = [
            item if isinstance(item, dict) else {"codigo": item, "quantidade": 1}
            for item in lista_produtos
        ]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Takao -> {codigo}")

        try:
            await buscar_produto(page, codigo)
            await asyncio.sleep(2)

            resultado = await extrair_dados_produto(page, codigo, qtd)
            if resultado:
                itens.append(resultado)

            await asyncio.sleep(3)

        except:
            print(f"⚠️ Produto {codigo} ignorado por instabilidade Takao.")
            await safe_reload(page, motivo="erro Takao")

    if itens and salvar_lote_sqlite:
        validos = [r for r in itens if r and r.get("status") != "Não encontrado"]
        if validos:
            print(f"⏳ Salvando {len(validos)} itens Takao...")
            salvar_lote_sqlite(preparar_dados_finais(validos))

    return itens
