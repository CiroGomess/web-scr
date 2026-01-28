import asyncio
import re
from datetime import datetime

# ===================== IMPORTAÇÃO DO SERVIÇO DE BANCO ===================== #
try:
    from services.db_saver import salvar_lote_sqlite
except ImportError:
    print("⚠️ Aviso: 'services.db_saver' não encontrado. O salvamento no banco será pulado.")
    salvar_lote_sqlite = None


# ===================== AUXILIARES DE FORMATAÇÃO ===================== #
def clean_price(preco_str):
    if not preco_str:
        return 0.0
    preco = re.sub(r"[^\d,]", "", preco_str)
    preco = preco.replace(",", ".")
    try:
        return float(preco)
    except Exception:
        return 0.0


def format_brl(valor):
    if valor is None or valor == 0:
        return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ===================== AUXILIAR: FECHAR POPUP "IMPORTANTE" ===================== #
async def fechar_popup_jahu(page):
    """
    Fecha o popup IMPORTANTE quando aparecer:
    1) marca #naoMostrarNovamente (se existir)
    2) clica em "Fechar" (texto) ou button[onclick*=fecharPopup]
    """
    try:
        popup = page.locator("#popup")
        if await popup.count() == 0:
            return
        if not await popup.is_visible():
            return

        print("🍪 Popup 'IMPORTANTE' detectado. Marcando 'Não mostrar novamente' e fechando...")

        # checkbox
        try:
            chk = popup.locator("#naoMostrarNovamente")
            if await chk.count() > 0:
                try:
                    marcado = await chk.is_checked()
                except Exception:
                    marcado = False
                if not marcado:
                    await chk.click()
                    await asyncio.sleep(0.3)
        except Exception:
            pass

        # botão fechar
        try:
            btn = popup.locator("button:has-text('Fechar')").first
            if await btn.count() == 0:
                btn = popup.locator("button[onclick*='fecharPopup']").first

            if await btn.count() > 0:
                await btn.click()
                await asyncio.sleep(0.8)
            else:
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)
        except Exception:
            pass

    except Exception:
        pass


# ===================== AUXILIAR: SELECIONAR EMPRESA "RIO DE JANEIRO" ===================== #
async def selecionar_empresa_rio_se_precisar(page):
    """
    Se aparecer #listEmpresa-main, seleciona "RIO DE JANEIRO".
    """
    try:
        await fechar_popup_jahu(page)

        lista_empresas = page.locator("#listEmpresa-main")
        if await lista_empresas.count() > 0 and await lista_empresas.is_visible():
            print("🏢 Lista de empresas detectada. Selecionando: RIO DE JANEIRO...")

            item_rio = lista_empresas.locator(
                "a.list-group-item:has(div:has-text('RIO DE JANEIRO'))"
            ).first

            if await item_rio.count() == 0:
                item_rio = lista_empresas.locator(
                    "a.list-group-item:has-text('RIO DE JANEIRO')"
                ).first

            if await item_rio.count() > 0:
                await item_rio.click()
                await asyncio.sleep(1.2)
                print("✅ Empresa selecionada: RIO DE JANEIRO")
                return True

            print("⚠️ Lista de empresas aberta, mas não achei 'RIO DE JANEIRO'.")
            return False

        return False

    except Exception as e:
        print(f"⚠️ Erro ao selecionar empresa: {e}")
        return False


