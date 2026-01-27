# produtoController14.py

import asyncio
import re
from datetime import datetime

# Variável de controle para remover o tutorial apenas uma vez
bloqueios_removidos = False

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

# ===================== PAGE RESOLVER ===================== #
def resolver_page(login_data_ou_page):
    if isinstance(login_data_ou_page, (tuple, list)):
        if len(login_data_ou_page) >= 3:
            return login_data_ou_page[2]
        return login_data_ou_page[-1]
    return login_data_ou_page

async def safe_reload(page, motivo="", wait_until="domcontentloaded"):
    try:
        print(f"🔄 Reload (safe) {('— ' + motivo) if motivo else ''}")
        await page.reload(wait_until=wait_until, timeout=60000)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
        except:
            pass
        return True
    except Exception as e:
        print(f"⚠️ Falha no reload: {e}")
        return False

# ===================== TIMEOUT HELPER ===================== #
async def extrair_com_timeout(coro, timeout_s=5):
    try:
        return await asyncio.wait_for(coro, timeout=timeout_s)
    except asyncio.TimeoutError:
        return "__TIMEOUT__"

# ===================== MODAL BOOTSTRAP KILLER ===================== #
async def fechar_modais_bootstrap(page, motivo=""):
    """
    Remove QUALQUER modal Bootstrap visível que esteja interceptando cliques.
    Idempotente e seguro.
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
        else:
            print("🧹 Modal Bootstrap removido")
        await asyncio.sleep(0.25)
        return True
    except Exception as e:
        print(f"ℹ️ Falha ao remover modal Bootstrap: {e}")
        return False

# ===================== FECHADOR DRIVER.JS ===================== #
async def fechar_driver_tutorial(page, motivo=""):
    try:
        btn_close = page.locator("button.driver-popover-close-btn")
        popover = page.locator(".driver-popover")

        for _ in range(3):
            await asyncio.sleep(0.6)

            if await btn_close.count() == 0:
                return False

            try:
                await btn_close.first.wait_for(state="visible", timeout=2500)
            except:
                continue

            try:
                await btn_close.first.click(force=True, timeout=3000)
            except:
                await page.evaluate("""
                    () => {
                        const btn = document.querySelector('button.driver-popover-close-btn');
                        if (btn) btn.click();
                    }
                """)

            try:
                await popover.first.wait_for(state="hidden", timeout=6000)
            except:
                pass

            print(f"🛑 Tutorial Driver.js fechado. {('Motivo: ' + motivo) if motivo else ''}")
            return True

        return False
    except Exception as e:
        print(f"ℹ️ Erro ao fechar tutorial Driver.js: {e}")
        return False

# ===================== BLOQUEIOS ÚNICOS ===================== #
async def verificar_bloqueios_unico(page):
    global bloqueios_removidos
    if bloqueios_removidos:
        return

    print("🛡️ Verificando bloqueios (Primeira vez na Pellegrino)...")
    await asyncio.sleep(2.5)

    await fechar_driver_tutorial(page, motivo="primeira verificação")
    await fechar_modais_bootstrap(page, motivo="primeira verificação")

    bloqueios_removidos = True

# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        await fechar_modais_bootstrap(page, "antes da busca")

        selector_busca = "#search-prod"
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)

        campo = page.locator(selector_busca)
        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")

        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)

        print(f"⌛ Pesquisando {codigo}...")
        await fechar_modais_bootstrap(page, "antes do ENTER")
        await page.keyboard.press("Enter")

        await verificar_bloqueios_unico(page)

        await asyncio.sleep(1.0)
        await fechar_driver_tutorial(page, motivo="pós-pesquisa")
        await fechar_modais_bootstrap(page, motivo="pós-pesquisa")

        try:
            await page.wait_for_selector("table tbody tr.odd, table tbody tr.even", timeout=8000)
        except:
            pass

    except Exception as e:
        print(f"❌ Erro na busca: {e}")

# ===================== EXTRAÇÃO ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    await fechar_modais_bootstrap(page, "antes da extração")

    linha_selector = "table tbody tr.odd, table tbody tr.even"

    if await page.locator(linha_selector).count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado (Tabela vazia).")
        return None

    tr = page.locator(linha_selector).first

    try:
        nome = (await tr.locator("span.font-weight-bold").inner_text()).strip()
        marca = (await tr.locator("span.text-truncate").inner_text()).strip()

        preco_raw = (await tr.locator("span.catalogo-preco").inner_text()).strip()
        preco_num = clean_price(preco_raw)

        return {
            "codigo": codigo_solicitado,
            "nome": nome,
            "marca": marca,
            "preco": preco_raw,
            "preco_num": preco_num,
            "preco_formatado": format_brl(preco_num),
            "qtdSolicitada": quantidade_solicitada,
            "qtdDisponivel": 1 if preco_num > 0 else 0,
            "podeComprar": preco_num > 0,
            "status": "Disponível" if preco_num > 0 else "Indisponível"
        }

    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Pellegrino",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial14(login_data_ou_page, lista_produtos):
    global bloqueios_removidos
    bloqueios_removidos = False

    itens_extraidos = []
    page = resolver_page(login_data_ou_page)

    if not page or not hasattr(page, "goto"):
        print("❌ Erro: Objeto 'page' inválido recebido.")
        return []

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Pellegrino -> Buscando: {codigo}")

        try:
            await buscar_produto(page, codigo)
            await fechar_driver_tutorial(page, motivo="antes da extração")
            await fechar_modais_bootstrap(page, motivo="antes da extração")

            resultado = await extrair_dados_produto(page, codigo, qtd)
            if resultado:
                itens_extraidos.append(resultado)

            await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ Erro crítico no loop F14: {e}")
            await safe_reload(page, motivo="erro no loop F14")

    if itens_extraidos and salvar_lote_sqlite:
        validos = [r for r in itens_extraidos if r]
        if validos:
            print(f"⏳ Salvando {len(validos)} itens Sky no banco...")
            salvar_lote_sqlite(preparar_dados_finais(validos))

    return itens_extraidos
