# produtoController17.py

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

# ===================== MODAL BOOTSTRAP KILLER ===================== #
async def fechar_modais_bootstrap(page, motivo=""):
    """
    Remove qualquer modal Bootstrap ativo que possa interceptar cliques.
    Seguro, idempotente e silencioso.
    """
    try:
        await page.evaluate("""
        () => {
            document.querySelectorAll('.modal.show').forEach(m => m.remove());
            document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('padding-right');
        }
        """)
        if motivo:
            print(f"🧹 Modal Bootstrap removido ({motivo})")
        await asyncio.sleep(0.25)
        return True
    except Exception as e:
        print(f"ℹ️ Falha ao remover modal Bootstrap: {e}")
        return False

# ===================== LOADING: REGRA ABSOLUTA ===================== #
async def wait_loading_sumir(page, timeout=60000):
    try:
        loading = page.locator("#loading")
        if await loading.count() == 0:
            return True

        if await loading.is_visible():
            print("⏳ #loading visível... aguardando sumir.")
            await loading.wait_for(state="hidden", timeout=timeout)
            print("✅ #loading sumiu.")
        return True
    except Exception as e:
        print(f"⚠️ Timeout/erro aguardando #loading sumir: {e}")
        return False

async def ensure_ready(page, timeout=60000, tentar_recuperar=True):
    ok = await wait_loading_sumir(page, timeout=timeout)
    if ok:
        return True

    if tentar_recuperar:
        print("⚠️ #loading pode estar travado. Tentando recuperar com reload...")
        try:
            await page.reload()
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=20000)
            except:
                pass
        except Exception as e:
            print(f"⚠️ Falha no reload de recuperação: {e}")

        return await wait_loading_sumir(page, timeout=timeout)

    return False

async def verificar_e_recuperar_loading(page) -> bool:
    try:
        loading = page.locator("#loading")
        if await loading.count() > 0 and await loading.is_visible():
            print("⚠️ TELA DE LOADING DETECTADA! Iniciando recuperação...")
            await page.reload()
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=20000)
            except:
                pass
            await wait_loading_sumir(page, timeout=60000)
            print("🔄 Página atualizada. Retomando fluxo...")
            return True
    except:
        pass
    return False

# ===================== HELPERS COM CALMA ===================== #
async def click_com_calma(locator, pre=0.4, post=0.6, force=True):
    try:
        await ensure_ready(locator.page, timeout=60000, tentar_recuperar=True)
    except:
        pass

    await fechar_modais_bootstrap(locator.page, "antes do clique")

    try:
        await asyncio.sleep(pre)
        await locator.scroll_into_view_if_needed()
        await locator.click(force=force)
    except:
        pass

    await asyncio.sleep(post)

async def limpar_e_digitar_com_calma(page, selector, texto, delay_keypress=70):
    await ensure_ready(page, timeout=60000, tentar_recuperar=True)
    await fechar_modais_bootstrap(page, "antes de digitar")

    await page.wait_for_selector(selector, state="visible", timeout=20000)
    campo = page.locator(selector).first

    await click_com_calma(campo, pre=0.25, post=0.25)

    await page.keyboard.press("Control+A")
    await asyncio.sleep(0.15)
    await page.keyboard.press("Backspace")
    await asyncio.sleep(0.25)

    await campo.type(str(texto), delay=delay_keypress)
    await asyncio.sleep(0.3)

