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

def normalize_space(s):
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()

def absolutizar_url_img(src):
    if not src:
        return None
    src = str(src).strip()

    # Se já é absoluta
    if src.startswith("http://") or src.startswith("https://"):
        return src

    # Se for relativa, usa o domínio base do sistema
    if src.startswith("/"):
        return "https://ecommerce.gb.com.br" + src

    return "https://ecommerce.gb.com.br/" + src.lstrip("/")

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def garantir_tela_produtos(page):
    """Garante que está na tela de produtos (#/unit004)"""
    if not page:
        return

    if "unit004" in page.url:
        return

    print("📂 Navegando para o menu 'Produtos'...")
    try:
        menu_produtos = page.locator('a[href="#/unit004"]')
        if await menu_produtos.is_visible():
            await menu_produtos.click(force=True)
        else:
            print("⚠️ Menu não visível, forçando URL...")
            await page.goto("https://ecommerce.gb.com.br/#/unit004", wait_until="networkidle")

        await asyncio.sleep(2)

    except Exception as e:
        print(f"⚠️ Erro navegação: {e}")
        await page.goto("https://ecommerce.gb.com.br/#/unit004", wait_until="networkidle")

async def voltar_para_lista(page):
    """
    Clica no botão 'voltar' do sistema para retornar à tela/listagem,
    garantindo que o campo de busca reapareça para a próxima pesquisa.
    """
    try:
        btn = page.locator("#btn-voltar")

        if await btn.count() > 0 and await btn.is_visible():
            await btn.click(force=True)
            await asyncio.sleep(1)
        else:
            try:
                await page.go_back(wait_until="networkidle")
            except:
                pass

        await garantir_tela_produtos(page)
        await page.wait_for_selector("#txt-search-simples", state="attached", timeout=15000)

    except Exception as e:
        print(f"⚠️ Falha ao voltar para a lista: {e}")
        try:
            await page.goto("https://ecommerce.gb.com.br/#/unit004", wait_until="networkidle")
            await asyncio.sleep(2)
        except:
            pass

async def buscar_produto(page, codigo):
    """
    Busca por código no campo #txt-search-simples.
    Depois da busca, o sistema pode:
    - abrir direto o detalhe, ou
    - mostrar lista (tr.destacavel) para clicar.
    """
    try:
        await garantir_tela_produtos(page)

        selector_busca = "#txt-search-simples"

        print(f"🔎 Localizando campo de busca: {selector_busca}")
        await page.wait_for_selector(selector_busca, state="attached", timeout=20000)

        try:
            await page.click("label[for='txt-search-simples']", force=True, timeout=2000)
        except:
            await page.locator(selector_busca).click(force=True)

        await asyncio.sleep(0.2)

        print(f"⌨️ Inserindo código: {codigo}")

        try:
            await page.fill(selector_busca, str(codigo))
        except:
            await page.evaluate(
                """
                (codigo) => {
                    var input = document.getElementById('txt-search-simples');
                    if (!input) return;
                    input.value = codigo;
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                    input.dispatchEvent(new Event('change', {bubbles: true}));
                }
                """,
                str(codigo),
            )

        await asyncio.sleep(0.2)

        print("🚀 Pressionando ENTER...")
        await page.keyboard.press("Enter")

        try:
            await page.click("i.material-icons.prefix:has-text('search')", timeout=1000, force=True)
        except:
            pass

        print("⏳ Aguardando resultado (lista ou detalhe)...")
        try:
            await page.wait_for_selector(
                "div.col.s12.m6.mb-1 h5, tr.destacavel, .alert-warning, .card-panel.red",
                timeout=15000
            )
        except:
            pass

        await asyncio.sleep(0.6)

    except Exception as e:
        print(f"❌ Erro na rotina de busca: {e}")

# ===================== SELECIONA PRIMEIRO RESULTADO APENAS SE HOUVER > 1 ===================== #
async def selecionar_primeiro_resultado_se_precisar(page):
    """
    Regra:
    - Se houver 0 linhas: retorna "none"
    - Se houver 1 linha: não clica (fluxo normal) e retorna "single"
    - Se houver >1: clica na primeira e retorna "multi_clicked"
    """
    selector_linha = "tr.destacavel"
    linhas = page.locator(selector_linha)
    qtd = await linhas.count()

    if qtd == 0:
        return "none"

    if qtd == 1:
        return "single"

    print(f"ℹ️ {qtd} resultados encontrados. Clicando no primeiro da lista...")
    primeira = linhas.first

    try:
        await primeira.scroll_into_view_if_needed()
    except:
        pass

    await asyncio.sleep(0.2)
    await primeira.click(force=True)

    try:
        await page.wait_for_selector("div.col.s12.m6.mb-1 h5", timeout=15000)
    except:
        pass

    await asyncio.sleep(0.6)
    return "multi_clicked"

