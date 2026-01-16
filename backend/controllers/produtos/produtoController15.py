import asyncio
import re
from datetime import datetime

# ===================== IMPORTAÇÃO DO SERVIÇO DE BANCO ===================== #
try:
    from services.db_saver import salvar_lote_postgres
except ImportError:
    print("⚠️ Aviso: 'services.db_saver' não encontrado. O salvamento no banco será pulado.")
    salvar_lote_postgres = None


# ===================== AUXILIARES ===================== #
def clean_price(preco_str):
    if not preco_str:
        return 0.0
    preco = re.sub(r"[^\d,]", "", preco_str)
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
        return 0
    stock = re.sub(r"[^\d]", "", stock_str)
    try:
        return int(stock)
    except:
        return 0


# ===================== NAVEGAÇÃO ===================== #
async def navegar_para_carrinho(page):
    try:
        if await page.locator("input[placeholder='Pesquisar por código']").is_visible():
            return

        menu = page.locator("div.x-treelist-item-text:has-text('MEU CARRINHO')")
        if await menu.is_visible():
            await menu.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
    except Exception as e:
        print(f"⚠️ Erro ao navegar para carrinho: {e}")


async def abrir_modal_adicionar(page):
    try:
        if await page.locator("input[placeholder='Pesquisar por código']").is_visible():
            return

        btn = page.locator("span.x-btn-inner:has-text('Adicionar')")
        if await btn.is_visible():
            await btn.click()
            await asyncio.sleep(2)
    except Exception as e:
        print(f"⚠️ Erro ao abrir modal: {e}")


async def buscar_produto(page, codigo):
    try:
        await navegar_para_carrinho(page)
        await abrir_modal_adicionar(page)

        campo = page.locator("input[placeholder='Pesquisar por código']")
        await campo.wait_for(state="visible", timeout=20000)

        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")

        print(f"⌨️ Buscando código: {codigo}")
        await campo.fill(str(codigo))
        await asyncio.sleep(1)

        for _ in range(5):
            await page.keyboard.press("Enter")
            await asyncio.sleep(1.2)

        await page.wait_for_selector(
            "div.x-grid-item-container table.x-grid-item",
            timeout=15000
        )

        await asyncio.sleep(1.5)

    except Exception as e:
        print(f"❌ Erro na busca: {e}")


# ===================== EXTRAÇÃO (EXTJS DEFINITIVO) ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):

    # 🔒 ÂNCORA EXATA: div que TEM a table.x-grid-item como filha
    table = page.locator(
        "div.x-grid-item-container > table.x-grid-item"
    ).first

    await table.wait_for(state="visible", timeout=15000)

    tbody = table.locator("tbody")
    await tbody.wait_for(state="visible", timeout=15000)

    row = tbody.locator("tr.x-grid-row").first
    await row.wait_for(state="visible", timeout=15000)

    def cell(column_id):
        return row.locator(
            f"td[data-columnid='{column_id}'] div.x-grid-cell-inner"
        )

    try:
        codigo_fab  = (await cell("gridcolumn-1500").inner_text()).strip()
        cod_fabrica = (await cell("gridcolumn-1501").inner_text()).strip()
        nome        = (await cell("gridcolumn-1502").inner_text()).strip()
        marca       = (await cell("gridcolumn-1503").inner_text()).strip()
        preco_raw   = (await cell("gridcolumn-1506").inner_text()).strip()
        estoque_raw = (await cell("gridcolumn-1507").inner_text()).strip()
    except Exception as e:
        print(f"❌ Falha ao extrair dados do grid: {e}")
        return None

    preco_num = clean_price(preco_raw)
    qtd_disp = clean_stock(estoque_raw)

    tem_estoque = preco_num > 0 and qtd_disp >= 0
    pode_comprar = tem_estoque and qtd_disp >= quantidade_solicitada
    valor_total = preco_num * quantidade_solicitada

    item = {
        "codigo": codigo_fab,
        "cod_fabrica": cod_fabrica,
        "nome": nome,
        "marca": marca,
        "imagem": None,
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "uf": "RJ",
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disp,
        "podeComprar": pode_comprar,
        "mensagem": None if pode_comprar else "Estoque insuficiente",
        "disponivel": tem_estoque,
        "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [{
            "uf": "RJ",
            "preco": preco_raw,
            "preco_num": preco_num,
            "preco_formatado": format_brl(preco_num),
            "qtdSolicitada": quantidade_solicitada,
            "qtdDisponivel": qtd_disp,
            "valor_total": valor_total,
            "valor_total_formatado": format_brl(valor_total),
            "podeComprar": pode_comprar,
            "mensagem": None if pode_comprar else "Estoque insuficiente",
            "disponivel": tem_estoque
        }]
    }

    print(f"✅ SUCESSO: {codigo_fab} | {format_brl(preco_num)} | Estoque: {qtd_disp}")
    return item


# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedor": "Fornecedor 15 (RioJC)",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }


# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial15(page_or_tuple, lista_produtos):

    page = page_or_tuple[2] if isinstance(page_or_tuple, (list, tuple)) else page_or_tuple
    itens_extraidos = []

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Buscando: {codigo}")

        try:
            await buscar_produto(page, codigo)
            resultado = await extrair_dados_produto(page, codigo, qtd)

            if resultado:
                itens_extraidos.append(resultado)

            await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ Erro crítico no loop: {e}")
            try:
                await page.reload(wait_until="networkidle")
            except:
                pass

    if itens_extraidos and salvar_lote_postgres:
        salvar_lote_postgres(preparar_dados_finais(itens_extraidos))

    return itens_extraidos
