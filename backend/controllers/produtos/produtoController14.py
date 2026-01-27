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

# ===================== PAGE RESOLVER (ACEITA TUPLA OU PAGE) ===================== #
def resolver_page(login_data_ou_page):
    """
    Aceita:
      - page
      - tuple/list (browser, context, page)
    Retorna a page correta ou None.
    """
    if isinstance(login_data_ou_page, (tuple, list)):
        if len(login_data_ou_page) >= 3:
            return login_data_ou_page[2]
        return login_data_ou_page[-1]
    return login_data_ou_page

async def safe_reload(page, motivo="", wait_until="domcontentloaded"):
    """Reload que não explode e dá logs."""
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

# ===================== TIMEOUT HELPER (PULAR EM 5s) ===================== #
async def extrair_com_timeout(coro, timeout_s=5):
    """
    Executa uma coroutine de extração (inner_text/get_attribute/etc) com timeout curto.
    Se passar do tempo, retorna "__TIMEOUT__" e o loop pula o produto.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_s)
    except asyncio.TimeoutError:
        return "__TIMEOUT__"

# ===================== FECHADOR ROBUSTO DO DRIVER.JS ===================== #
async def fechar_driver_tutorial(page, motivo=""):
    """
    Fecha o popover do Driver.js com calma (esperas) e valida que sumiu.
    Pode ser chamado quantas vezes quiser (idempotente).
    """
    try:
        btn_close = page.locator("button.driver-popover-close-btn")
        popover = page.locator(".driver-popover")

        # tenta algumas vezes porque o tutorial pode renderizar com atraso
        for tentativa in range(3):
            await asyncio.sleep(0.6)

            if await btn_close.count() == 0:
                return False

            try:
                await btn_close.first.wait_for(state="visible", timeout=2500)
            except:
                continue

            await asyncio.sleep(1.2)

            try:
                await btn_close.first.hover()
                await asyncio.sleep(0.2)
                await btn_close.first.click(force=True, timeout=3000)
            except:
                # fallback JS
                try:
                    await page.evaluate(
                        """() => {
                            const btn = document.querySelector('button.driver-popover-close-btn');
                            if (btn) btn.click();
                        }"""
                    )
                except:
                    pass

            # aguarda sumir
            try:
                await popover.first.wait_for(state="hidden", timeout=6000)
            except:
                try:
                    await btn_close.first.wait_for(state="hidden", timeout=4000)
                except:
                    pass

            print(f"🛑 Tutorial Driver.js fechado. {('Motivo: ' + motivo) if motivo else ''}")
            return True

        return False

    except Exception as e:
        print(f"ℹ️ Erro ao fechar tutorial Driver.js: {e}")
        return False

# ===================== FUNÇÃO DE LIMPEZA ÚNICA ===================== #
async def verificar_bloqueios_unico(page):
    """
    Tenta fechar o tutorial Driver.js APENAS UMA VEZ por sessão (na primeira busca).
    """
    global bloqueios_removidos

    if bloqueios_removidos:
        return

    print("🛡️ Verificando bloqueios (Primeira vez na Pellegrino)...")
    await asyncio.sleep(2.5)

    fechado = await fechar_driver_tutorial(page, motivo="primeira verificação")
    if not fechado:
        print("👍 Nenhum tutorial ativo (ou já fechado).")

    bloqueios_removidos = True

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def buscar_produto(page, codigo):
    """Digita o código no campo #search-prod"""
    try:
        selector_busca = "#search-prod"
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)

        campo = page.locator(selector_busca)
        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")

        await campo.fill(str(codigo))
        await asyncio.sleep(0.6)

        print(f"⌛ Pesquisando {codigo}...")
        await page.keyboard.press("Enter")

        # ✅ Fecha tutorial (primeira vez com mais paciência)
        await verificar_bloqueios_unico(page)

        # ✅ fecha novamente após a pesquisa (pode reaparecer)
        await asyncio.sleep(1.0)
        await fechar_driver_tutorial(page, motivo="pós-pesquisa")

        # Espera a tabela carregar (se vier resultado)
        try:
            await page.wait_for_selector("table tbody tr.odd, table tbody tr.even", timeout=8000)
        except:
            pass

    except Exception as e:
        print(f"❌ Erro na busca: {e}")