# ===================== EXTRAÇÃO: DETALHES DO PRODUTO (PAINEL) ===================== #
async def _get_detail_value(page, label_text):
    label_text = normalize_space(label_text)

    row = page.locator(
        f"tbody tr.row:has(div.col.s4 b:has-text('{label_text}'))"
    ).first

    if await row.count() == 0:
        return None

    val = row.locator("div.col.s8").first
    try:
        return normalize_space(await val.inner_text())
    except:
        return None

async def _get_imagem_produto(page):
    """
    Pega a imagem do bloco:
    <div class="col s12 white z-depth-1 pa-0"> <img src="webapi/item/.../fotoHigh" ...>
    """
    try:
        img = page.locator("div.col.s12.white.z-depth-1.pa-0 img").first
        if await img.count() == 0:
            # fallback mais tolerante caso as classes mudem
            img = page.locator("img[src*='webapi/item/'][src*='fotoHigh']").first

        if await img.count() == 0:
            return None

        src = await img.get_attribute("src")
        return absolutizar_url_img(src)
    except:
        return None

async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    try:
        await page.wait_for_selector("div.col.s12.m6.mb-1 h5", timeout=15000)
    except:
        print(f"❌ {codigo_solicitado} não encontrado (painel de detalhes não carregou).")
        return {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "RJ", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }

    # NOME
    try:
        nome_text = normalize_space(await page.locator("div.col.s12.m6.mb-1 h5").first.inner_text())
    except:
        nome_text = None

    # IMAGEM
    imagem_url = await _get_imagem_produto(page)

    # PREÇO (VALOR FINAL)
    preco_raw = "0,00"
    try:
        preco_node = page.locator(
            "div.col.s12.m6.mb-1 table tbody tr:has(td:has-text('Valor Final (com impostos)')) td.right-align h5"
        ).first
        if await preco_node.count() > 0:
            preco_raw = normalize_space(await preco_node.inner_text())
        else:
            fallback = page.locator("div.col.s12.m6.mb-1 table tbody td.right-align h5").last
            if await fallback.count() > 0:
                preco_raw = normalize_space(await fallback.inner_text())
    except:
        pass

    preco_num = clean_price(preco_raw)

    # CAMPOS DO DETALHE
    codigo_gb = await _get_detail_value(page, "Código GB:") or codigo_solicitado
    marca_text = await _get_detail_value(page, "Marca:") or "N/A"
    ncm_text = await _get_detail_value(page, "Ncm:") or None

    tem_estoque = preco_num > 0
    qtd_disponivel = 1.0 if tem_estoque else 0.0

    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque

    regiao_rj = {
        "uf": "RJ",
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "podeComprar": pode_comprar,
        "mensagem": None if pode_comprar else "Indisponível",
        "disponivel": tem_estoque
    }

    item_formatado = {
        "codigo": codigo_gb,
        "nome": nome_text,
        "marca": marca_text,
        "ncm": ncm_text,
        "imagem": imagem_url,
        "preco": preco_raw,
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

    print(f"✅ SUCESSO: {codigo_gb} | {format_brl(preco_num)} | {marca_text}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "G&B",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial4(login_data_ou_page, lista_produtos):
    itens_extraidos = []

    if isinstance(login_data_ou_page, (tuple, list)) and len(login_data_ou_page) >= 3:
        page = login_data_ou_page[2]
    else:
        page = login_data_ou_page

    if not page:
        print("❌ Erro: page inválida (não veio do login).")
        return []

    if not lista_produtos:
        lista_produtos = [{"codigo": "73512", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]
    elif isinstance(lista_produtos, list) and len(lista_produtos) > 0 and isinstance(lista_produtos[0], str):
        lista_produtos = [{"codigo": c, "quantidade": 1} for c in lista_produtos]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] GB -> Buscando: {codigo}")

        try:
            await buscar_produto(page, codigo)

            # ✅ Só clica se houver MAIS DE UM resultado
            await selecionar_primeiro_resultado_se_precisar(page)

            # ✅ Extrai do painel de detalhes (incluindo imagem)
            resultado = await extrair_dados_produto(page, codigo, qtd)

            if resultado:
                itens_extraidos.append(resultado)

        except Exception as e:
            print(f"❌ Erro crítico no loop F4: {e}")
            try:
                await page.reload(wait_until="networkidle")
            except:
                pass

        finally:
            await voltar_para_lista(page)
            await asyncio.sleep(0.4)

    if itens_extraidos:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]

        if validos:
            if salvar_lote_postgres:
                print(f"⏳ Salvando {len(validos)} itens no banco...")
                if salvar_lote_postgres(preparar_dados_finais(validos)):
                    print("✅ Banco atualizado com sucesso!")
                else:
                    print("❌ Erro ao salvar no banco.")
            else:
                print("ℹ️ Banco não configurado.")
        else:
            print("⚠️ Nenhum produto válido encontrado. Nada será salvo.")

    return itens_extraidos
