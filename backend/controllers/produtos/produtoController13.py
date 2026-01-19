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
    except Exception:
        return 0.0


def format_brl(valor):
    if valor is None or valor == 0:
        return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def limpar_codigo(texto):
    if not texto:
        return ""
    return re.sub(r"[^a-zA-Z0-9]", "", str(texto)).upper()


def preparar_dados_finais(lista_itens):
    """
    Monta o dicionário mestre no padrão esperado pelo db_saver (chave 'fornecedror')
    """
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Sky Peças",  # <- IMPORTANTE: db_saver espera 'fornecedror'
        "total_itens": len(lista_itens),
        "itens": lista_itens,
    }


# ===================== NOVO: TRATAMENTO MODAL SWEETALERT2 ===================== #
# ===================== NOVO: TRATAMENTO MODAL SWEETALERT2 ===================== #
async def fechar_modal_sem_resultados(page) -> bool:
    """
    Fecha o modal SweetAlert2 quando a busca não retorna resultados.
    Agora com delay (1.9s) antes de clicar no OK, para evitar clique "instantâneo".
    Retorna True se encontrou e fechou o modal, False caso contrário.
    """
    popup = page.locator(".swal2-popup.swal2-modal")
    ok_btn = page.locator("button.swal2-confirm.swal2-styled")

    try:
        # Detecta o popup rapidamente
        await popup.wait_for(state="visible", timeout=600)
    except Exception:
        return False

    try:
        titulo = ""
        msg = ""

        try:
            titulo = (await page.locator("#swal2-title").inner_text()).strip()
        except Exception:
            pass

        try:
            msg = (await page.locator("#swal2-html-container").inner_text()).strip()
        except Exception:
            pass

        # ✅ Aguarda 1.9s antes de interagir (evita "instantâneo")
        await asyncio.sleep(1.9)

        # Garante que o botão ainda está lá e clicável
        try:
            await ok_btn.wait_for(state="visible", timeout=3000)
        except Exception:
            # se sumiu sozinho nesse meio tempo, considera fechado
            try:
                await popup.wait_for(state="hidden", timeout=1500)
                print(f"⚠️ Modal SweetAlert sumiu sozinho. Título: '{titulo}' | Msg: '{msg}'")
                return True
            except Exception:
                return True

        # ✅ Clique "humano": hover -> pequeno delay -> click
        try:
            await ok_btn.hover()
            await asyncio.sleep(0.2)
            await ok_btn.click(timeout=3000)
        except Exception:
            # fallback: força click via JS
            try:
                await page.evaluate(
                    """() => {
                        const btn = document.querySelector('button.swal2-confirm.swal2-styled');
                        if (btn) btn.click();
                    }"""
                )
            except Exception:
                pass

        # Espera o popup sumir
        try:
            await popup.wait_for(state="hidden", timeout=7000)
        except Exception:
            pass

        print(f"⚠️ Modal SweetAlert fechado. Título: '{titulo}' | Msg: '{msg}'")
        return True

    except Exception as e:
        print(f"⚠️ Erro ao tratar modal SweetAlert2: {e}")
        return True

# ===================== EXTRAÇÃO DE DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):

    cards = page.locator(".bx_produto")
    count_cards = await cards.count()

    if count_cards == 0:
        print(f"❌ {codigo_solicitado} não encontrado (Nenhum card .bx_produto).")
        return None

    print(f"🔎 Encontrados {count_cards} itens. Verificando correspondência exata...")

    item_alvo = None
    cod_buscado_limpo = limpar_codigo(codigo_solicitado)

    for i in range(count_cards):
        card = cards.nth(i)

        try:
            cod_fab_site = await card.locator(".codfab strong").inner_text()
            cod_site_limpo = limpar_codigo(cod_fab_site)

            match_found = False
            if cod_buscado_limpo == cod_site_limpo:
                match_found = True
            else:
                # tentativa secundária por N/N
                try:
                    cod_nn_text = await card.locator(".codnn").inner_text()  # "N/N: 270942J"
                    if cod_buscado_limpo in limpar_codigo(cod_nn_text):
                        match_found = True
                        cod_fab_site = codigo_solicitado
                except Exception:
                    pass

            if match_found:
                item_alvo = card
                print(f"✅ Correspondência confirmada: Site '{cod_fab_site}' == Buscado '{codigo_solicitado}'")
                break
            else:
                print(f"item {i+1}: Código '{cod_site_limpo}' não bate com '{cod_buscado_limpo}'. Pulando...")

        except Exception:
            continue

    if not item_alvo:
        print("⚠️ Item encontrado na busca, mas códigos não conferem.")
        return None

    try:
        # Nome
        nome_text = await item_alvo.locator(".nome").inner_text()

        # Marca
        try:
            marca_text = await item_alvo.locator(".fornecedor").inner_text()
        except Exception:
            marca_text = "N/A"

        # Imagem
        try:
            link_img_rel = await item_alvo.locator(".foto img").first.get_attribute("src")
            if link_img_rel and not link_img_rel.startswith("http"):
                link_img = "https://cliente.skypecas.com.br" + link_img_rel
            else:
                link_img = link_img_rel or ""
        except Exception:
            link_img = ""

        # Preço
        try:
            preco_raw = await item_alvo.locator(".preco_final").inner_text()
        except Exception:
            preco_raw = "0,00"

        preco_num = clean_price(preco_raw)

        # Estoque
        qtd_disponivel = 0
        try:
            estoque_text = await item_alvo.locator(".lkEstoqueProduto").inner_text()
            match_estoque = re.search(r"(\d+)", estoque_text or "")
            if match_estoque:
                qtd_disponivel = int(match_estoque.group(1))
        except Exception:
            qtd_disponivel = 0

        qtd_solic = int(quantidade_solicitada or 1)
        tem_estoque = (qtd_disponivel > 0) and (preco_num > 0)
        valor_total = preco_num * qtd_solic
        pode_comprar = tem_estoque

        regiao_rj = {
            "uf": "RJ",
            "preco": str(preco_raw).strip(),
            "preco_num": preco_num,
            "preco_formatado": format_brl(preco_num),
            "qtdSolicitada": qtd_solic,
            "qtdDisponivel": qtd_disponivel,
            "valor_total": valor_total,
            "valor_total_formatado": format_brl(valor_total),
            "podeComprar": pode_comprar,
            "mensagem": None if pode_comprar else "Sem estoque",
            "disponivel": tem_estoque,
        }

        return {
            "codigo": str(codigo_solicitado).strip(),
            "nome": str(nome_text).strip(),
            "marca": str(marca_text).strip(),
            "imagem": link_img,
            "preco": str(preco_raw).strip(),
            "preco_num": preco_num,
            "preco_formatado": format_brl(preco_num),
            "valor_total": valor_total,
            "valor_total_formatado": format_brl(valor_total),
            "uf": "RJ",
            "qtdSolicitada": qtd_solic,
            "qtdDisponivel": qtd_disponivel,
            "podeComprar": pode_comprar,
            "mensagem": regiao_rj["mensagem"],
            "disponivel": tem_estoque,
            "status": "Disponível" if tem_estoque else "Indisponível",
            "regioes": [regiao_rj],
        }

    except Exception as e:
        print(f"⚠ Erro ao ler dados do card Sky Peças: {e}")
        return None


