import asyncio
import re
from datetime import datetime
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

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
        return 0
    stock = re.sub(r"[^\d]", "", str(stock_str))
    try:
        return int(stock)
    except:
        return 0


# ===================== EXTJS: ACHAR O GRID CERTO (SEM ID) ===================== #
async def obter_grid_resultados(page, timeout_ms=4000):
    """
    Encontra o GRID correto do ExtJS baseado nos headers fixos, sem depender de IDs dinâmicos.
    """
    grid = page.locator(
        "div.x-panel.x-grid:visible"
        ":has(span.x-column-header-text-inner:has-text('PRODUTO'))"
        ":has(span.x-column-header-text-inner:has-text('REFERENCIA'))"
        ":has(span.x-column-header-text-inner:has-text('NOME'))"
        ":has(span.x-column-header-text-inner:has-text('FABRICANTE'))"
        ":has(span.x-column-header-text-inner:has-text('ESTOQUE'))"
        ":has(span.x-column-header-text-inner:has-text('UN'))"
        ":has(span.x-column-header-text-inner:has-text('PRECO'))"
        ":has(span.x-column-header-text-inner:has-text('A VISTA'))"
    ).first

    await grid.wait_for(state="visible", timeout=timeout_ms)
    return grid


# ===================== NAVEGAÇÃO ===================== #
async def navegar_para_carrinho(page):
    """
    Garantia: se já estiver vendo o input de pesquisa, não faz nada.
    Senão, tenta clicar no menu 'MEU CARRINHO'.
    """
    try:
        input_busca = page.locator("input[placeholder='Pesquisar por código']").first
        if await input_busca.is_visible():
            return True

        menu = page.locator("div.x-treelist-item-text:has-text('MEU CARRINHO')").first
        if await menu.is_visible():
            await menu.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(0.6)
            return True

        return False
    except Exception as e:
        print(f"⚠️ Erro ao navegar para carrinho: {e}")
        return False


async def abrir_modal_adicionar(page):
    """
    Se já está vendo o input de pesquisa, não precisa abrir modal.
    Senão, clica no botão 'Adicionar'.
    """
    try:
        input_busca = page.locator("input[placeholder='Pesquisar por código']").first
        if await input_busca.is_visible():
            return True

        btn = page.locator("span.x-btn-inner:has-text('Adicionar')").first
        if await btn.is_visible():
            await btn.click()
            await asyncio.sleep(0.6)
            return True

        return False
    except Exception as e:
        print(f"⚠️ Erro ao abrir modal: {e}")
        return False


# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    """
    Fluxo:
    1) MEU CARRINHO
    2) Adicionar
    3) input Pesquisar por código
    4) Enter 5x devagar
    5) Espera o grid certo aparecer (até 4s)
    """
    try:
        ok_carrinho = await navegar_para_carrinho(page)
        if not ok_carrinho:
            return False

        ok_add = await abrir_modal_adicionar(page)
        if not ok_add:
            return False

        campo = page.locator("input[placeholder='Pesquisar por código']").first
        await campo.wait_for(state="visible", timeout=20000)

        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")

        print(f"⌨️ Buscando código: {codigo}")
        await campo.fill(str(codigo))

        # Enter 5x devagar
        for _ in range(5):
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.7)

        # Aguarda o grid renderizar (SEM ID)
        await obter_grid_resultados(page, timeout_ms=4000)

        await asyncio.sleep(0.3)
        return True

    except Exception as e:
        print(f"❌ Busca falhou/sem grid em 4s: {e}")
        return False


# ===================== EXTRAÇÃO (VARRER TODOS TBODY/TABLES) ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    """
    Regra: varrer todos os table.x-grid-item (cada um tem tbody->tr)
    e achar a linha em que a coluna PRODUTO (td index 1) == codigo_solicitado.

    Colunas por índice:
    0 AÇÕES (ignora)
    1 PRODUTO (codigo)
    2 REFERENCIA
    3 NOME
    4 FABRICANTE
    5 ESTOQUE (Sim/Não ou número, depende)
    6 UN
    7 PRECO
    8 A VISTA (ignora)
    """
    codigo_solicitado = str(codigo_solicitado).strip()
    qtd_solic = int(quantidade_solicitada)

    try:
        grid = await obter_grid_resultados(page, timeout_ms=4000)

        container = grid.locator(".x-grid-item-container").first
        await container.wait_for(state="visible", timeout=4000)

        tables = container.locator("table.x-grid-item")
        total = await tables.count()

        if total == 0:
            return None

        async def td_text(row, idx):
            return (await row.locator("td.x-grid-cell").nth(idx)
                    .locator("div.x-grid-cell-inner").inner_text()).strip()

        for i in range(total):
            table = tables.nth(i)
            row = table.locator("tbody tr.x-grid-row").first
            if await row.count() == 0:
                continue

            td_count = await row.locator("td.x-grid-cell").count()
            if td_count < 8:
                continue

            codigo_encontrado = await td_text(row, 1)
            if codigo_encontrado != codigo_solicitado:
                continue

            referencia = await td_text(row, 2)
            nome = await td_text(row, 3)
            fabricante = await td_text(row, 4)
            estoque_raw = await td_text(row, 5)
            un = await td_text(row, 6)
            preco_raw = await td_text(row, 7)

            preco_num = clean_price(preco_raw)

            # Estoque no portal costuma ser Sim/Não
            estoque_txt = (estoque_raw or "").strip().lower()
            if estoque_txt in ["sim", "yes", "true"]:
                qtd_disp = 999999
                tem_estoque = True
            elif estoque_txt in ["não", "nao", "no", "false"]:
                qtd_disp = 0
                tem_estoque = False
            else:
                qtd_disp = clean_stock(estoque_raw)
                tem_estoque = qtd_disp > 0

            pode_comprar = tem_estoque and preco_num > 0 and qtd_disp >= qtd_solic
            valor_total = preco_num * qtd_solic

            item = {
                "codigo": codigo_encontrado,
                "cod_fabrica": referencia,
                "nome": nome,
                "marca": fabricante,
                "imagem": None,
                "unidade": un,
                "estoque_raw": estoque_raw,
                "preco": preco_raw,
                "preco_num": preco_num,
                "preco_formatado": format_brl(preco_num),
                "valor_total": valor_total,
                "valor_total_formatado": format_brl(valor_total),
                "uf": "RJ",
                "qtdSolicitada": qtd_solic,
                "qtdDisponivel": qtd_disp,
                "podeComprar": pode_comprar,
                "mensagem": None if pode_comprar else ("Sem estoque" if not tem_estoque else "Estoque insuficiente"),
                "disponivel": tem_estoque and preco_num > 0,
                "status": "Disponível" if (tem_estoque and preco_num > 0) else "Indisponível",
                "regioes": [{
                    "uf": "RJ",
                    "preco": preco_raw,
                    "preco_num": preco_num,
                    "preco_formatado": format_brl(preco_num),
                    "qtdSolicitada": qtd_solic,
                    "qtdDisponivel": qtd_disp,
                    "valor_total": valor_total,
                    "valor_total_formatado": format_brl(valor_total),
                    "podeComprar": pode_comprar,
                    "mensagem": None if pode_comprar else ("Sem estoque" if not tem_estoque else "Estoque insuficiente"),
                    "disponivel": tem_estoque
                }]
            }

            print(f"✅ ACHOU NO GRID: {codigo_encontrado} | {format_brl(preco_num)} | Estoque: {estoque_raw}")
            return item

        return None

    except Exception as e:
        print(f"❌ Erro ao extrair ({codigo_solicitado}): {e}")
        return None


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
    """
    Regras:
    - Para cada item: busca -> tenta extrair
    - Se não encontrar em 4s (grid não aparece ou código não aparece): pula pro próximo
    """
    page = page_or_tuple[2] if isinstance(page_or_tuple, (list, tuple)) else page_or_tuple
    itens_extraidos = []

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Buscando: {codigo}")

        try:
            ok = await buscar_produto(page, codigo)
            if not ok:
                print("⏭️ Sem grid em 4s (ou falha no fluxo). Pulando...")
                continue

            # Timeout geral de 4s pra achar o código dentro das linhas
            try:
                resultado = await asyncio.wait_for(
                    extrair_dados_produto(page, codigo, qtd),
                    timeout=4
                )
            except asyncio.TimeoutError:
                resultado = None

            if not resultado:
                print("⏭️ Código não apareceu no grid em 4s. Pulando...")
                continue

            itens_extraidos.append(resultado)
            await asyncio.sleep(0.3)

        except Exception as e:
            print(f"❌ Erro crítico no loop: {e}")
            try:
                await page.reload(wait_until="networkidle")
            except:
                pass

    if itens_extraidos and salvar_lote_sqlite:
        salvar_lote_sqlite(preparar_dados_finais(itens_extraidos))

    return itens_extraidos
