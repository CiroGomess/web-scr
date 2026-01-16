import asyncio
from typing import Dict, Any, List

def log_interno(msg: str) -> None:
    print(f"   [GB Bot] {msg}")

def _to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return default

# ---------------------------
# MODAL: "Existe um pedido iniciado anteriormente."
# ---------------------------
async def _tratar_modal_pedido_iniciado(page) -> bool:
    """
    Se aparecer o modal 'Atenção' perguntando se deseja iniciar novo ou continuar,
    clica em 'Continuar Pedido' e aguarda o modal sumir.
    Retorna True se o modal foi tratado, False se não apareceu.
    """

    # O modal tem classes: "modal ... ConfirmDialog open"
    modal = page.locator("div.modal.ConfirmDialog.open").first

    try:
        # se não existir/visível, sai rápido
        if await modal.count() == 0:
            return False

        if not await modal.is_visible():
            return False

        # Confirma que é o modal certo (texto)
        if not await modal.locator("text=Existe um pedido iniciado anteriormente.").count():
            # Se for outro modal, não mexe
            return False

        log_interno("Modal detectado: existe um pedido iniciado anteriormente. Clicando em 'Continuar Pedido'...")

        # Clicar no botão "Continuar Pedido"
        btn_continuar = modal.locator("a.modal-action").filter(has_text="Continuar Pedido").first
        await btn_continuar.click(force=True)

        # Aguarda o modal fechar (sumir ou perder classe open)
        # Preferi aguardar sumir visualmente
        for _ in range(50):  # 5s total (50 * 0.1)
            # se não estiver visível, consideramos fechado
            try:
                if await modal.count() == 0 or (await modal.is_visible()) is False:
                    break
            except Exception:
                break
            await asyncio.sleep(0.1)

        await asyncio.sleep(0.4)  # tempo extra pro Vue processar
        log_interno("Modal tratado com sucesso (Continuar Pedido).")
        return True

    except Exception as e:
        log_interno(f"Falha ao tratar modal de pedido anterior: {e}")
        return False

# ---------------------------
# 1) GARANTIR TELA: FAZER PEDIDO (#/unit005)
# ---------------------------
async def garantir_tela_fazer_pedido(page) -> None:
    if "unit005" not in (page.url or ""):
        log_interno("Navegando para 'Fazer Pedido' (#/unit005)...")

        menu_selector = 'a[href="#/unit005"]'
        try:
            await page.wait_for_selector(menu_selector, state="attached", timeout=15000)

            menu = page.locator(menu_selector).first
            if await menu.is_visible():
                await menu.click(force=True)
            else:
                await page.goto("https://ecommerce.gb.com.br/#/unit005", wait_until="domcontentloaded")

        except Exception as e:
            log_interno(f"Falha ao clicar no menu, forçando URL. Motivo: {e}")
            await page.goto("https://ecommerce.gb.com.br/#/unit005", wait_until="domcontentloaded")

        # tempo pro Vue montar
        await asyncio.sleep(2.5)

    # SEMPRE que estiver na unit005, tenta tratar o modal (se existir)
    await _tratar_modal_pedido_iniciado(page)

