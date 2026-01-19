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
    """
    Clique com pequenas esperas para evitar race condition/UI lenta.
    """
    try:
        await asyncio.sleep(pre)
        await locator.scroll_into_view_if_needed()
    except Exception:
        pass

    await asyncio.sleep(pre)
    await locator.click(force=force)
    await asyncio.sleep(post)

# ===================== TUTORIAL DRIVER.JS (COM CALMA + REUTILIZÁVEL) ===================== #
async def fechar_tutorial_driver(page, motivo=""):
    """
    Fecha qualquer pop-up do Driver.js (tutorial) caso esteja aberto.
    - Espera um tempo antes de clicar (com calma)
    - Tenta mais de uma vez
    Retorna True se encontrou e fechou, False caso não exista.
    """
    btn_fechar = page.locator(".driver-popover-close-btn").first

    # tenta poucas vezes, pois às vezes o tutorial aparece "um pouco depois"
    for tentativa in range(1, 4):
        try:
            # espera curta para detectar sem travar a execução
            await btn_fechar.wait_for(state="visible", timeout=900)
        except Exception:
            return False

        try:
            if await btn_fechar.count() > 0 and await btn_fechar.is_visible():
                if motivo:
                    print(f"🛡️ Tutorial detectado ({motivo}) | tentativa {tentativa}/3. Fechando...")

                # tempo “humano” antes de clicar
                await asyncio.sleep(1.9)
                await btn_fechar.hover()
                await asyncio.sleep(0.2)
                await click_com_calma(btn_fechar, pre=0.2, post=0.8, force=True)

                # aguarda sumir
                try:
                    await btn_fechar.wait_for(state="hidden", timeout=4000)
                except Exception:
                    pass

                print("✅ Tutorial fechado.")
                return True

        except Exception:
            # fallback: click via JS
            try:
                await asyncio.sleep(1.2)
                await page.evaluate(
                    """() => {
                        const btn = document.querySelector('.driver-popover-close-btn');
                        if (btn) btn.click();
                    }"""
                )
                await asyncio.sleep(0.8)
                print("✅ Tutorial fechado (fallback JS).")
                return True
            except Exception:
                pass

    return False

# ===================== FUNÇÃO “APENAS UMA VEZ” (COM CALMA) ===================== #
async def verificar_bloqueios_unico(page):
    """
    Tenta fechar o tutorial Driver.js APENAS UMA VEZ por sessão.
    Agora:
    - espera mais (com calma)
    - faz verificação e clique “humano”
    """
    global bloqueios_removidos

    if bloqueios_removidos:
        return

    print("🛡️ Verificando bloqueios (Primeira vez)...")
    try:
        # dá tempo real para o tutorial aparecer após login / primeira interação
        await asyncio.sleep(3.0)

        fechou = await fechar_tutorial_driver(page, motivo="primeira vez")
        if not fechou:
            print("👍 Nenhum tutorial apareceu.")

        bloqueios_removidos = True

    except Exception as e:
        print(f"ℹ️ Erro ao tentar fechar bloqueio: {e}")
        bloqueios_removidos = True

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def buscar_produto(page, codigo):
    """
    Digita o código no campo #search-prod e trata pop-ups/tutoriais
    - fecha tutorial no pós-login (primeira vez)
    - fecha tutorial que possa aparecer após pesquisar também
    """
    try:
        selector_busca = "#search-prod"

        # Garante que o campo está na tela
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)

        # antes de mexer, tenta fechar tutorial se ele estiver por cima
        await fechar_tutorial_driver(page, motivo="antes de buscar")

        campo = page.locator(selector_busca).first

        # clique com calma
        await click_com_calma(campo, pre=0.25, post=0.25, force=True)

        await asyncio.sleep(0.2)
        await page.keyboard.press("Control+A")
        await asyncio.sleep(0.15)
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.25)

        # digita “com calma”
        await campo.type(str(codigo), delay=70)
        await asyncio.sleep(0.5)

        print(f"⌛ Pesquisando {codigo}...")
        await asyncio.sleep(0.35)
        await page.keyboard.press("Enter")

        # --- AÇÃO: FECHAR O POP-UP (SÓ NA PRIMEIRA VEZ) ---
        await verificar_bloqueios_unico(page)
        # --------------------------------------------------

        # e também: se aparecer depois da busca, fecha de novo (com calma)
        await asyncio.sleep(1.2)
        await fechar_tutorial_driver(page, motivo="após buscar")

        # Espera a tabela carregar (odd/even)
        try:
            await page.wait_for_selector("table tbody tr.odd, table tbody tr.even", timeout=8000)
        except Exception:
            pass

        await asyncio.sleep(0.8)

    except Exception as e:
        print(f"❌ Erro na busca: {e}")