# ===================== AUXILIAR: CLICAR NO CLIENTE ===================== #
async def selecionar_cliente_se_precisar(page):
    """
    Se aparecer a tela de cliente (#listClient-main), clica no item.
    Prioridade:
      1) item que contenha "AUTO PECAS VIEIRA"
      2) senão, primeiro item
    Depois:
      - clica VOLTAR
      - aguarda voltar para lista de empresas e seleciona RIO novamente
    """
    try:
        await fechar_popup_jahu(page)

        lista_clientes = page.locator("#listClient-main")
        if await lista_clientes.count() == 0 or not await lista_clientes.is_visible():
            return False

        print("👥 Tela de seleção de cliente detectada. Selecionando cliente...")

        # 1) tenta pelo nome
        item_vieira = lista_clientes.locator(
            "a.list-group-item:has(div:has-text('AUTO PECAS VIEIRA'))"
        ).first

        if await item_vieira.count() > 0:
            await item_vieira.click()
            await asyncio.sleep(1.2)
            print("✅ Cliente selecionado: AUTO PECAS VIEIRA")
        else:
            # 2) fallback: primeiro item
            primeiro_item = lista_clientes.locator("a.list-group-item").first
            if await primeiro_item.count() > 0:
                await primeiro_item.click()
                await asyncio.sleep(1.2)
                print("✅ Cliente selecionado: 1º item da lista")
            else:
                print("⚠️ Tela de cliente aberta, mas não encontrei itens clicáveis.")
                return False

        await fechar_popup_jahu(page)

        # Após selecionar cliente: clicar VOLTAR (se existir)
        try:
            btn_voltar = page.locator("div.previous button:has-text('VOLTAR')").first
            if await btn_voltar.count() > 0 and await btn_voltar.is_visible():
                print("↩️ Clicando em VOLTAR após selecionar cliente...")
                await btn_voltar.click()
                await asyncio.sleep(1.2)

                # Aguarda empresas aparecerem e seleciona RIO de novo
                await fechar_popup_jahu(page)
                print("⏳ Aguardando 3s antes de selecionar empresa novamente...")
                await asyncio.sleep(3)

                # espera lista de empresas
                try:
                    await page.wait_for_selector("#listEmpresa-main", timeout=15000)
                except Exception:
                    pass

                await selecionar_empresa_rio_se_precisar(page)

        except Exception:
            pass

        return True

    except Exception as e:
        print(f"⚠️ Erro ao selecionar cliente: {e}")
        return False


# ===================== RESOLVER SELEÇÕES PÓS-LOGIN ===================== #
async def resolver_selecao_pos_login(page):
    """
    Pós-login pode pedir:
    - Selecionar empresa (RIO)
    - Selecionar cliente (listClient) -> clicar cliente -> VOLTAR -> selecionar RIO
    Se não aparecer nada, segue.
    """
    await fechar_popup_jahu(page)

    # Se cair na lista de empresas direto, escolhe RIO
    selecionou_empresa = await selecionar_empresa_rio_se_precisar(page)
    if selecionou_empresa:
        await fechar_popup_jahu(page)
        print("⏳ Aguardando 3s após seleção de empresa...")
        await asyncio.sleep(3)

    # Se cair na lista de clientes, seleciona cliente e depois VOLTAR + RIO
    selecionou_cliente = await selecionar_cliente_se_precisar(page)
    if selecionou_cliente:
        await fechar_popup_jahu(page)
        print("⏳ Aguardando 3s após seleção de cliente...")
        await asyncio.sleep(3)

    # garante que search-input exista (quando a tela final já estiver pronta)
    try:
        await page.wait_for_selector("#search-input", timeout=15000)
    except Exception:
        pass


# ===================== DETECTAR 'SEM RESULTADOS' ===================== #
async def sem_resultados_busca(page, codigo):
    try:
        await fechar_popup_jahu(page)

        empty = page.locator(".products-empty")
        if await empty.count() > 0 and await empty.is_visible():
            txt = (await empty.inner_text()).strip().lower()
            if "não encontramos nenhum resultado" in txt or "nao encontramos nenhum resultado" in txt:
                print(f"🔎 Sem resultados para: {codigo}")
                return True
    except Exception:
        pass
    return False


