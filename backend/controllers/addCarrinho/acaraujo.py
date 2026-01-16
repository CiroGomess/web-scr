import asyncio
from typing import Dict, Any, List

def log_interno(msg: str) -> None:
    print(f"   [Acaraujo Bot] {msg}")

def _to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return default

# ===========================
# HELPERS DE LISTA (PAI/FILHOS)
# ===========================
def _body_selector() -> str:
    # Elemento com duas classes (precisa do . em ambas)
    return (
        "div.products-list__body.products-list__body__last-page, "
        "div.products-list__body"
    )

async def _aguardar_lista_ter_itens(page, timeout_s: int = 20) -> None:
    # 1) espera o PAI
    await page.wait_for_selector(_body_selector(), state="visible", timeout=timeout_s * 1000)
    body = page.locator(_body_selector()).first

    # 2) espera ter FILHOS
    itens = body.locator("div.products-list__item")
    for _ in range(timeout_s * 10):  # checa a cada 100ms
        if await itens.count() > 0:
            return
        await asyncio.sleep(0.1)

    raise Exception("Lista carregou, mas nenhum .products-list__item apareceu dentro do container.")

# ---------------------------
# 1) BUSCA
# ---------------------------
async def _buscar_produto_acaraujo(page, codigo: str) -> None:
    log_interno(f"Iniciando busca pelo código: {codigo}")
    selector_busca = "input.search__input[name='s']"

    await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
    campo = page.locator(selector_busca).first

    await campo.click()
    await campo.fill("")
    await campo.fill(str(codigo))
    log_interno("Código digitado. Pressionando Enter...")
    await campo.press("Enter")

    # Página pode atualizar via XHR.
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(0.5)

    # Aqui é o ponto-chave: aguarda o pai e só então os itens dentro dele
    await _aguardar_lista_ter_itens(page, timeout_s=20)

# ---------------------------
# 2) ACHAR ITEM (CARD) PELO SKU
# ---------------------------
async def _achar_item_por_sku(page, codigo: str):
    log_interno("Localizando item na grade de produtos...")
    codigo = (codigo or "").strip().upper()

    try:
        # garante que pai e filhos existam
        await _aguardar_lista_ter_itens(page, timeout_s=15)
    except Exception as e:
        log_interno(f"Nenhum item apareceu após a busca: {e}")
        return None

    body = page.locator(_body_selector()).first
    itens = body.locator("div.products-list__item")

    # Estratégia 1: achar pelo atributo data-codigo-produto dentro do body
    el = body.locator(f"[data-codigo-produto='{codigo}']").first
    if await el.count() > 0:
        item = el.locator("xpath=ancestor::div[contains(@class,'products-list__item')]").first
        if await item.count() > 0:
            log_interno(f"Item localizado via atributo data-codigo-produto: {codigo}")
            return item

    # Estratégia 2 (fallback): texto “Código: M8183”
    item_fallback = itens.filter(has_text=f"Código: {codigo}").first
    if await item_fallback.count() > 0:
        log_interno(f"Item localizado via texto Código: {codigo}")
        return item_fallback

    log_interno(f"ERRO: Item com código {codigo} não encontrado dentro do container.")
    return None