# ===================== EXTRAÇÃO DOS DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    # Se tiver odd ou even, pega o primeiro
    linha_selector = "table tbody tr.odd, table tbody tr.even"

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
        # se tutorial aparecer em cima da tabela, fecha
        await fechar_tutorial_driver(page, motivo="antes de extrair")

        # Nome
        nome_element = tr.locator("span.font-weight-bold.font-size-h6-sm")
        nome_text = (await nome_element.inner_text()).strip()

        # Marca
        marca_element = tr.locator("span.nowrap.text-truncate.font-weight-light")
        marca_text = (await marca_element.inner_text()).strip()

        # Código
        cod_element = tr.locator("span.procedencia")
        if await cod_element.count() > 0:
            codigo_fab = (await cod_element.inner_text()).strip()
        else:
            codigo_fab = codigo_solicitado

        # Imagem
        img_element = tr.locator("div.symbol-label img")
        link_img = await img_element.get_attribute("src")
        if link_img and not link_img.startswith("http"):
            link_img = "https://compreonline.lagunaautopecas.com.br" + link_img

        # Preço
        preco_element = tr.locator("span.catalogo-preco")
        preco_raw = (await preco_element.inner_text()).strip()
        preco_num = clean_price(preco_raw)

        # Estoque/Disponibilidade
        input_qtd = tr.locator("input.vit-qtde-table")
        tem_estoque = await input_qtd.count() > 0 and preco_num > 0
        qtd_disponivel = 1.0 if tem_estoque else 0.0

    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

    # --- CONSOLIDAÇÃO ---
    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque

    regiao_sc = {
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
        "uf": "SC",
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar,
        "mensagem": regiao_sc["mensagem"],
        "disponivel": tem_estoque,
        "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_sc]
    }

    print(f"✅ SUCESSO: {codigo_fab} | {format_brl(preco_num)} | {marca_text}")
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
async def processar_lista_produtos_sequencial6(page, lista_produtos):
    # Reinicia a variável global para cada nova execução do processo
    global bloqueios_removidos
    bloqueios_removidos = False

    itens_extraidos = []

    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste padrão.")
        lista_produtos = [{"codigo": "9430084214", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    # tenta fechar tutorial logo no início (pós-login), com calma
    try:
        await asyncio.sleep(2.0)
        await verificar_bloqueios_unico(page)
    except Exception:
        pass

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Laguna -> Buscando: {codigo}")

        try:
            await buscar_produto(page, codigo)

            # se tutorial aparecer após a busca e antes de extrair, fecha
            await asyncio.sleep(0.6)
            await fechar_tutorial_driver(page, motivo="pré-extração")

            resultado = await extrair_dados_produto(page, codigo, qtd)

            if resultado:
                itens_extraidos.append(resultado)

            await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ Erro crítico no loop F6: {e}")
            await page.reload(wait_until="networkidle")

    # SALVAMENTO
    if itens_extraidos:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]

        if validos:
            if salvar_lote_sqlite:
                print(f"⏳ Salvando {len(validos)} itens no banco...")
                if salvar_lote_sqlite(preparar_dados_finais(validos)):
                    print("✅ Banco atualizado!")
                else:
                    print("❌ Erro ao salvar no banco.")
            else:
                print("ℹ️ Banco não configurado.")
        else:
            print("⚠️ Nada encontrado para salvar.")

    return itens_extraidos