# ===================== EXTRAÇÃO DOS DADOS (TIMEOUT 5s -> PULA) ===================== #
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
        nome_element = tr.locator("span.font-weight-bold.font-size-h6-sm")
        nome_text = await extrair_com_timeout(nome_element.inner_text(), timeout_s=5)
        if nome_text == "__TIMEOUT__":
            print(f"⏭️ Timeout (5s) extraindo NOME. Pulando {codigo_solicitado}.")
            return None
        nome_text = nome_text.strip()

        # Marca (onde estava travando)
        marca_element = tr.locator("span.nowrap.text-truncate.font-weight-light")
        marca_text = await extrair_com_timeout(marca_element.inner_text(), timeout_s=5)
        if marca_text == "__TIMEOUT__":
            print(f"⏭️ Timeout (5s) extraindo MARCA. Pulando {codigo_solicitado}.")
            return None
        marca_text = marca_text.strip()

        # Código
        cod_element = tr.locator("span.procedencia")
        if await cod_element.count() > 0:
            codigo_fab = await extrair_com_timeout(cod_element.inner_text(), timeout_s=5)
            if codigo_fab == "__TIMEOUT__":
                print(f"⏭️ Timeout (5s) extraindo CÓDIGO. Pulando {codigo_solicitado}.")
                return None
            codigo_fab = codigo_fab.strip()
        else:
            codigo_fab = codigo_solicitado

        # Imagem
        img_element = tr.locator("div.symbol-label img")
        link_img = await extrair_com_timeout(img_element.get_attribute("src"), timeout_s=5)
        if link_img == "__TIMEOUT__":
            print(f"⏭️ Timeout (5s) extraindo IMAGEM. Pulando {codigo_solicitado}.")
            return None

        if link_img and not link_img.startswith("http"):
            link_img = "https://compreonline.pellegrino.com.br" + link_img

        # Preço
        preco_element = tr.locator("span.catalogo-preco")
        preco_raw = await extrair_com_timeout(preco_element.inner_text(), timeout_s=5)
        if preco_raw == "__TIMEOUT__":
            print(f"⏭️ Timeout (5s) extraindo PREÇO. Pulando {codigo_solicitado}.")
            return None
        preco_raw = preco_raw.strip()

        # Preço destaque (opcional)
        try:
            preco_destaque = tr.locator("span.catalogo-preco .text-green")
            if await preco_destaque.count() > 0:
                preco_raw2 = await extrair_com_timeout(preco_destaque.inner_text(), timeout_s=5)
                if preco_raw2 != "__TIMEOUT__" and preco_raw2:
                    preco_raw = preco_raw2.strip()
        except:
            pass

        preco_num = clean_price(preco_raw)

        # Estoque (na Pellegrino o input existe quando pode comprar)
        input_qtd = tr.locator("input.vit-qtde-table")
        tem_estoque = await input_qtd.count() > 0 and preco_num > 0
        qtd_disponivel = 1.0 if tem_estoque else 0.0

    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

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

    print(f"✅ SUCESSO SKY: {codigo_fab} | {format_brl(preco_num)} | {marca_text}")
    return item_formatado

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

    # ✅ aceita tupla (browser, context, page) OU page direto
    page = resolver_page(login_data_ou_page)

    if not page or not hasattr(page, "goto"):
        print("❌ Erro: Objeto 'page' inválido recebido (veio tupla errada ou None).")
        return []

    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste padrão.")
        lista_produtos = [{"codigo": "HG 33013", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Pellegrino -> Buscando: {codigo}")

        try:
            await buscar_produto(page, codigo)

            # redundância: se o tutorial aparecer durante o carregamento, fecha de novo
            await asyncio.sleep(0.8)
            await fechar_driver_tutorial(page, motivo="antes da extração")

            # ✅ extração com timeout 5s interno (se travar, retorna None e pula)
            resultado = await extrair_dados_produto(page, codigo, qtd)

            if resultado:
                itens_extraidos.append(resultado)

            await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ Erro crítico no loop F14: {e}")
            await safe_reload(page, motivo="erro no loop F14", wait_until="domcontentloaded")

    # SALVAMENTO
    if itens_extraidos:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]

        if validos:
            if salvar_lote_sqlite:
                print(f"⏳ Salvando {len(validos)} itens Sky no banco...")
                if salvar_lote_sqlite(preparar_dados_finais(validos)):
                    print("✅ Banco atualizado!")
                else:
                    print("❌ Erro ao salvar no banco.")
            else:
                print("ℹ️ Banco não configurado.")
        else:
            print("⚠️ Nada encontrado para salvar.")

    return itens_extraidos
