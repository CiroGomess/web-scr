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

# ===================== FUNÇÃO DE LIMPEZA ÚNICA (TUTORIAL) ===================== #
async def verificar_bloqueios_unico(page):
    """
    Tenta fechar o tutorial Driver.js APENAS UMA VEZ por sessão.
    """
    global bloqueios_removidos

    if not bloqueios_removidos:
        print("🛡️ Verificando bloqueios (Primeira vez na SAMA)...")
        try:
            btn_fechar = page.locator(".driver-popover-close-btn")

            if await btn_fechar.is_visible(timeout=3000):
                print("🛑 Pop-up detectado! Clicando no X...")
                await btn_fechar.click()
                await asyncio.sleep(1)
                print("✅ Pop-up fechado.")
            else:
                print("👍 Nenhum pop-up apareceu.")

            bloqueios_removidos = True

        except Exception as e:
            print(f"ℹ️ Erro ao tentar fechar bloqueio: {e}")

# ===================== TRATAMENTO LOADING (TRAVAMENTO) ===================== #
async def verificar_e_recuperar_loading(page) -> bool:
    """
    Verifica se a tela de loading está travada.
    Se estiver visível: Dá refresh na página e aguarda.
    """
    try:
        is_loading = await page.locator(".blockUI, .loading-mask").is_visible(timeout=1000)

        if is_loading:
            print("⚠️ TELA DE LOADING TRAVADA DETECTADA! Iniciando recuperação...")

            await page.reload()
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass

            print("🔄 Página atualizada. Retomando fluxo...")

            # Reseta bloqueio pois a página recarregou
            global bloqueios_removidos
            bloqueios_removidos = False

            return True
    except Exception:
        pass

    return False

# ===================== PRONTIDÃO DA TELA (ANTI TIMEOUT) ===================== #
async def garantir_pronto_para_buscar_sama(page) -> bool:
    """
    Garante que a tela está pronta:
    - DOM carregado
    - loading não está travado
    - tutorial/overlay fechado ANTES da busca
    - campo de busca existe no DOM e é interagível (com fallback de seletores)
    Retorna True quando estiver pronto; False se precisa tentar novamente.
    """
    # 1) estado mínimo de DOM
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except:
        pass

    # 2) recupera loading travado
    if await verificar_e_recuperar_loading(page):
        return False

    # 3) fecha tutorial/overlay antes de procurar input
    await verificar_bloqueios_unico(page)

    # 4) tenta aguardar loading sumir (melhor do que depender do input "visible")
    try:
        await page.locator(".blockUI, .loading-mask").wait_for(state="hidden", timeout=8000)
    except:
        # se ainda estiver carregando, tenta recuperar
        if await verificar_e_recuperar_loading(page):
            return False

    # 5) procura campo por seletores candidatos (caso o id mude ou o input não esteja "visible")
    selector_candidates = [
        "#search-prod",
        "input#search-prod",
        "input[name='search-prod']",
        "input[placeholder*='Buscar']",
        "input[type='search']",
    ]

    for sel in selector_candidates:
        loc = page.locator(sel).first
        try:
            if await loc.count() > 0:
                # tenta trazer para a viewport
                try:
                    await loc.scroll_into_view_if_needed(timeout=2000)
                except:
                    pass

                # tenta foco (se falhar, ainda pode funcionar via fill)
                try:
                    await loc.click(timeout=2000, force=True)
                except:
                    pass

                return True
        except:
            continue

    print("⚠️ Campo de busca não encontrado na SAMA (possível rota errada, sessão caiu ou layout mudou).")
    return False

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def buscar_produto(page, codigo):
    """
    Busca resiliente na SAMA:
    - prepara a tela (fecha overlay, garante loading ok)
    - evita depender de state=visible
    - faz retries curtos controlados
    """
    try:
        for tentativa in range(1, 4):
            pronto = await garantir_pronto_para_buscar_sama(page)
            if not pronto:
                print(f"🔄 Tentativa {tentativa}/3: página ainda não está pronta. Repetindo...")
                await asyncio.sleep(1)
                continue

            # Prioriza o seletor oficial
            campo = page.locator("#search-prod").first

            # fallback caso id mude
            if await campo.count() == 0:
                for sel in ["input[placeholder*='Buscar']", "input[type='search']"]:
                    alt = page.locator(sel).first
                    if await alt.count() > 0:
                        campo = alt
                        break

            # limpa e digita
            try:
                await campo.click(force=True)
            except:
                pass

            await asyncio.sleep(0.2)

            # tenta limpar via teclado
            try:
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
            except:
                # fallback: limpar via fill
                try:
                    await campo.fill("")
                except:
                    pass

            print(f"⌨️ Digitando: {codigo}")
            await campo.fill(str(codigo))
            await asyncio.sleep(0.3)

            print("🚀 Enter para pesquisar...")
            await page.keyboard.press("Enter")

            # após enter, pode aparecer loading/tutorial novamente (garante)
            await verificar_bloqueios_unico(page)

            print("⏳ Aguardando resultados...")

            # Espera resultado ou detecta travamento de loading
            try:
                task_table = asyncio.create_task(
                    page.wait_for_selector("table tbody tr.odd, table tbody tr.even", timeout=9000)
                )
                task_loading = asyncio.create_task(
                    page.wait_for_selector(".blockUI, .loading-mask", state="visible", timeout=2000)
                )

                done, pending = await asyncio.wait(
                    {task_table, task_loading},
                    return_when=asyncio.FIRST_COMPLETED
                )

                for t in pending:
                    t.cancel()

                # consome possíveis exceções de timeout para não sujar o log
                for t in done:
                    try:
                        t.result()
                    except Exception:
                        pass

            except:
                pass

            # se travou loading, recupera e repete
            if await verificar_e_recuperar_loading(page):
                print("🔄 Loading travou após Enter. Recuperado, repetindo busca...")
                continue

            return

        print("❌ Erro na busca SAMA: não foi possível preparar a tela/campo após 3 tentativas.")

    except Exception as e:
        print(f"❌ Erro na busca SAMA: {e}")

