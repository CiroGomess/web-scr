# produtoController6.py (Laguna) - versão ajustada:
# - Evita timeout no #search-prod
# - Se aparecer "Nenhum registro mostrado", pula imediatamente para o próximo produto
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
    except Exception:
        return 0.0

def format_brl(valor):
    if valor is None or valor == 0:
        return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ===================== HELPERS “COM CALMA” ===================== #
async def click_com_calma(locator, pre=0.5, post=0.8, force=True):
    try:
        await asyncio.sleep(pre)
        await locator.scroll_into_view_if_needed()
    except Exception:
        pass
    await asyncio.sleep(pre)
    await locator.click(force=force)
    await asyncio.sleep(post)

# ===================== TUTORIAL DRIVER.JS ===================== #
async def fechar_tutorial_driver(page, motivo=""):
    """
    Fecha qualquer pop-up do Driver.js (tutorial) caso esteja aberto.
    """
    btn_fechar = page.locator(".driver-popover-close-btn").first

    for tentativa in range(1, 3):
        try:
            if await btn_fechar.is_visible(timeout=1000):
                if motivo:
                    print(f"🛡️ Tutorial detectado ({motivo}). Fechando...")

                await asyncio.sleep(0.5)
                await btn_fechar.click(force=True)

                try:
                    await btn_fechar.wait_for(state="hidden", timeout=2000)
                except:
                    pass

                print("✅ Tutorial fechado.")
                return True
        except Exception:
            pass

    return False

# ===================== FUNÇÃO “APENAS UMA VEZ” ===================== #
async def verificar_bloqueios_unico(page):
    global bloqueios_removidos

    if bloqueios_removidos:
        return

    print("🛡️ Verificando bloqueios (Primeira vez)...")
    try:
        await asyncio.sleep(2.0)
        fechou = await fechar_tutorial_driver(page, motivo="primeira vez")
        if not fechou:
            print("👍 Nenhum tutorial apareceu.")
        bloqueios_removidos = True
    except Exception as e:
        print(f"ℹ️ Erro ao tentar fechar bloqueio: {e}")
        bloqueios_removidos = True

# ===================== TRATAMENTO LOADING (TRAVAMENTO) ===================== #
async def verificar_e_recuperar_loading(page) -> bool:
    """
    Verifica se a tela de loading está travada.
    """
    try:
        is_loading = await page.locator("#loading, .blockUI, .loading-mask").is_visible(timeout=1000)

        if is_loading:
            print("⚠️ TELA DE LOADING TRAVADA DETECTADA! Iniciando recuperação...")

            await page.reload()
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass

            print("🔄 Página atualizada. Retomando fluxo...")

            global bloqueios_removidos
            bloqueios_removidos = False

            return True
    except Exception:
        pass

    return False

# ===================== CHECK "NENHUM REGISTRO" ===================== #
async def tem_msg_nenhum_registro(page) -> bool:
    """
    Retorna True se a Laguna mostrar a mensagem:
    'Nenhum registro mostrado'
    """
    try:
        info = page.locator("#table-produtos-CatalogoNovo_info").first
        if await info.count() == 0:
            return False

        # lê o texto (se não estiver visível, o inner_text pode falhar)
        try:
            txt = (await info.inner_text()).strip().lower()
        except:
            try:
                txt = (await info.text_content() or "").strip().lower()
            except:
                return False

        return "nenhum registro" in txt or "nenhum registro mostrado" in txt
    except Exception:
        return False