# ---------------------------
# 2) BUSCAR ITEM PELO CÓDIGO (MESMO INPUT)
# ---------------------------
async def buscar_item_gb(page, codigo: str) -> None:
    await garantir_tela_fazer_pedido(page)

    # redundância: o modal pode surgir “um pouco depois” do load
    await _tratar_modal_pedido_iniciado(page)

    selector_busca = "#txt-search-simples"
    log_interno(f"Buscando item: {codigo}")

    await page.wait_for_selector(selector_busca, state="attached", timeout=20000)

    # clicar no label primeiro (Materialize/Vue às vezes cobre o input)
    try:
        await page.click("label[for='txt-search-simples']", force=True, timeout=2000)
    except Exception:
        try:
            await page.locator(selector_busca).click(force=True, timeout=2000)
        except Exception:
            pass

    await asyncio.sleep(0.2)

    # limpar + preencher (com fallback JS)
    try:
        await page.fill(selector_busca, "")
        await page.fill(selector_busca, str(codigo))
    except Exception:
        log_interno("Fill padrão falhou. Usando injeção JS no input...")
        await page.evaluate(
            """(codigo) => {
                var input = document.getElementById('txt-search-simples');
                if (!input) return;
                input.value = codigo;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            str(codigo),
        )

    await asyncio.sleep(0.2)

    # Enter + clique na lupa (redundância)
    try:
        await page.keyboard.press("Enter")
    except Exception:
        pass

    try:
        await page.click("i.material-icons.prefix:has-text('search')", timeout=1500, force=True)
    except Exception:
        pass

    # aguarda inputs de quantidade do pedido (data-peddid)
    try:
        await page.wait_for_selector("input[type='number'][data-peddid]", state="attached", timeout=12000)
    except Exception:
        pass

    await asyncio.sleep(0.8)

# ---------------------------
# 3) ACHAR O "BLOCO/LINHA" DO ITEM PELO CÓDIGO
# ---------------------------
async def achar_container_item_por_codigo(page, codigo: str):
    codigo = (codigo or "").strip().upper()

    linha = page.locator("tr:has(input[type='number'][data-peddid])").filter(has_text=codigo).first
    if await linha.count() > 0:
        return linha

    card = page.locator("div:has(input[type='number'][data-peddid])").filter(has_text=codigo).first
    if await card.count() > 0:
        return card

    el = page.locator(f"text={codigo}").first
    if await el.count() > 0:
        container = el.locator("xpath=ancestor::*[.//input[@data-peddid]]").first
        if await container.count() > 0:
            return container

    return None

# ---------------------------
# 4) SETAR QUANTIDADE NO INPUT data-peddid
# ---------------------------
async def setar_quantidade_no_pedido(page, container, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 0)

    qty_input = container.locator("input[type='number'][data-peddid]").first
    try:
        await qty_input.wait_for(state="visible", timeout=8000)
        await qty_input.scroll_into_view_if_needed()

        await qty_input.click(force=True)
        try:
            await qty_input.fill(str(quantidade))
        except Exception:
            await qty_input.evaluate(
                """(el, v) => {
                    el.value = v;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.blur();
                }""",
                str(quantidade),
            )

        try:
            await qty_input.dispatch_event("input")
            await qty_input.dispatch_event("change")
            await qty_input.evaluate("el => el.blur()")
        except Exception:
            pass

        await asyncio.sleep(0.3)

        final_val = await qty_input.input_value()
        final_int = _to_int(final_val, -1)

        if final_int != quantidade:
            return {
                "success": False,
                "error": f"Quantidade não persistiu. Valor final no input: {final_val}",
                "qtd_enviada": quantidade,
                "qtd_final": final_val,
            }

        return {"success": True, "qtd": final_int}

    except Exception as e:
        return {"success": False, "error": str(e)}

# ---------------------------
# 5) FUNÇÃO PRINCIPAL (PRODUÇÃO)
# ---------------------------
async def processar_lista_produtos_gb(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    resultados = []
    log_interno(f"Processando {len(itens)} itens (GB) para o pedido...")

    await garantir_tela_fazer_pedido(page)

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip().upper()
        quantidade = _to_int(item.get("quantidade", 0), 0)

        log_interno(f"--- GB: {codigo} / Qtd: {quantidade} ---")

        try:
            await buscar_item_gb(page, codigo)

            container = await achar_container_item_por_codigo(page, codigo)
            if not container:
                resultados.append({"success": False, "error": "Produto não encontrado na tela de pedido", "codigo": codigo})
                continue

            qtd_res = await setar_quantidade_no_pedido(page, container, quantidade)
            resultados.append({
                "success": qtd_res.get("success", False),
                "codigo": codigo,
                "quantidade": quantidade,
                "detalhes": qtd_res,
            })

        except Exception as e:
            resultados.append({"success": False, "codigo": codigo, "error": str(e)})

    log_interno("Aguardando 3 segundos antes de encerrar...")
    await asyncio.sleep(3)

    return {"success": True, "itens": resultados}