# ===================== EXTRAÇÃO DE DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    await fechar_popup_jahu(page)

    cards = page.locator(".up-produto")
    total_cards = await cards.count()

    if total_cards == 0:
        return {
            "codigo": codigo_solicitado,
            "nome": "Não encontrado",
            "preco": "R$ 0,00",
            "uf": "RJ",
            "disponivel": False,
            "regioes": []
        }

    for i in range(total_cards):
        await fechar_popup_jahu(page)
        card = cards.nth(i)

        try:
            sku_no_card = await card.locator("#produto-sku-grid b").inner_text()
            sku_no_card = sku_no_card.strip()
        except Exception:
            continue

        if sku_no_card == codigo_solicitado or sku_no_card.startswith(codigo_solicitado):
            try:
                nome_selector = card.locator(".description span.ng-binding:not(:has-text('SKU:'))")
                nome_text = (await nome_selector.inner_text()).strip()

                link_img = await card.locator("img.originalImg").first.get_attribute("src")

                preco_raw = (await card.locator(".product-price").inner_text()).strip()
                preco_num = clean_price(preco_raw)

                status_estoque = ""
                try:
                    status_estoque = (await card.locator(".produto-status").inner_text()).strip()
                except Exception:
                    try:
                        status_estoque = (await card.locator(".highlight").inner_text()).strip()
                    except Exception:
                        status_estoque = ""

                tem_estoque = ("indisponível" not in status_estoque.lower()) and (preco_num > 0)
                qtd_disponivel = 1 if tem_estoque else 0

                valor_total = preco_num * quantidade_solicitada
                pode_comprar = tem_estoque and preco_num > 0

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
                    "mensagem": None if pode_comprar else "Sem estoque imediato",
                    "disponivel": tem_estoque
                }

                return {
                    "codigo": sku_no_card,
                    "nome": nome_text,
                    "marca": "JAHU",
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
                    "status": status_estoque,
                    "regioes": [regiao_rj]
                }

            except Exception as e:
                print(f"⚠ Erro nos detalhes do card: {e}")
                continue

    return None


# ===================== PREPARAÇÃO DE DADOS PARA O BANCO ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedor": "Jahu",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }


# ===================== FUNÇÃO PRINCIPAL (NOME FINAL) ===================== #
async def processar_lista_produtos_jahu(page, lista_produtos, context=None, **kwargs):
    """
    Fluxo final:
    - Fecha popup IMPORTANTE
    - Se aparecer Cliente => seleciona cliente -> VOLTAR -> seleciona RIO
    - Se aparecer Empresa => seleciona RIO
    - Aguarda 3s entre etapas grandes
    - Loop de SKUs com delay 3s antes de cada busca
    """
    itens_extraidos = []

    # Pós-login: resolve seleções
    await resolver_selecao_pos_login(page)

    for idx, item in enumerate(lista_produtos):
        await fechar_popup_jahu(page)

        codigo = str(item.get("codigo", "")).strip()
        quantidade = int(item.get("quantidade", 1))
        if not codigo:
            continue

        print(f"\n⏳ Aguardando 3s antes de iniciar a busca do próximo SKU...")
        await asyncio.sleep(3)

        print(f"📦 [{idx+1}/{len(lista_produtos)}] Buscando: {codigo}")

        try:
            await fechar_popup_jahu(page)

            campo_busca = page.locator("#search-input")
            await campo_busca.wait_for(state="visible", timeout=15000)

            await campo_busca.fill("")
            await campo_busca.type(codigo, delay=80)
            await page.keyboard.press("Enter")

            await asyncio.sleep(2)
            await fechar_popup_jahu(page)

            # Se reaparecer tela de seleção (cliente/empresa), resolve e segue
            await resolver_selecao_pos_login(page)

            if await sem_resultados_busca(page, codigo):
                continue

            resultado = await extrair_dados_produto(page, codigo, quantidade)
            if resultado:
                itens_extraidos.append(resultado)
                print(f"✅ Extraído: {resultado['nome']} | SKU: {resultado['codigo']}")
            else:
                print(f"⚠ Não bateu SKU nos cards para: {codigo}")

        except Exception as e:
            print(f"❌ Erro no loop para o código {codigo}: {e}")

    # ===================== SALVAR NO BANCO (se configurado) ===================== #
    if itens_extraidos:
        validos = [r for r in itens_extraidos if r and r.get("codigo")]
        if validos:
            dados_completos = preparar_dados_finais(validos)

            if salvar_lote_sqlite:
                print("⏳ Enviando dados para o banco...")
                sucesso = salvar_lote_sqlite(dados_completos)
                if sucesso:
                    print("✅ Dados salvos no banco com sucesso!")
                else:
                    print("❌ Falha ao salvar no banco.")
            else:
                print("ℹ️ Salvamento de banco pulado (módulo não importado).")

    return itens_extraidos



