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
    Remove QUALQUER modal/overlay Bootstrap que intercepte cliques.
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
        await asyncio.sleep(0.2)
    except:
        pass

# ===================== LOADING (INTERMITENTE) ===================== #
async def wait_loading_sumir(page, timeout=60000):
    """
    Espera o #loading SUMIR se ele existir.
    Se não existir, segue SEM erro.
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
    except:
        # ⚠️ NUNCA propaga exceção
        print("ℹ️ Loader não apareceu ou já sumiu.")
        return True

async def ensure_ready(page, timeout=60000, tentar_recuperar=True):
    ok = await wait_loading_sumir(page, timeout)
    if ok:
        return True

    if tentar_recuperar:
        print("⚠️ Loader pode ter travado. Recarregando página...")
        try:
            await page.reload(wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
        except:
            pass
        return await wait_loading_sumir(page, timeout)

    return False

async def verificar_e_recuperar_loading(page):
    """
    Recuperação defensiva caso loader fique preso.
    """
    try:
        loading = page.locator("#loading")
        if await loading.count() > 0 and await loading.is_visible():
            print("⚠️ Loader travado detectado. Recuperando...")
            await page.reload(wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
            await wait_loading_sumir(page, timeout=60000)
            print("🔄 Página recuperada.")
            return True
    except:
        pass
    return False

# ===================== HELPERS COM CALMA ===================== #
async def click_com_calma(locator, pre=0.4, post=0.6, force=True):
    try:
        await ensure_ready(locator.page, timeout=60000, tentar_recuperar=True)
        await fechar_modais_bootstrap(locator.page, "antes do clique")
        await asyncio.sleep(pre)
        await locator.scroll_into_view_if_needed()
        await locator.click(force=force)
        await asyncio.sleep(post)
    except:
        pass

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
        if "/Movimentacao" in (page.url or ""):
            return

        base_url = page.url.split(".br")[0] + ".br" if ".br" in page.url else "http://novo.plsweb.com.br"
        target_url = base_url + "/Movimentacao"

        print(f"🚀 Navegando para: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await ensure_ready(page, timeout=90000, tentar_recuperar=True)
    except:
        print("⚠️ Não foi possível navegar para Movimentação.")

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
        await page.wait_for_selector("#codPeca", timeout=15000)
    except:
        print("⚠️ Falha ao ativar aba Produtos.")

# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        await navegar_para_pedido(page)

        if await verificar_e_recuperar_loading(page):
            await navegar_para_pedido(page)

        print("⏳ Aguardando carregamento inicial (10s)...")
        await asyncio.sleep(10)

        await ativar_aba_produtos(page)

        print(f"⌨️ Buscando código: {codigo}")
        await limpar_e_digitar_com_calma(page, "#codPeca", codigo)

        await fechar_modais_bootstrap(page, "antes do ENTER")
        await page.keyboard.press("Enter")

        print("⏳ Processando busca...")
        await ensure_ready(page, timeout=90000, tentar_recuperar=True)

        try:
            await page.wait_for_selector("tr.jqgrow", timeout=6000)
        except:
            pass

    except:
        print(f"⚠️ Falha na busca do produto {codigo}.")

# ===================== EXTRAÇÃO ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade=1):
    await ensure_ready(page, timeout=60000, tentar_recuperar=True)
    await fechar_modais_bootstrap(page, "antes da extração")

    linhas = page.locator("tr.jqgrow")
    if await linhas.count() == 0:
        print(f"ℹ️ Produto {codigo_solicitado} não encontrado.")
        return None

    tr = linhas.first

    try:
        cols = tr.locator("td")
        codigo = (await cols.nth(0).inner_text()).strip()
        nome = (await cols.nth(2).inner_text()).strip()
        marca = (await cols.nth(3).inner_text()).strip()

        estoque_raw = (await cols.nth(7).inner_text()).strip()
        qtd_disp = clean_stock(estoque_raw)

        preco_raw = (await cols.nth(9).inner_text()).strip()
        preco_num = clean_price(preco_raw)

        pode_comprar = qtd_disp >= quantidade and preco_num > 0
        valor_total = preco_num * quantidade

        return {
            "codigo": codigo,
            "nome": nome,
            "marca": marca,
            "preco": preco_raw,
            "preco_num": preco_num,
            "preco_formatado": format_brl(preco_num),
            "valor_total": valor_total,
            "valor_total_formatado": format_brl(valor_total),
            "qtdSolicitada": quantidade,
            "qtdDisponivel": qtd_disp,
            "podeComprar": pode_comprar,
            "status": "Disponível" if pode_comprar else "Indisponível",
            "regioes": []
        }

    except:
        print(f"⚠️ Falha ao extrair dados de {codigo_solicitado}.")
        return None

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Odapel",
        "total_itens": len(itens),
        "itens": itens
    }

# ===================== LOOP PRINCIPAL ===================== #
async def processar_lista_produtos_sequencial17(login_data_ou_page, lista_produtos):
    page = login_data_ou_page[2] if isinstance(login_data_ou_page, (tuple, list)) else login_data_ou_page
    if not page:
        print("❌ Page inválida.")
        return []

    itens = []

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] PLS/Odapel -> {codigo}")

        while True:
            try:
                await ensure_ready(page, timeout=90000, tentar_recuperar=True)

                if await verificar_e_recuperar_loading(page):
                    continue

                await buscar_produto(page, codigo)

                await ensure_ready(page, timeout=90000, tentar_recuperar=True)

                resultado = await extrair_dados_produto(page, codigo, qtd)
                if resultado:
                    itens.append(resultado)

                await asyncio.sleep(1)
                break

            except:
                print(f"⚠️ Produto {codigo} ignorado por instabilidade.")
                if await verificar_e_recuperar_loading(page):
                    continue
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=60000)
                except:
                    pass
                break

    if itens and salvar_lote_sqlite:
        print(f"⏳ Salvando {len(itens)} itens Odapel...")
        salvar_lote_sqlite(preparar_dados_finais(itens))

    return itens
