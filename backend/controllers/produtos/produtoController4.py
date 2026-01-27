import asyncio
import re
from datetime import datetime

# ===================== IMPORTAÇÃO DO SERVIÇO DE BANCO ===================== #
try:
    from services.db_saver import salvar_lote_sqlite
except ImportError:
    print("⚠️ Aviso: 'services.db_saver' não encontrado. O salvamento no banco será pulado.")
    salvar_lote_sqlite = None

# ===================== HELPERS GERAIS ===================== #
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
    if not valor:
        return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def normalize_space(s):
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()

def absolutizar_url_img(src):
    if not src:
        return None
    src = src.strip()
    if src.startswith("http"):
        return src
    if src.startswith("/"):
        return "https://ecommerce.gb.com.br" + src
    return "https://ecommerce.gb.com.br/" + src.lstrip("/")

async def safe_wait_gb(page, timeout=3000):
    """
    G&B NÃO possui loader.
    Garante apenas estabilidade da UI.
    """
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)
    except:
        pass

# ===================== NAVEGAÇÃO ===================== #
async def garantir_tela_produtos(page):
    if not page:
        return

    if "unit004" in page.url:
        return

    print("📂 Navegando para Produtos (G&B)...")
    try:
        menu = page.locator('a[href="#/unit004"]')
        if await menu.is_visible(timeout=8000):
            await menu.click(force=True)
        else:
            await page.goto("https://ecommerce.gb.com.br/#/unit004", wait_until="domcontentloaded")

        await safe_wait_gb(page)

    except:
        await page.goto("https://ecommerce.gb.com.br/#/unit004", wait_until="domcontentloaded")
        await safe_wait_gb(page)

async def voltar_para_lista(page):
    try:
        btn = page.locator("#btn-voltar")
        if await btn.count() > 0 and await btn.is_visible():
            await asyncio.sleep(3)
            await btn.click(force=True)
        else:
            try:
                await page.go_back(wait_until="domcontentloaded")
            except:
                pass

        await safe_wait_gb(page)
        await garantir_tela_produtos(page)
        await page.wait_for_selector("#txt-search-simples", timeout=15000)

    except:
        try:
            await page.goto("https://ecommerce.gb.com.br/#/unit004", wait_until="domcontentloaded")
            await safe_wait_gb(page)
        except:
            pass

# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        await garantir_tela_produtos(page)

        selector = "#txt-search-simples"
        await page.wait_for_selector(selector, timeout=30000)

        await page.fill(selector, "")
        await page.fill(selector, str(codigo))
        await asyncio.sleep(0.3)

        await page.keyboard.press("Enter")
        await asyncio.sleep(0.4)

        success_selector = "div.col.s12.m6.mb-1 h5, tr.destacavel"
        error_selector = "#toast-container .toast:has-text('Total de 0 produtos')"

        found = await page.wait_for_selector(
            f"{success_selector}, {error_selector}",
            timeout=10000
        )

        texto = await found.inner_text()
        if "Total de 0 produtos" in texto:
            print(f"ℹ️ Produto {codigo} não encontrado.")
            return False

        return True

    except:
        print(f"⚠️ Falha ao buscar {codigo}.")
        return False

# ===================== SELEÇÃO ===================== #
async def selecionar_primeiro_resultado_se_precisar(page):
    linhas = page.locator("tr.destacavel")
    qtd = await linhas.count()

    if qtd <= 1:
        return

    try:
        await linhas.first.click(force=True)
        await page.wait_for_selector("div.col.s12.m6.mb-1 h5", timeout=15000)
    except:
        pass

# ===================== EXTRAÇÃO ===================== #
async def _get_detail_value(page, label):
    row = page.locator(f"tbody tr.row:has(div.col.s4 b:has-text('{label}'))").first
    if await row.count() == 0:
        return None
    try:
        return normalize_space(await row.locator("div.col.s8").inner_text())
    except:
        return None

async def _get_imagem_produto(page):
    try:
        img = page.locator("img[src*='fotoHigh']").first
        if await img.count() == 0:
            return None
        return absolutizar_url_img(await img.get_attribute("src"))
    except:
        return None

async def extrair_dados_produto(page, codigo, quantidade=1):
    try:
        await page.wait_for_selector("div.col.s12.m6.mb-1 h5", timeout=15000)
    except:
        print(f"⚠️ Detalhes não carregaram para {codigo}.")
        return None

    nome = normalize_space(await page.locator("div.col.s12.m6.mb-1 h5").inner_text())
    imagem = await _get_imagem_produto(page)

    preco_raw = "0,00"
    try:
        preco_node = page.locator("td:has-text('Valor Final')").locator("h5").first
        if await preco_node.count() > 0:
            preco_raw = normalize_space(await preco_node.inner_text())
    except:
        pass

    preco_num = clean_price(preco_raw)
    tem_estoque = preco_num > 0

    codigo_gb = await _get_detail_value(page, "Código GB:") or codigo
    marca = await _get_detail_value(page, "Marca:") or "N/A"
    ncm = await _get_detail_value(page, "Ncm:")

    valor_total = preco_num * quantidade

    return {
        "codigo": codigo_gb,
        "nome": nome,
        "marca": marca,
        "ncm": ncm,
        "imagem": imagem,
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "uf": "RJ",
        "qtdSolicitada": quantidade,
        "qtdDisponivel": 1 if tem_estoque else 0,
        "podeComprar": tem_estoque,
        "disponivel": tem_estoque,
        "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": []
    }

# ===================== DB ===================== #
def preparar_dados_finais(itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "G&B",
        "total_itens": len(itens),
        "itens": itens
    }

# ===================== LOOP PRINCIPAL ===================== #
async def processar_lista_produtos_sequencial4(login_data_ou_page, lista_produtos):
    page = login_data_ou_page[2] if isinstance(login_data_ou_page, (tuple, list)) else login_data_ou_page
    itens = []

    if not lista_produtos:
        return []

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] G&B -> {codigo}")

        try:
            if not await buscar_produto(page, codigo):
                continue

            await selecionar_primeiro_resultado_se_precisar(page)
            resultado = await extrair_dados_produto(page, codigo, qtd)

            if resultado:
                itens.append(resultado)

        except:
            print(f"⚠️ Produto {codigo} ignorado por instabilidade.")

        finally:
            await voltar_para_lista(page)
            await asyncio.sleep(0.5)

    if itens and salvar_lote_sqlite:
        salvar_lote_sqlite(preparar_dados_finais(itens))

    return itens
