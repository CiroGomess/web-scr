import asyncio



# ============================================================
# 🔧 Converte "R$ 1.234,50" → 1234.50
# ============================================================
def clean_price(preco_str):
    if not preco_str:
        return None
    preco = preco_str.replace("R$", "").strip()
    preco = preco.replace(".", "")
    preco = preco.replace(",", ".")
    try:
        return float(preco)
    except:
        return None


# ============================================================
# 🔧 Formata 1234.5 → "R$ 1.234,50"
# ============================================================
def format_brl(valor):
    if valor is None:
        return None
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ============================================================
# 🔍 BUSCAR PRODUTO
# ============================================================
async def buscar_produto(page, codigo, quantidade=1):

    print(f"\n🔎 Buscando código: {codigo} — Quantidade desejada: {quantidade}")

    await page.wait_for_selector("input[name='src'][formcontrolname='search']:visible", timeout=20000)

    campo_busca = page.locator("input[name='src'][formcontrolname='search']:visible")
    await campo_busca.fill("")
    await campo_busca.fill(str(codigo))

    await asyncio.sleep(0.7)

    btn = page.locator("button.btn-search:visible")
    await btn.click()

    print("➡ Pesquisa enviada. Aguardando resultados...")
    await page.wait_for_load_state("networkidle")
    print("✔ Página carregada:", page.url)


