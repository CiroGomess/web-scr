# controllers/addCarrinho/jahu.py
import asyncio
from typing import Dict, Any, List, Optional

def _to_int(v, default=0):
    try:
        return int(str(v).strip())
    except Exception:
        return default

async def _buscar_produto_jahu(page, codigo: str) -> None:
    codigo = (codigo or "").strip()
    if not codigo:
        return

    search = page.locator("#search-input").first
    btn = page.locator("#search-button").first

    await search.wait_for(state="visible", timeout=20000)

    await search.click()
    await search.fill("")
    await search.fill(codigo)

    await btn.click()

    # aguarda resultado renderizar
    try:
        await page.wait_for_selector("div.item up-produto, div.item .up-produto", timeout=20000)
    except Exception:
        pass

    await asyncio.sleep(0.8)

async def _achar_card_por_sku(page, codigo: str):
    codigo = (codigo or "").strip()
    if not codigo:
        return None

    sku_span = page.locator("span.up-produto-sku", has_text=codigo).first
    if await sku_span.count() == 0:
        sku_span = page.locator("span.up-produto-sku-grid", has_text=codigo).first

    if await sku_span.count() == 0:
        candidatos = page.locator("div.item", has_text=codigo)
        if await candidatos.count() == 0:
            return None
        return candidatos.first

    card = sku_span.locator("xpath=ancestor::div[contains(@class,'item')][1]")
    if await card.count() == 0:
        card = sku_span.locator("xpath=ancestor::up-produto[1]")
    return card.first

async def _set_quantidade_jahu(card, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 1)
    if quantidade < 1:
        quantidade = 1

    qty_input = card.locator(".quantity input").first
    await qty_input.wait_for(state="visible", timeout=20000)

    try:
        atual = _to_int(await qty_input.input_value(), 1)
    except Exception:
        atual = 1

    # 1) tenta fill direto
    try:
        await qty_input.click()
        await qty_input.fill(str(quantidade))
        await qty_input.press("Tab")
        await asyncio.sleep(0.25)

        atual2 = _to_int(await qty_input.input_value(), atual)
        return {
            "modo": "fill",
            "quantidade_solicitada": quantidade,
            "quantidade_no_input": atual2
        }
    except Exception:
        pass

    # 2) modo botões (+/-) (ids repetidos, então sempre relativo ao card)
    btn_plus = card.locator(".quantity button", has=card.locator(".w-icon-plus")).first
    btn_minus = card.locator(".quantity button", has=card.locator(".w-icon-minus")).first

    steps = 0
    max_steps = 200

    while atual > quantidade and steps < max_steps:
        if await btn_minus.count() == 0:
            break
        await btn_minus.click()
        await asyncio.sleep(0.12)
        try:
            atual = _to_int(await qty_input.input_value(), atual)
        except Exception:
            break
        steps += 1

    while atual < quantidade and steps < max_steps:
        if await btn_plus.count() == 0:
            break
        antes = atual
        await btn_plus.click()
        await asyncio.sleep(0.12)
        try:
            atual = _to_int(await qty_input.input_value(), atual)
        except Exception:
            break
        if atual == antes:
            break
        steps += 1

    return {
        "modo": "plus_minus",
        "quantidade_solicitada": quantidade,
        "quantidade_no_input": atual,
        "steps": steps
    }

async def _clicar_adicionar_jahu(page, card) -> Dict[str, Any]:
    btn_add = card.locator("button[id^='adicionar_']").first
    await btn_add.wait_for(state="visible", timeout=20000)

    await btn_add.click()

    # demora para efetivar no carrinho
    await asyncio.sleep(3.2)

    try:
        await page.wait_for_load_state("networkidle", timeout=4000)
    except Exception:
        pass

    return {"confirmacao": "sleep_3s"}

async def processar_lista_produtos_jahu(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    resultados = []

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        if not codigo:
            resultados.append({"success": False, "error": "Item sem codigo", "item": item})
            continue

        await _buscar_produto_jahu(page, codigo)

        card = await _achar_card_por_sku(page, codigo)
        if card is None:
            resultados.append({"success": False, "error": "Produto não encontrado", "codigo": codigo})
            continue

        qty_info = await _set_quantidade_jahu(card, quantidade)
        add_info = await _clicar_adicionar_jahu(page, card)

        resultados.append({
            "success": True,
            "codigo": codigo,
            "quantidade": quantidade,
            "qty_info": qty_info,
            "add_info": add_info
        })

    return {"success": True, "itens": resultados}
