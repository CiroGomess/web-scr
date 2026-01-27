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

# ===================== LOADING: REGRA ABSOLUTA ===================== #
async def wait_loading_sumir(page, timeout=60000):
    """
    Espera o #loading SUMIR (hidden/detached).
    - Se não existir, segue.
    - Se existir e estiver visível, aguarda esconder.
    """
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
    """
    Garante que nenhuma ação ocorra com loader na tela.
    Se travar e tentar_recuperar=True, dá reload e tenta de novo.
    """
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

        ok2 = await wait_loading_sumir(page, timeout=timeout)
        return ok2

    return False

# Mantém a função existente (usada no seu loop), mas agora mais consistente.
async def verificar_e_recuperar_loading(page) -> bool:
    """
    Se #loading estiver visível, dá refresh e espera sumir.
    Retorna True se fez recuperação (reload), False se não precisou.
    """
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
    except Exception:
        pass
    return False

# ===================== HELPERS “COM CALMA” ===================== #
async def click_com_calma(locator, pre=0.4, post=0.6, force=True):
    try:
        page = locator.page
        await ensure_ready(page, timeout=60000, tentar_recuperar=True)
    except:
        pass

    try:
        await asyncio.sleep(pre)
        await locator.scroll_into_view_if_needed()
    except:
        pass

    await asyncio.sleep(pre)
    await locator.click(force=force)
    await asyncio.sleep(post)

