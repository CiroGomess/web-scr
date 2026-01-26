# produtoController16.py

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

# ===================== HELPERS DE LOADING/ESPERA ===================== #
async def aguardar_loader_sumir(page, selector=".loading-mask", timeout_visible=800, timeout_hidden=15000):
    """
    Tenta detectar o loader; se aparecer, aguarda sumir.
    Se não aparecer dentro de timeout_visible, segue sem erro.
    """
    try:
        await page.wait_for_selector(selector, state="visible", timeout=timeout_visible)
        await page.wait_for_selector(selector, state="hidden", timeout=timeout_hidden)
    except:
        pass

async def verificar_e_recuperar_loading(page) -> bool:
    """
    Verifica se a tela de loading está travada ou se a página quebrou.
    Se necessário: Dá refresh na página e aguarda o sistema voltar.
    """
    try:
        # Evite usar um locator com múltiplos seletores e chamar is_visible com timeout
        # em sequência. Aqui tentamos de forma simples e tolerante.
        selectors = ["#loading", ".loading-mask", ".block-ui-overlay"]

        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    # is_visible não aceita timeout em algumas versões; então faça wait curto
                    try:
                        visible = await loc.is_visible()
                    except:
                        visible = False

                    if visible:
                        print("⚠️ TELA DE LOADING TRAVADA DETECTADA! Iniciando recuperação...")
                        await page.reload()

                        try:
                            await page.wait_for_load_state("networkidle", timeout=10000)
                        except:
                            pass

                        print("⏳ Aguardando 5s para o sistema voltar...")
                        await asyncio.sleep(5)

                        print("🔄 Página atualizada. Retomando fluxo...")
                        return True
            except:
                pass

    except:
        pass

    return False


async def fechar_tutorial_se_houver(page):
    try:
        await fechar_tutorial_se_houver(page)
        # Seletor do "overlay" ou botão de fechar do tutorial (Driver.js)
        # Tenta clicar no botão de "Pular" ou "Done" se existir, ou clica no overlay
        if await page.locator(".driver-overlay, .driver-close-btn").is_visible(timeout=2000):
            print("🛡️ Tutorial detectado. Tentando fechar...")
            # Tenta disparar um Escape ou clicar no botão de fechar
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
            
            # Se ainda estiver lá, força clique no overlay
            if await page.locator(".driver-overlay").is_visible():
                await page.click(".driver-overlay", position={"x": 10, "y": 10}, force=True)
                print("🛡️ Clique forçado no overlay do tutorial.")
    except:
        pass

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def buscar_produto(page, codigo):
    """
    Busca um produto no Furacão:
    - limpa o campo
    - digita o código
    - Enter
    - aguarda loader (se houver) e/ou resultado
    """
    try:
        selector_busca = "input#gsearch"

        # Campo de busca
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
        campo = page.locator(selector_busca).first

        # Clica e limpa
        await campo.click(force=True)
        await asyncio.sleep(0.3)
        await page.keyboard.press("Control+A")
        await asyncio.sleep(0.1)
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.2)

        # Digita e pesquisa
        print(f"⌨️ Digitando: {codigo}")
        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)

        print("🚀 Enter para pesquisar...")
        await page.keyboard.press("Enter")

        print("⏳ Aguardando resultados...")

        # --------- CORREÇÃO CRÍTICA (sem "Task exception was never retrieved") ---------
        # Faz a corrida: ou aparece resultado, ou aparece loading.
        # E sempre "coleta" exceptions das tasks (gather return_exceptions=True).
        task_result = asyncio.create_task(
            page.wait_for_selector("tr[ng-controller='RowCtrl']", state="visible", timeout=10000)
        )
        task_loading = asyncio.create_task(
            page.wait_for_selector(".loading-mask", state="visible", timeout=2000)
        )

        try:
            done, pending = await asyncio.wait(
                {task_result, task_loading},
                return_when=asyncio.FIRST_COMPLETED
            )

            # cancela o restante
            for t in pending:
                t.cancel()

            # IMPORTANTÍSSIMO: aguarda todas para consumir exceptions/cancelamentos
            await asyncio.gather(*done, *pending, return_exceptions=True)

        except:
            # Mesmo se der erro aqui, consome tasks para não vazar exception
            try:
                task_result.cancel()
                task_loading.cancel()
                await asyncio.gather(task_result, task_loading, return_exceptions=True)
            except:
                pass
        # ---------------------------------------------------------------------------

        # Se o loading apareceu, aguarda sumir (se já sumiu, passa)
        await aguardar_loader_sumir(page, selector=".loading-mask", timeout_visible=300, timeout_hidden=15000)

        # Pequena folga
        await asyncio.sleep(1.5)

    except Exception as e:
        print(f"❌ Erro na busca Furação: {e}")
        # Não lança erro aqui para permitir que o loop principal trate com reload