# ===================== PRONTIDÃO DA TELA (ANTI TIMEOUT) ===================== #
async def garantir_pronto_para_buscar_laguna(page) -> bool:
    """
    Garante que a tela está pronta:
    - DOM carregado
    - loading não está travado
    - tutorial fechado ANTES de interagir
    - campo de busca existe no DOM (com fallback de seletores)
    """
    # 1) DOM mínimo
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except:
        pass

    # 2) recupera loading travado
    if await verificar_e_recuperar_loading(page):
        return False

    # 3) fecha tutorial antes do input
    await fechar_tutorial_driver(page, motivo="pré-busca")
    await verificar_bloqueios_unico(page)

    # 4) aguarda loading sumir
    try:
        await page.locator("#loading, .blockUI, .loading-mask").wait_for(state="hidden", timeout=8000)
    except:
        if await verificar_e_recuperar_loading(page):
            return False

    # 5) valida campo de busca com fallback
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
                try:
                    await loc.scroll_into_view_if_needed(timeout=2000)
                except:
                    pass
                try:
                    await loc.click(timeout=2000, force=True)
                except:
                    pass
                return True
        except:
            continue

    print("⚠️ Campo de busca não encontrado na Laguna (rota errada, sessão caiu ou layout mudou).")
    return False

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def buscar_produto(page, codigo):
    """
    Retorna True se achou resultado.
    Retorna False se:
      - timeout/sem resultado
      - aparecer "Nenhum registro mostrado" (pula pro próximo)
    """
    try:
        for tentativa in range(1, 4):
            pronto = await garantir_pronto_para_buscar_laguna(page)
            if not pronto:
                print(f"🔄 Tentativa {tentativa}/3: tela ainda não pronta. Repetindo...")
                await asyncio.sleep(1)
                continue

            # pega campo principal, fallback se necessário
            campo = page.locator("#search-prod").first
            if await campo.count() == 0:
                for sel in ["input[placeholder*='Buscar']", "input[type='search']"]:
                    alt = page.locator(sel).first
                    if await alt.count() > 0:
                        campo = alt
                        break

            await fechar_tutorial_driver(page, motivo="antes de buscar")

            await click_com_calma(campo, pre=0.25, post=0.25, force=True)

            await asyncio.sleep(0.2)

            # limpa
            try:
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
            except:
                try:
                    await campo.fill("")
                except:
                    pass

            # digita
            await campo.type(str(codigo), delay=70)
            await asyncio.sleep(0.4)

            print(f"⌛ Pesquisando {codigo}...")
            await page.keyboard.press("Enter")

            # pós-enter: tutorial pode reaparecer
            await verificar_bloqueios_unico(page)
            await fechar_tutorial_driver(page, motivo="após Enter")

            # Espera rápida: ou veio linha de resultado, ou já aparece "nenhum registro"
            print("⏳ Aguardando resultados...")

            try:
                task_table = asyncio.create_task(
                    page.wait_for_selector("table tbody tr.odd, table tbody tr.even", timeout=7000)
                )
                task_info = asyncio.create_task(
                    page.wait_for_selector("#table-produtos-CatalogoNovo_info", timeout=3000)
                )
                task_loading = asyncio.create_task(
                    page.wait_for_selector("#loading, .blockUI, .loading-mask", state="visible", timeout=2000)
                )

                done, pending = await asyncio.wait(
                    {task_table, task_info, task_loading},
                    return_when=asyncio.FIRST_COMPLETED
                )

                for t in pending:
                    t.cancel()

                # consome exceções para não sujar log
                for t in done:
                    try:
                        t.result()
                    except Exception:
                        pass

            except:
                pass

            # Se apareceu "nenhum registro", pula imediatamente
            if await tem_msg_nenhum_registro(page):
                print(f"⛔ {codigo}: Nenhum registro mostrado. Pulando...")
                return False

            # Se loading travou, recupera e tenta novamente
            if await verificar_e_recuperar_loading(page):
                print("🔄 Loading travou após Enter. Recuperado, repetindo busca...")
                continue

            # Se veio linha, sucesso
            if await page.locator("table tbody tr.odd, table tbody tr.even").count() > 0:
                await asyncio.sleep(0.6)
                return True

            # Nada encontrado dentro do tempo
            print(f"⚠️ Timeout/sem resultado para {codigo}.")
            return False

        print("❌ Busca Laguna falhou: não foi possível preparar tela/campo após 3 tentativas.")
        return False

    except Exception as e:
        print(f"❌ Erro na busca Laguna: {e}")
        return False

# ===================== EXTRAÇÃO DOS DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    linha_selector = "table tbody tr.odd, table tbody tr.even"

    # Primeiro: se a própria tela já está dizendo "nenhum registro", retorna não encontrado
    if await tem_msg_nenhum_registro(page):
        print(f"❌ {codigo_solicitado} não encontrado (Nenhum registro mostrado).")
        return {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "RJ", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }

    if await page.locator(linha_selector).count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado (Tabela vazia).")
        return {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "RJ", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }

    tr = page.locator(linha_selector).first

    try:
        await fechar_tutorial_driver(page, motivo="antes de extrair")

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
                    link_img = "https://compreonline.lagunaautopecas.com.br" + link_img_attr
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

        # Estoque
        input_qtd = tr.locator("input.vit-qtde-table")
        tem_estoque = await input_qtd.count() > 0 and preco_num > 0
        qtd_disponivel = 1.0 if tem_estoque else 0.0

    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque

    regiao_sc = {
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
        "uf": "SC", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar, "mensagem": regiao_sc["mensagem"],
        "disponivel": tem_estoque, "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_sc]
    }

    print(f"✅ SUCESSO LAGUNA: {codigo_fab} | {format_brl(preco_num)} | {marca_text}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Laguna",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial6(login_data_ou_page, lista_produtos):
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
        print("⚠️ Lista vazia. Usando teste: 9430084214")
        lista_produtos = [{"codigo": "9430084214", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    # tenta fechar tutorial inicial
    try:
        await asyncio.sleep(2.0)
        await verificar_bloqueios_unico(page)
    except:
        pass

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Laguna -> Buscando: {codigo}")

        while True:
            try:
                if await verificar_e_recuperar_loading(page):
                    continue

                encontrou = await buscar_produto(page, codigo)

                # Se não encontrou OU deu "nenhum registro", vai para o próximo item do FOR
                if not encontrou:
                    print("⏩ Pulando item...")
                    break

                if await verificar_e_recuperar_loading(page):
                    continue

                resultado = await extrair_dados_produto(page, codigo, qtd)

                if resultado:
                    itens_extraidos.append(resultado)

                await asyncio.sleep(1)
                break

            except Exception as e:
                print(f"❌ Erro crítico no loop F6: {e}")
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
            print(f"⏳ Salvando {len(validos)} itens no banco...")
            if salvar_lote_sqlite(preparar_dados_finais(validos)):
                print("✅ Banco atualizado!")
            else:
                print("❌ Erro ao salvar no banco.")

    return itens_extraidos