# ============================================================
# 📦 EXTRAIR DADOS DO PRODUTO
# ============================================================
async def extrair_dados_produto(page, quantidade=1):

    print("\n📦 Extraindo dados do produto...")

    # =======================================================
    # 1) Sem resultado
    # =======================================================
    no_result = page.locator("h3:has-text('Não encontramos nenhum resultado')")
    if await no_result.count() > 0:
        print("❌ Produto não encontrado!")

        dados = {
            "codigo": None,
            "nome": None,
            "marca": None,
            "imagem": None,

            "preco": None,
            "preco_num": None,
            "preco_formatado": None,

            "valor_total": None,
            "valor_total_formatado": None,

            "uf": None,
            "disponivel": False,
            "status": "Não encontrado",

            "qtdSolicitada": quantidade,
            "qtdDisponivel": 0,
            "podeComprar": False,
            "mensagem": "Nenhum resultado encontrado",
            "regioes": None
        }
        
        return dados

    # =======================================================
    # 2) Encontrar o card
    # =======================================================
    card_locator = page.locator("isthmus-produto-b2b-card")

    try:
        await card_locator.first.wait_for(timeout=15000)
    except:
        print("❌ Nenhum card carregou.")
        dados = {
            "codigo": None,
            "nome": None,
            "marca": None,
            "imagem": None,
            "preco": None,
            "preco_num": None,
            "preco_formatado": None,
            "valor_total": None,
            "valor_total_formatado": None,
            "uf": None,
            "disponivel": False,
            "status": "Erro",
            "qtdSolicitada": quantidade,
            "qtdDisponivel": 0,
            "podeComprar": False,
            "mensagem": "Nenhum card encontrado",
            "regioes": None
        }
        
        return dados

    card = card_locator.first

    # =======================================================
    # 3) Esperar spinner sumir
    # =======================================================
    spinner = card.locator("mat-spinner")
    if await spinner.count() > 0:
        print("⏳ Aguardando preço carregar…")
        try:
            await spinner.wait_for(state="detached", timeout=10000)
        except:
            print("⚠ Spinner não sumiu — possivelmente indisponível.")

    # =======================================================
    # 4) Campos básicos
    # =======================================================
    nome = (await card.locator(".card-nome").inner_text()).strip()

    marca_el = card.locator(".nome-marca")
    marca = (await marca_el.inner_text()).strip() if await marca_el.count() else ""

    imagem = await card.locator(".card-imagem img").get_attribute("src")

    titulo = await card.locator(".card-imagem a").get_attribute("title")
    codigo = titulo.split("(Cód.:")[-1].replace(")", "").strip() if "(Cód.:" in titulo else None

    # =======================================================
    # 5) MULTI-UF
    # =======================================================
    regioes_info = []
    lista_precos_li = card.locator(".card-preco ul.precos li")
    total_li = await lista_precos_li.count()

    qtd_input = card.locator("input[aria-label='Quantidade do produto']")
    botao_plus = card.locator("button[aria-label='Aumentar quantidade do produto']")
    alerta = page.locator("div.alert.alert-success")

    # -------------------------------------------------------
    # SE EXISTEM MÚLTIPLAS UFs
    # -------------------------------------------------------
    if total_li > 0:

        for idx in range(total_li):

            li = lista_precos_li.nth(idx)

            # Seleciona UF
            await li.click()
            await asyncio.sleep(0.3)

            # Identifica UF
            uf_txt = None
            uf_span = li.locator("span.text-muted.small")
            if await uf_span.count() > 0:
                uf_txt = (await uf_span.inner_text()).strip().upper()

            # Identifica preço desta UF
            strong_el = li.locator("strong")
            tem_preco_uf = await strong_el.count() > 0
            preco_uf = (await strong_el.inner_text()).strip() if tem_preco_uf else None

            # Se não houver preço → indisponível
            if not tem_preco_uf or not preco_uf:
                regioes_info.append({
                    "uf": uf_txt,
                    "preco": None,
                    "preco_num": None,
                    "preco_formatado": None,
                    "qtdSolicitada": quantidade,
                    "qtdDisponivel": 0,
                    "valor_total": None,
                    "valor_total_formatado": None,
                    "podeComprar": False,
                    "mensagem": "Indisponível",
                    "disponivel": False
                })
                continue

            # ----------------------------------------------
            # RESET QUANTIDADE SEMPRE QUE TROCAR DE UF
            # ----------------------------------------------
            try:
                await qtd_input.fill("1")
                await asyncio.sleep(0.2)
            except:
                pass

            # limpar alertas antigos
            try:
                await page.evaluate("""
                    document.querySelectorAll('div.alert.alert-success')
                    .forEach(el => el.remove());
                """)
            except:
                pass

            qtd_disponivel_reg = 1
            mensagem_reg = None
            pode_comprar_reg = True

            # ----------------------------------------------
            # Clicar até atingir quantidade solicitada OU alerta
            # ----------------------------------------------
            for i in range(quantidade - 1):

                await botao_plus.click()
                await asyncio.sleep(0.25)

                # ALERTA → estoque insuficiente
                if await alerta.count() > 0:
                    texto_alerta = (await alerta.inner_text()).strip()
                    num = "".join(c for c in texto_alerta if c.isdigit())

                    qtd_disponivel_reg = int(num) if num else qtd_disponivel_reg
                    mensagem_reg = texto_alerta
                    pode_comprar_reg = False
                    break

                # quantidade aumentou normalmente
                qtd_disponivel_reg = i + 2  # pois inicia em 1

            valor_unitario_reg = clean_price(preco_uf)
            valor_total_reg = (
                valor_unitario_reg * qtd_disponivel_reg if valor_unitario_reg else None
            )

            regioes_info.append({
                "uf": uf_txt,
                "preco": preco_uf,
                "preco_num": valor_unitario_reg,
                "preco_formatado": format_brl(valor_unitario_reg),
                "qtdSolicitada": quantidade,
                "qtdDisponivel": qtd_disponivel_reg,
                "valor_total": valor_total_reg,
                "valor_total_formatado": format_brl(valor_total_reg),
                "podeComprar": pode_comprar_reg,
                "mensagem": mensagem_reg,
                "disponivel": bool(valor_unitario_reg)
            })

        # ---------------------------------------------------
        # Consolidar com base na 1ª UF
        # ---------------------------------------------------
        primeira = regioes_info[0]

        dados = {
            "codigo": codigo,
            "nome": nome,
            "marca": marca,
            "imagem": imagem,

            "preco": primeira["preco"],
            "preco_num": primeira["preco_num"],
            "preco_formatado": primeira["preco_formatado"],

            "valor_total": primeira["valor_total"],
            "valor_total_formatado": primeira["valor_total_formatado"],

            "uf": primeira["uf"],
            "qtdSolicitada": quantidade,
            "qtdDisponivel": primeira["qtdDisponivel"],
            "podeComprar": primeira["podeComprar"],
            "mensagem": primeira["mensagem"],

            "disponivel": any(r["disponivel"] for r in regioes_info),
            "status": "Disponível" if any(r["disponivel"] for r in regioes_info) else "Indisponível",

            "regioes": regioes_info
        }

        
        return dados

    # =======================================================
    # 6) Fallback sem multi-UF (como antes)
    # =======================================================
    preco_el = card.locator(".card-preco strong")
    tem_preco = await preco_el.count() > 0
    preco = (await preco_el.inner_text()).strip() if tem_preco else None

    spans = card.locator("span.text-muted.small")
    df_uf = None
    indisponivel = not tem_preco

    for i in range(await spans.count()):
        txt = (await spans.nth(i).inner_text()).strip().lower()
        if "indisponível" in txt:
            indisponivel = True
        else:
            df_uf = txt.upper()

    qtd_disponivel = 1
    mensagem = None
    pode_comprar = True

    if not indisponivel:
        for i in range(quantidade - 1):
            await botao_plus.click()
            await asyncio.sleep(0.2)

            if await alerta.count() > 0:
                texto = (await alerta.inner_text()).strip()
                num = "".join(c for c in texto if c.isdigit())
                qtd_disponivel = int(num) if num else 1
                mensagem = texto
                pode_comprar = False
                break
            qtd_disponivel = i + 2
    else:
        qtd_disponivel = 0
        pode_comprar = False
        mensagem = "Produto indisponível"

    valor_unitario = clean_price(preco)
    valor_total = valor_unitario * qtd_disponivel if valor_unitario else None

    dados = {
        "codigo": codigo,
        "nome": nome,
        "marca": marca,
        "imagem": imagem,

        "preco": preco,
        "preco_num": valor_unitario,
        "preco_formatado": format_brl(valor_unitario),

        # "valor_total": valor_total,
        # "valor_total_formatado": format_brl(valor_total),

        
        "disponivel": not indisponivel,
        "status": "Disponível" if not indisponivel else "Indisponível",

        "qtdSolicitada": quantidade,
        "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar,
        "mensagem": mensagem,

        "regioes": None
    }

   
    return dados