async def limpar_e_digitar_com_calma(page, selector, texto, delay_keypress=70):
    await ensure_ready(page, timeout=60000, tentar_recuperar=True)

    await page.wait_for_selector(selector, state="visible", timeout=20000)
    campo = page.locator(selector).first

    await click_com_calma(campo, pre=0.25, post=0.25)
    await ensure_ready(page, timeout=60000, tentar_recuperar=True)

    await asyncio.sleep(0.2)
    await page.keyboard.press("Control+A")
    await asyncio.sleep(0.15)
    await page.keyboard.press("Backspace")
    await asyncio.sleep(0.25)

    await campo.type(str(texto), delay=delay_keypress)
    await asyncio.sleep(0.3)

    await ensure_ready(page, timeout=60000, tentar_recuperar=False)

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def navegar_para_pedido(page):
    """
    Navega DIRETO via URL para /Movimentacao.
    """
    try:
        url_atual = page.url or ""

        if "/Movimentacao" in url_atual:
            return

        base_url = "http://novo.plsweb.com.br"
        if ".br" in url_atual:
            base_url = url_atual.split(".br")[0] + ".br"

        target_url = base_url + "/Movimentacao"

        print(f"🚀 Navegando direto para: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

        # ✅ REGRA: não faz nada com loader na tela
        await ensure_ready(page, timeout=90000, tentar_recuperar=True)

        try:
            await page.wait_for_selector("a[href='#tabs-2'], #loading", timeout=10000)
        except:
            pass

    except Exception as e:
        print(f"⚠️ Erro ao navegar para Pedido: {e}")

async def ativar_aba_produtos(page):
    """Clica na aba 'Produtos' (#tabs-2) com calma e só avança sem loader."""
    try:
        await ensure_ready(page, timeout=60000, tentar_recuperar=True)

        aba_produtos = page.locator("a[href='#tabs-2']").first

        # Se o input já estiver visível, a aba já está ok
        try:
            if await page.locator("#codPeca").is_visible():
                return
        except:
            pass

        print("📑 Clicando na aba 'Produtos'...")
        try:
            await aba_produtos.wait_for(state="visible", timeout=10000)
        except:
            pass

        if await aba_produtos.count() > 0 and await aba_produtos.is_visible():
            await click_com_calma(aba_produtos, pre=0.6, post=1.0)

        # ✅ depois do clique, espera o loader sumir e o input aparecer
        await ensure_ready(page, timeout=90000, tentar_recuperar=True)
        await page.wait_for_selector("#codPeca", state="visible", timeout=15000)

    except Exception as e:
        print(f"⚠️ Erro ao ativar aba Produtos: {e}")

async def buscar_produto(page, codigo):
    try:
        await navegar_para_pedido(page)

        # Se travou no loading logo após navegar
        if await verificar_e_recuperar_loading(page):
            await navegar_para_pedido(page)

        # ================================================================
        # ⏳ WAIT FIXO PARA CARREGAMENTO DA TELA (MANTIDO)
        # ================================================================
        print("⏳ Aguardando 10 segundos fixos para carregamento da tela...")
        await asyncio.sleep(10)
        # ================================================================

        await ativar_aba_produtos(page)

        selector_busca = "#codPeca"
        print(f"⌨️ Digitando código: {codigo}")
        await limpar_e_digitar_com_calma(page, selector_busca, codigo, delay_keypress=70)

        print("🚀 Pressionando ENTER...")
        await asyncio.sleep(0.4)
        await page.keyboard.press("Enter")

        # ✅ REGRA PRINCIPAL: só prossegue quando #loading sumir
        print("⏳ Aguardando processamento da busca (#loading sumir)...")
        await ensure_ready(page, timeout=90000, tentar_recuperar=True)

        # tenta aguardar resultado, mas não falha se não vier
        print("⏳ Aguardando resultados...")
        try:
            await page.wait_for_selector("tr.jqgrow", timeout=6000)
        except:
            pass

        await asyncio.sleep(0.8)

    except Exception as e:
        print(f"❌ Erro na busca PLS: {e}")

# ===================== EXTRAÇÃO DOS DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    await ensure_ready(page, timeout=60000, tentar_recuperar=True)

    linhas = page.locator("tr.jqgrow")

    if await linhas.count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado.")
        return {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "RJ",
            "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }

    tr = linhas.first

    try:
        await asyncio.sleep(0.4)
        await ensure_ready(page, timeout=60000, tentar_recuperar=False)

        colunas = tr.locator("td")

        codigo_fab = (await colunas.nth(0).inner_text()).strip()
        nome_text = (await colunas.nth(2).inner_text()).strip()
        marca_text = (await colunas.nth(3).inner_text()).strip()

        estoque_raw = (await colunas.nth(7).inner_text()).strip()
        qtd_disponivel = clean_stock(estoque_raw)

        preco_raw = (await colunas.nth(9).inner_text()).strip()
        preco_num = clean_price(preco_raw)

        link_img = None
        tem_estoque = qtd_disponivel > 0 and preco_num > 0

    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque and (qtd_disponivel >= quantidade_solicitada)

    regiao_sp = {
        "uf": "RJ", "preco": preco_raw, "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num), "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel, "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total), "podeComprar": pode_comprar,
        "mensagem": None if pode_comprar else "Estoque insuficiente", "disponivel": tem_estoque
    }

    return {
        "codigo": codigo_fab, "nome": nome_text, "marca": marca_text, "imagem": link_img,
        "preco": preco_raw, "preco_num": preco_num, "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total, "valor_total_formatado": format_brl(valor_total),
        "uf": "RJ", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar, "mensagem": regiao_sp["mensagem"],
        "disponivel": tem_estoque, "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_sp]
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

    # === Extração segura da Page da Tupla ===
    if isinstance(login_data_ou_page, (tuple, list)):
        if len(login_data_ou_page) >= 3:
            page = login_data_ou_page[2]
        else:
            page = login_data_ou_page[-1]
    else:
        page = login_data_ou_page

    if not page or not hasattr(page, "goto"):
        print("❌ Erro: Objeto 'page' inválido recebido.")
        return []

    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste: 1867.8")
        lista_produtos = [{"codigo": "1867.8", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] PLS -> Buscando: {codigo}")

        # === LOOP DE RETRY PARA LOADING TRAVADO ===
        while True:
            try:
                # 0) REGRA: se tiver loader visível, resolve antes de tudo
                await ensure_ready(page, timeout=90000, tentar_recuperar=True)

                # 1) Verifica antes
                if await verificar_e_recuperar_loading(page):
                    continue

                await buscar_produto(page, codigo)

                # 2) Garante que a busca terminou e loader sumiu
                await ensure_ready(page, timeout=90000, tentar_recuperar=True)

                # 3) Verifica depois da busca
                if await verificar_e_recuperar_loading(page):
                    continue

                resultado = await extrair_dados_produto(page, codigo, qtd)

                if resultado:
                    itens_extraidos.append(resultado)

                await asyncio.sleep(1.1)
                break

            except Exception as e:
                print(f"❌ Erro crítico no loop F17: {e}")

                # tenta recuperar e continuar
                recuperou = await verificar_e_recuperar_loading(page)
                if recuperou:
                    continue

                try:
                    await page.reload(wait_until="domcontentloaded")
                    await ensure_ready(page, timeout=90000, tentar_recuperar=False)
                except:
                    pass
                break

    # SALVAMENTO
    if itens_extraidos and salvar_lote_sqlite:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]
        if validos:
            print(f"⏳ Salvando {len(validos)} itens no banco...")
            if salvar_lote_sqlite(preparar_dados_finais(validos)):
                print("✅ Banco atualizado!")
            else:
                print("❌ Erro ao salvar no banco.")

    return itens_extraidos