# ===================== EXTRAÇÃO DOS DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    card_selector = "tr[ng-controller='RowCtrl']"

    if await page.locator(card_selector).count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado.")
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
        # Nome / Descrição
        nome_element = card.locator("div.descricao span.ng-binding").last
        nome_text = (await nome_element.inner_text()).strip()

        # Código (se houver)
        try:
            cod_el = card.locator("span.ng-binding").first
            codigo_fab = (await cod_el.inner_text()).strip()
        except:
            codigo_fab = codigo_solicitado

        # Marca
        marca_text = "N/A"
        try:
            marca_el = card.locator("strong:has-text('Marca:') + span")
            if await marca_el.count() > 0:
                marca_text = (await marca_el.inner_text()).strip()
        except:
            pass

        # Imagem
        try:
            img_element = card.locator("div.img img").first
            link_img = await img_element.get_attribute("src")
            if link_img and not link_img.startswith("http"):
                link_img = "https://vendas.furacao.com.br" + link_img
        except:
            link_img = None

        # Preço
        try:
            preco_element = card.locator("span.h3.ng-binding").last
            preco_raw = (await preco_element.inner_text()).strip()
        except:
            preco_raw = "0,00"

        preco_num = clean_price(preco_raw)

        # Estoque
        qtd_disponivel = 0.0
        try:
            estoque_el = card.locator("span:has-text('Estoque:')")
            if await estoque_el.count() > 0:
                texto_estoque = await estoque_el.inner_text()
                qtd_disponivel = clean_stock(texto_estoque)
        except:
            pass

        tem_estoque = qtd_disponivel > 0 and preco_num > 0

    except Exception as e:
        print(f"⚠ Erro na extração do card: {e}")
        return None

    # Consolidação
    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque and (qtd_disponivel >= quantidade_solicitada)

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
        "mensagem": None if pode_comprar else "Estoque insuficiente",
        "disponivel": tem_estoque
    }

    item_formatado = {
        "codigo": codigo_fab,
        "nome": nome_text,
        "marca": marca_text,
        "imagem": link_img,
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

    print(f"✅ SUCESSO FURAÇÃO: {codigo_fab} | {format_brl(preco_num)} | Marca: {marca_text}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Furacão",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial16(login_data_ou_page, lista_produtos):
    itens_extraidos = []

    # Extração correta do objeto 'page' da tupla de login
    if isinstance(login_data_ou_page, (tuple, list)):
        if len(login_data_ou_page) >= 3:
            page = login_data_ou_page[2]
        else:
            page = login_data_ou_page[-1]
    else:
        page = login_data_ou_page

    # Validação
    if not page or not hasattr(page, "goto"):
        print("❌ Erro: Objeto 'page' inválido recebido.")
        return []

    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste: IWP065")
        lista_produtos = [{"codigo": "IWP065", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Furação -> Buscando: {codigo}")

        # Loop de retry para o MESMO produto
        while True:
            try:
                # 1) Verifica se já travou antes de começar
                if await verificar_e_recuperar_loading(page):
                    continue

                await buscar_produto(page, codigo)

                # 2) Verifica se travou durante a busca
                if await verificar_e_recuperar_loading(page):
                    continue

                resultado = await extrair_dados_produto(page, codigo, qtd)
                if resultado:
                    itens_extraidos.append(resultado)

                await asyncio.sleep(1.5)

                # Se chegou aqui, concluiu este item
                break

            except Exception as e:
                print(f"❌ Erro crítico no loop F16: {e}")

                # tenta recuperar se for loading
                if await verificar_e_recuperar_loading(page):
                    continue

                # Se for outro erro, dá reload e aborta esse item (não travar o robô inteiro)
                try:
                    await page.reload(wait_until="networkidle")
                except:
                    pass
                break

    # Salvamento
    if itens_extraidos and salvar_lote_sqlite:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]

        if validos:
            print(f"⏳ Salvando {len(validos)} itens no banco...")
            if salvar_lote_sqlite(preparar_dados_finais(validos)):
                print("✅ Banco atualizado!")
            else:
                print("❌ Erro ao salvar no banco.")

    return itens_extraidos