# ===================== EXTRAÇÃO DOS DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):

    linha_selector = "table tbody tr.odd, table tbody tr.even"

    if await page.locator(linha_selector).count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado (Tabela vazia).")
        return {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "RJ",
            "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }

    tr = page.locator(linha_selector).first

    try:
        # Nome
        try:
            nome_element = tr.locator("span.font-weight-bold.font-size-h6-sm")
            nome_text = (await nome_element.inner_text()).strip()
        except:
            nome_text = "N/A"

        # Marca
        try:
            marca_element = tr.locator("span.nowrap.text-truncate.font-weight-light")
            marca_text = (await marca_element.inner_text()).strip()
        except:
            marca_text = "N/A"

        # Código
        codigo_fab = codigo_solicitado
        try:
            cod_element = tr.locator("span.procedencia")
            if await cod_element.count() > 0:
                codigo_fab = (await cod_element.inner_text()).strip()
        except:
            pass

        # Imagem
        link_img = None
        try:
            img_element = tr.locator("div.symbol-label img")
            link_img_attr = await img_element.get_attribute("src")
            if link_img_attr:
                if not link_img_attr.startswith("http"):
                    link_img = "https://compreonline.samaautopecas.com.br" + link_img_attr
                else:
                    link_img = link_img_attr
        except:
            pass

        # Preço
        try:
            preco_element = tr.locator("span.catalogo-preco")
            preco_raw = (await preco_element.inner_text()).strip()
            preco_num = clean_price(preco_raw)
        except:
            preco_raw = "0,00"
            preco_num = 0.0

        # Disponibilidade
        input_qtd = tr.locator("input.vit-qtde-table")
        tem_estoque = await input_qtd.count() > 0 and preco_num > 0
        qtd_disponivel = 100.0 if tem_estoque else 0.0

    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque

    regiao_mg = {
        "uf": "RJ", "preco": preco_raw, "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num), "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel, "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total), "podeComprar": pode_comprar,
        "mensagem": None if pode_comprar else "Indisponível", "disponivel": tem_estoque
    }

    item_formatado = {
        "codigo": codigo_fab, "nome": nome_text, "marca": marca_text, "imagem": link_img,
        "preco": preco_raw, "preco_num": preco_num, "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total, "valor_total_formatado": format_brl(valor_total),
        "uf": "RJ", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar, "mensagem": regiao_mg["mensagem"],
        "disponivel": tem_estoque, "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_mg]
    }

    print(f"✅ SUCESSO SAMA: {codigo_fab} | {format_brl(preco_num)} | {marca_text}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "SAMA",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial8(login_data_ou_page, lista_produtos):
    global bloqueios_removidos
    bloqueios_removidos = False

    itens_extraidos = []

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
        print("⚠️ Lista vazia. Usando teste: CT488")
        lista_produtos = [{"codigo": "CT488", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    # (Opcional, mas recomendado) garantir rota inicial do catálogo, se você tiver a URL correta:
    # try:
    #     await page.goto("https://compreonline.samaautopecas.com.br/catalogo", wait_until="domcontentloaded")
    # except:
    #     pass

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] SAMA -> Buscando: {codigo}")

        while True:
            try:
                if await verificar_e_recuperar_loading(page):
                    continue

                await buscar_produto(page, codigo)

                if await verificar_e_recuperar_loading(page):
                    continue

                resultado = await extrair_dados_produto(page, codigo, qtd)

                if resultado:
                    itens_extraidos.append(resultado)

                await asyncio.sleep(1)
                break

            except Exception as e:
                print(f"❌ Erro crítico no loop F8: {e}")

                if await verificar_e_recuperar_loading(page):
                    continue

                try:
                    await page.reload(wait_until="networkidle")
                except:
                    pass
                bloqueios_removidos = False
                break

    if itens_extraidos and salvar_lote_sqlite:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]

        if validos:
            print(f"⏳ Salvando {len(validos)} itens SAMA no banco...")
            if salvar_lote_sqlite(preparar_dados_finais(validos)):
                print("✅ Banco atualizado!")
            else:
                print("❌ Erro ao salvar no banco.")

    return itens_extraidos