# ---------------------------
# 3) SET QUANTIDADE (com fallback + / -)
# ---------------------------
async def _set_quantidade_acaraujo(page, item, codigo: str, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 1)
    codigo = (codigo or "").strip().upper()
    log_interno(f"Inserindo quantidade solicitada: {quantidade} (SKU: {codigo})")

    qty_input = item.locator(
        f"input.input-number__input[data-codigo-produto='{codigo}']"
    ).first

    try:
        await qty_input.wait_for(state="visible", timeout=8000)
        await qty_input.scroll_into_view_if_needed()

        # Tentativa 1: fill + eventos
        await qty_input.click()
        await qty_input.fill(str(quantidade))
        await qty_input.dispatch_event("input")
        await qty_input.dispatch_event("change")
        await qty_input.evaluate("el => el.blur()")
        await asyncio.sleep(0.4)

        atual = _to_int(await qty_input.input_value(), -1)
        if atual == quantidade:
            log_interno(f"Quantidade aplicada via input: {atual}")
            return {"success": True, "qtd": quantidade}

        # Tentativa 2: forçar por JS
        log_interno(f"Fill não persistiu (atual={atual}). Forçando via JS...")
        await qty_input.evaluate(
            """(el, v) => {
                el.value = v;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.blur();
            }""",
            str(quantidade),
        )
        await asyncio.sleep(0.4)

        atual = _to_int(await qty_input.input_value(), -1)
        if atual == quantidade:
            log_interno(f"Quantidade aplicada via JS: {atual}")
            return {"success": True, "qtd": quantidade}

        # Tentativa 3: clicar no + / -
        log_interno("JS não persistiu. Ajustando via botões + / - ...")

        btn_plus = item.locator(".input-number__add").first
        btn_minus = item.locator(".input-number__sub").first

        atual = _to_int(await qty_input.input_value(), 1)

        max_passos = 50
        passos = 0

        while atual != quantidade and passos < max_passos:
            if atual < quantidade:
                await btn_plus.click(force=True)
            else:
                await btn_minus.click(force=True)

            await asyncio.sleep(0.15)
            atual = _to_int(await qty_input.input_value(), atual)
            passos += 1

        if atual == quantidade:
            log_interno(f"Quantidade ajustada via +/−: {atual}")
            return {"success": True, "qtd": quantidade}

        return {"success": False, "error": f"Não consegui ajustar a quantidade. Final={atual}, esperado={quantidade}"}

    except Exception as e:
        log_interno(f"Erro ao definir quantidade: {e}")
        return {"success": False, "error": str(e)}

# ---------------------------
# 4) CLICAR ADICIONAR
# ---------------------------
async def _clicar_adicionar_acaraujo(page, item, codigo: str) -> Dict[str, Any]:
    codigo = (codigo or "").strip().upper()
    log_interno(f"Verificando botão de adicionar ao carrinho (SKU: {codigo})...")

    btn_add = item.locator(
        f"button.product-card__addtocart[data-codigo-produto='{codigo}']"
    ).first

    try:
        await btn_add.wait_for(state="visible", timeout=10000)
        await btn_add.scroll_into_view_if_needed()

        if await btn_add.is_disabled():
            log_interno("Botão está desabilitado (Provavelmente sem estoque).")
            return {"success": False, "error": "Botão desabilitado (sem estoque?)"}

        log_interno("Clicando no botão 'Adicionar'...")
        await btn_add.click(force=True)

        await asyncio.sleep(1.5)
        log_interno("Clique em 'Adicionar' executado.")
        return {"success": True}

    except Exception as e:
        log_interno(f"Erro ao clicar no botão adicionar: {e}")
        return {"success": False, "error": str(e)}

# ---------------------------
# 5) PROCESSAR LISTA
# ---------------------------
async def processar_lista_produtos_acaraujo(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    resultados = []
    log_interno(f"Processando {len(itens)} itens para o carrinho...")

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip().upper()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        log_interno(f"--- Iniciando Processo: {codigo} / Qtd: {quantidade} ---")

        try:
            # 1) Busca
            await _buscar_produto_acaraujo(page, codigo)

            # 2) Item
            item_card = await _achar_item_por_sku(page, codigo)
            if not item_card:
                resultados.append({"success": False, "error": "Produto não encontrado", "codigo": codigo})
                continue

            # 3) Quantidade
            qtd_res = await _set_quantidade_acaraujo(page, item_card, codigo, quantidade)
            if not qtd_res["success"]:
                resultados.append({"success": False, "error": qtd_res.get("error", "Erro na quantidade"), "codigo": codigo})
                continue

            # 4) Adicionar
            add_res = await _clicar_adicionar_acaraujo(page, item_card, codigo)

            resultados.append({
                "success": add_res["success"],
                "codigo": codigo,
                "quantidade": quantidade,
                "detalhes": add_res
            })

        except Exception as e:
            log_interno(f"Falha crítica no item {codigo}: {e}")
            resultados.append({"success": False, "error": str(e), "codigo": codigo})

    # Espera 3 segundos antes do seu fluxo encerrar e o navegador/página ser fechado
    log_interno("Aguardando 3 segundos antes de encerrar...")
    await asyncio.sleep(3)

    return {"success": True, "itens": resultados}