# ===================== EXECUTOR + SALVAMENTO ===================== #
async def processar_lista_produtos_sequencial_sky(page, lista_produtos):
    itens_extraidos = []
    selector_input = "#inpCodigo"

    for idx, item in enumerate(lista_produtos):
        codigo = str(item.get("codigo", "")).strip()
        qtd = int(item.get("quantidade", 1) or 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] SKY -> Buscando: {codigo}")

        if not codigo:
            print("⚠️ Item sem código. Pulando...")
            continue

        try:
            await page.wait_for_selector(selector_input, timeout=15000)
            campo = page.locator(selector_input).first

            await campo.click()
            await page.fill(selector_input, "")
            await campo.type(codigo, delay=100)
            await page.keyboard.press("Enter")

            # ===== ESPERA: produto OU "Nenhum registro" OU modal SweetAlert2 =====
            t1 = asyncio.create_task(page.wait_for_selector(".bx_produto", timeout=7000))
            t2 = asyncio.create_task(page.wait_for_selector("text=Nenhum registro", timeout=7000))
            t3 = asyncio.create_task(page.wait_for_selector(".swal2-popup.swal2-modal", timeout=7000))

            done, pending = await asyncio.wait({t1, t2, t3}, return_when=asyncio.FIRST_COMPLETED)

            for t in pending:
                t.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

            # Se o modal apareceu, fecha e pula extração
            if t3 in done:
                fechou = await fechar_modal_sem_resultados(page)
                if fechou:
                    print("⚠️ Busca sem resultados (modal). Pulando este item.")
                    continue

            # Se não foi modal, ainda assim tenta fechar caso apareça um pouco depois
            await fechar_modal_sem_resultados(page)

            await asyncio.sleep(1.0)

            resultado = await extrair_dados_produto(page, codigo, qtd)

            if resultado:
                itens_extraidos.append(resultado)
                print(f"✅ Extraído: {resultado['nome']} | {resultado['preco_formatado']}")
            else:
                print("⚠️ Produto não identificado ou código divergente.")

        except Exception as e:
            print(f"❌ Falha no loop Sky ({codigo}): {e}")
            try:
                # tenta fechar modal se ele travou o fluxo
                await fechar_modal_sem_resultados(page)
            except Exception:
                pass

            try:
                await page.goto("https://cliente.skypecas.com.br/", wait_until="networkidle")
            except Exception:
                pass

    # ===================== SALVAR NO POSTGRES (LOTE) ===================== #
    if itens_extraidos:
        validos = [r for r in itens_extraidos if r and r.get("codigo")]

        if validos:
            dados_completos = preparar_dados_finais(validos)

            if salvar_lote_sqlite:
                print("⏳ Enviando dados para o PostgreSQL...")
                try:
                    sucesso = salvar_lote_sqlite(dados_completos)
                    if sucesso:
                        print("✅ Dados salvos no banco com sucesso!")
                    else:
                        print("❌ Falha ao salvar no banco.")
                except Exception as e:
                    print(f"❌ Erro ao salvar no PostgreSQL: {e}")
            else:
                print("ℹ️ Salvamento de banco pulado (módulo não importado).")

    return itens_extraidos