# ===================== NAVEGAÇÃO ===================== #
async def navegar_para_pedido(page):
    try:
        url_atual = page.url or ""
        if "/Movimentacao" in url_atual:
            return

        base_url = url_atual.split(".br")[0] + ".br" if ".br" in url_atual else "http://novo.plsweb.com.br"
        target_url = base_url + "/Movimentacao"

        print(f"🚀 Navegando direto para: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await ensure_ready(page, timeout=90000, tentar_recuperar=True)
    except Exception as e:
        print(f"⚠️ Erro ao navegar para Pedido: {e}")

async def ativar_aba_produtos(page):
    try:
        await ensure_ready(page, timeout=60000, tentar_recuperar=True)
        await fechar_modais_bootstrap(page, "antes de ativar aba")

        if await page.locator("#codPeca").is_visible():
            return

        aba = page.locator("a[href='#tabs-2']").first
        if await aba.count() > 0:
            await click_com_calma(aba, pre=0.6, post=1.0)

        await ensure_ready(page, timeout=90000, tentar_recuperar=True)
        await page.wait_for_selector("#codPeca", state="visible", timeout=15000)
    except Exception as e:
        print(f"⚠️ Erro ao ativar aba Produtos: {e}")

# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        await navegar_para_pedido(page)

        if await verificar_e_recuperar_loading(page):
            await navegar_para_pedido(page)

        print("⏳ Aguardando 10 segundos fixos para carregamento da tela...")
        await asyncio.sleep(10)

        await ativar_aba_produtos(page)

        print(f"⌨️ Digitando código: {codigo}")
        await limpar_e_digitar_com_calma(page, "#codPeca", codigo, delay_keypress=70)

        print("🚀 Pressionando ENTER...")
        await fechar_modais_bootstrap(page, "antes do ENTER")
        await page.keyboard.press("Enter")

        print("⏳ Aguardando processamento da busca (#loading sumir)...")
        await ensure_ready(page, timeout=90000, tentar_recuperar=True)

        try:
            await page.wait_for_selector("tr.jqgrow", timeout=6000)
        except:
            pass

    except Exception as e:
        print(f"❌ Erro na busca PLS: {e}")

# ===================== EXTRAÇÃO ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    await ensure_ready(page, timeout=60000, tentar_recuperar=True)
    await fechar_modais_bootstrap(page, "antes da extração")

    linhas = page.locator("tr.jqgrow")
    if await linhas.count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado.")
        return None

    tr = linhas.first

    try:
        colunas = tr.locator("td")
        codigo_fab = (await colunas.nth(0).inner_text()).strip()
        nome_text = (await colunas.nth(2).inner_text()).strip()
        marca_text = (await colunas.nth(3).inner_text()).strip()

        estoque_raw = (await colunas.nth(7).inner_text()).strip()
        qtd_disponivel = clean_stock(estoque_raw)

        preco_raw = (await colunas.nth(9).inner_text()).strip()
        preco_num = clean_price(preco_raw)

    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

    valor_total = preco_num * quantidade_solicitada
    pode_comprar = qtd_disponivel >= quantidade_solicitada and preco_num > 0

    return {
        "codigo": codigo_fab,
        "nome": nome_text,
        "marca": marca_text,
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar,
        "status": "Disponível" if pode_comprar else "Indisponível",
        "regioes": []
    }

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Odapel",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial17(login_data_ou_page, lista_produtos):
    itens_extraidos = []

    page = login_data_ou_page[2] if isinstance(login_data_ou_page, (tuple, list)) else login_data_ou_page
    if not page or not hasattr(page, "goto"):
        print("❌ Erro: Objeto 'page' inválido recebido.")
        return []

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] PLS -> Buscando: {codigo}")

        while True:
            try:
                await ensure_ready(page, timeout=90000, tentar_recuperar=True)

                if await verificar_e_recuperar_loading(page):
                    continue

                await buscar_produto(page, codigo)

                await ensure_ready(page, timeout=90000, tentar_recuperar=True)

                resultado = await extrair_dados_produto(page, codigo, qtd)
                if resultado:
                    itens_extraidos.append(resultado)

                await asyncio.sleep(1.1)
                break

            except Exception as e:
                print(f"❌ Erro crítico no loop F17: {e}")
                if await verificar_e_recuperar_loading(page):
                    continue
                try:
                    await page.reload(wait_until="domcontentloaded")
                except:
                    pass
                break

    if itens_extraidos and salvar_lote_sqlite:
        validos = [r for r in itens_extraidos if r]
        if validos:
            print(f"⏳ Salvando {len(validos)} itens no banco...")
            salvar_lote_sqlite(preparar_dados_finais(validos))

    return itens_extraidos
