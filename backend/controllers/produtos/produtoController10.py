# produtoController10.py

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
    preco = re.sub(r"[^\d,]", "", str(preco_str))
    preco = preco.replace(",", ".")
    try:
        return float(preco)
    except:
        return 0.0

def format_brl(valor):
    if valor is None or valor == 0:
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

# ===================== LOADING (OPCIONAL E SEGURO) ===================== #
async def verificar_e_recuperar_loading(page) -> bool:
    """
    Detecta loading travado e tenta recuperar com reload.
    Não gera exceção nem stacktrace.
    """
    try:
        loading = page.locator("#loading")
        if await loading.count() > 0 and await loading.is_visible():
            print("⚠️ Tela de carregamento travada. Recarregando página...")
            await page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(3)
            return True
    except:
        pass
    return False

# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        selector_busca = "input#codigo"

        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)

        campo = page.locator(selector_busca)
        await campo.click(force=True)
        await asyncio.sleep(0.2)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")

        print(f"⌨️ Digitando: {codigo}")
        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)

        print("🚀 Enter para pesquisar...")
        await page.keyboard.press("Enter")

        # 🔹 ESPERA CURTA E NÃO OBRIGATÓRIA (SEM TASKS)
        try:
            await page.wait_for_selector(
                ".product-card-modern-pedido",
                timeout=5000
            )
        except:
            print("ℹ️ Nenhum produto visível ainda (site pode estar lento). Continuando...")

        await asyncio.sleep(1.2)

    except Exception as e:
        print(f"⚠️ Não foi possível realizar a busca agora. Continuando. ({e})")

# ===================== EXTRAÇÃO ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):

    card_selector = ".product-card-modern-pedido"

    if await page.locator(card_selector).count() == 0:
        print(f"⚠️ Produto {codigo_solicitado} não encontrado ou site instável.")
        return {
            "codigo": codigo_solicitado,
            "nome": None,
            "marca": None,
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
        try:
            nome_text = (await card.locator(".product-title").inner_text()).strip()
        except:
            nome_text = "Produto sem nome"

        btn_add = card.locator("button.add-to-cart")

        codigo_fab = await btn_add.get_attribute("data-produto") or codigo_solicitado
        marca_text = await btn_add.get_attribute("data-fabricante") or "N/A"

        link_img = None
        try:
            img_container = card.locator(".product-image-container")
            img_attr = await img_container.get_attribute("data-img")
            if img_attr:
                link_img = img_attr if img_attr.startswith("http") else f"http://suportematriz.ddns.net:5006{img_attr}"
        except:
            pass

        preco_raw = await btn_add.get_attribute("data-preco")
        if preco_raw:
            preco_num = float(preco_raw)
            preco_visivel = f"R$ {preco_raw.replace('.', ',')}"
        else:
            try:
                preco_visivel = (await card.locator(".product-price").inner_text()).strip()
                preco_num = clean_price(preco_visivel)
            except:
                preco_visivel = "R$ 0,00"
                preco_num = 0.0

        qtd_disponivel = 0.0
        estoque_raw = await btn_add.get_attribute("data-qtdatual")
        if estoque_raw:
            qtd_disponivel = float(estoque_raw)
        else:
            try:
                texto_estoque = (await card.locator("span-estoque-carrinho").inner_text()).strip()
                qtd_disponivel = clean_stock(texto_estoque)
            except:
                pass

        tem_estoque = qtd_disponivel > 0

    except Exception as e:
        print(f"⚠️ Falha ao extrair dados do produto {codigo_solicitado}. ({e})")
        return None

    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque and qtd_disponivel >= quantidade_solicitada

    regiao_rj = {
        "uf": "RJ",
        "preco": preco_visivel,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "podeComprar": pode_comprar,
        "mensagem": None if pode_comprar else "Estoque insuficiente",
        "disponivel": tem_estoque
    }

    item_formatado = {
        "codigo": codigo_fab,
        "nome": nome_text,
        "marca": marca_text,
        "imagem": link_img,
        "preco": preco_visivel,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "uf": "RJ",
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar,
        "mensagem": regiao_rj["mensagem"],
        "disponivel": tem_estoque,
        "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_rj]
    }

    print(f"✅ SUCESSO MATRIZ: {codigo_fab} | {format_brl(preco_num)} | Estoque: {qtd_disponivel}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Suporte Matriz",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial10(login_data_ou_page, lista_produtos):
    itens_extraidos = []

    if isinstance(login_data_ou_page, (tuple, list)) and len(login_data_ou_page) >= 3:
        page = login_data_ou_page[2]
    else:
        page = login_data_ou_page

    if not page or not hasattr(page, "goto"):
        print("❌ Página inválida recebida.")
        return []

    if not lista_produtos:
        lista_produtos = [{"codigo": "10A1075C", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Matriz -> Buscando: {codigo}")

        while True:
            try:
                if await verificar_e_recuperar_loading(page):
                    continue

                await buscar_produto(page, codigo)

                if await verificar_e_recuperar_loading(page):
                    continue

                resultado = await extrair_dados_produto(page, codigo, qtd)
                if resultado:
                    itens_extraidos.append(resultado)

                await asyncio.sleep(1)
                break

            except Exception as e:
                print(f"⚠️ Problema temporário ao processar {codigo}. Pulando.")
                try:
                    await page.reload(wait_until="domcontentloaded")
                except:
                    pass
                break

    if itens_extraidos and salvar_lote_sqlite:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]
        if validos:
            print(f"⏳ Salvando {len(validos)} itens no banco...")
            salvar_lote_sqlite(preparar_dados_finais(validos))

    return itens_extraidos