# ============================================================
# 🔁 PROCESSAR LISTA DE PRODUTOS (SEQUENCIAL)
# ============================================================
async def processar_lista_produtos(page, lista_produtos):

    resultados = []

    for item in lista_produtos:
        codigo = item["codigo"]
        quantidade = item["quantidade"]

        print("\n======================================")
        print(f"▶ PROCESSANDO {codigo} (qtd: {quantidade})")
        print("======================================\n")

        await buscar_produto(page, codigo, quantidade)
        dados = await extrair_dados_produto(page, quantidade)

        resultados.append(dados)
        await asyncio.sleep(1)

    return resultados


# ============================================================
# 🔥 MULTI-ABAS / BATCH PARALELO
# ============================================================
async def processar_batch(context, batch):

    tarefas = []

    for item in batch:
        codigo = item["codigo"]
        qtd = item["quantidade"]

        async def processar_item(codigo=codigo, qtd=qtd):

            page = await context.new_page()

            try:
                await page.goto(
                    "https://www.portalcomdip.com.br/comdip/compras/pesquisa",
                    wait_until="networkidle",
                    timeout=30000
                )

                await buscar_produto(page, codigo, qtd)
                dados = await extrair_dados_produto(page, qtd)

            except Exception as e:
                dados = {"codigo": codigo, "erro": str(e)}

            finally:
                await page.close()

            return dados

        tarefas.append(processar_item())

    return await asyncio.gather(*tarefas)


# ============================================================
# 🔁 PROCESSAR BATCHES DE 5 EM 5
# ============================================================
async def processar_lista_produtos_parallel(context, lista_produtos, batch_size=5):

    resultados_finais = []

    for i in range(0, len(lista_produtos), batch_size):

        batch = lista_produtos[i:i + batch_size]

        print("\n======================================")
        print(f"▶ PROCESSANDO LOTE {i//batch_size + 1} ({len(batch)} itens)")
        print("======================================\n")

        resultados = await processar_batch(context, batch)
        resultados_finais.extend(resultados)

    return resultados_finais
