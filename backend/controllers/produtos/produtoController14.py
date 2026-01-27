# produtoController14.py

import asyncio
import re
from datetime import datetime

# ===================== CONTROLE GLOBAL ===================== #
bloqueios_removidos = False

# ===================== IMPORTAÇÃO DO SERVIÇO DE BANCO ===================== #
try:
    from services.db_saver import salvar_lote_sqlite
except ImportError:
    print("⚠️ Aviso: 'services.db_saver' não encontrado. O salvamento no banco será pulado.")
    salvar_lote_sqlite = None

# ===================== UTILITÁRIOS ===================== #
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

# ===================== PAGE RESOLVER ===================== #
def resolver_page(login_data_ou_page):
    if isinstance(login_data_ou_page, (tuple, list)):
        return login_data_ou_page[2] if len(login_data_ou_page) >= 3 else login_data_ou_page[-1]
    return login_data_ou_page

async def safe_reload(page, motivo=""):
    try:
        print(f"🔄 Reload seguro {motivo}")
        await page.reload(wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_load_state("domcontentloaded", timeout=20000)
    except:
        pass

# ===================== MODAL KILLER (BOOTSTRAP + CUPOM) ===================== #
async def fechar_modais_bootstrap(page, motivo=""):
    """
    Remove QUALQUER modal Bootstrap ou overlay que intercepte cliques.
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
        await asyncio.sleep(0.2)
    except:
        pass

# ===================== DRIVER.JS KILLER ===================== #
async def fechar_driver_tutorial(page, motivo=""):
    try:
        btn = page.locator("button.driver-popover-close-btn")
        popover = page.locator(".driver-popover")

        for _ in range(3):
            if await btn.count() == 0:
                return

            try:
                await btn.first.wait_for(state="visible", timeout=2000)
                await btn.first.click(force=True, timeout=2000)
            except:
                await page.evaluate("""
                    () => {
                        const b = document.querySelector('button.driver-popover-close-btn');
                        if (b) b.click();
                    }
                """)

            try:
                await popover.first.wait_for(state="hidden", timeout=4000)
            except:
                pass

            print(f"🛑 Driver.js fechado ({motivo})")
            return
    except:
        pass

# ===================== BLOQUEIOS ÚNICOS ===================== #
async def verificar_bloqueios_unico(page):
    global bloqueios_removidos
    if bloqueios_removidos:
        return

    print("🛡️ Limpando bloqueios iniciais (Pellegrino)...")
    await asyncio.sleep(2)

    await fechar_driver_tutorial(page, "primeira execução")
    await fechar_modais_bootstrap(page, "primeira execução")

    bloqueios_removidos = True

# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        await fechar_modais_bootstrap(page, "antes da busca")

        selector = "#search-prod"
        await page.wait_for_selector(selector, state="visible", timeout=20000)

        campo = page.locator(selector)
        await campo.click(force=True)
        await campo.fill("")
        await campo.fill(str(codigo))

        print(f"⌛ Buscando {codigo}...")
        await fechar_modais_bootstrap(page, "antes do ENTER")
        await page.keyboard.press("Enter")

        await verificar_bloqueios_unico(page)

        await asyncio.sleep(1)
        await fechar_driver_tutorial(page, "pós-busca")
        await fechar_modais_bootstrap(page, "pós-busca")

        try:
            await page.wait_for_selector(
                "table tbody tr.odd, table tbody tr.even",
                timeout=8000
            )
        except:
            pass

    except Exception:
        print(f"⚠️ Não foi possível buscar o produto {codigo}.")

# ===================== EXTRAÇÃO ===================== #
async def extrair_dados_produto(page, codigo, quantidade=1):
    await fechar_modais_bootstrap(page, "antes da extração")

    linhas = page.locator("table tbody tr.odd, table tbody tr.even")
    if await linhas.count() == 0:
        print(f"ℹ️ Produto {codigo} não encontrado.")
        return None

    tr = linhas.first

    try:
        nome = (await tr.locator("span.font-weight-bold").inner_text()).strip()
        marca = (await tr.locator("span.text-truncate").inner_text()).strip()
        preco_raw = (await tr.locator("span.catalogo-preco").inner_text()).strip()

        preco_num = clean_price(preco_raw)
        tem_estoque = preco_num > 0

        return {
            "codigo": codigo,
            "nome": nome,
            "marca": marca,
            "preco": preco_raw,
            "preco_num": preco_num,
            "preco_formatado": format_brl(preco_num),
            "qtdSolicitada": quantidade,
            "qtdDisponivel": 1 if tem_estoque else 0,
            "podeComprar": tem_estoque,
            "status": "Disponível" if tem_estoque else "Indisponível"
        }

    except:
        print(f"⚠️ Falha ao extrair dados de {codigo}.")
        return None

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Pellegrino",
        "total_itens": len(itens),
        "itens": itens
    }

# ===================== LOOP PRINCIPAL ===================== #
async def processar_lista_produtos_sequencial14(login_data_ou_page, lista_produtos):
    global bloqueios_removidos
    bloqueios_removidos = False

    page = resolver_page(login_data_ou_page)
    if not page:
        print("❌ Page inválida.")
        return []

    itens = []

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Pellegrino -> {codigo}")

        try:
            await buscar_produto(page, codigo)
            await fechar_driver_tutorial(page, "antes da extração")
            await fechar_modais_bootstrap(page, "antes da extração")

            resultado = await extrair_dados_produto(page, codigo, qtd)
            if resultado:
                itens.append(resultado)

            await asyncio.sleep(0.8)

        except:
            print(f"⚠️ Produto {codigo} ignorado por instabilidade.")
            await safe_reload(page, "recuperação")

    if itens and salvar_lote_sqlite:
        print(f"⏳ Salvando {len(itens)} itens Pellegrino...")
        salvar_lote_sqlite(preparar_dados_finais(itens))

    return itens
