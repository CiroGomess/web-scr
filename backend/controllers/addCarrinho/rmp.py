# controllers/addCarrinho/rmp.py
import asyncio
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

RMP_BASE = "https://loja.rmp.com.br"
# Magento geralmente responde bem com q=
SEARCH_URL = RMP_BASE + "/catalogsearch/result/?q={q}"
# Se o RMP exigir "code" também, use:
# SEARCH_URL = RMP_BASE + "/catalogsearch/result/?code={q}&q={q}"


def _to_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


async def _find_form_for_codigo(page, codigo: str):
    """
    Tenta encontrar o form de add-to-cart do item correspondente ao código.
    O HTML do RMP traz:
      form[data-role="tocart-form"][data-product-sku="00010057000178"]
    e também li#product-item-00010057000178
    """
    codigo = (codigo or "").strip()
    if not codigo:
        return None, None

    # 1) Melhor caso: form com data-product-sku = codigo
    form = page.locator(f"form[data-role='tocart-form'][data-product-sku='{codigo}']").first
    if await form.count() > 0:
        li = form.locator("xpath=ancestor::li[contains(@class,'product-item')]").first
        return form, li

    # 2) Alternativa: li com id product-item-{codigo}
    li = page.locator(f"li#product-item-{codigo}").first
    if await li.count() > 0:
        form = li.locator("form[data-role='tocart-form']").first
        if await form.count() > 0:
            return form, li

    # 3) Fallback: primeiro resultado da lista (quando o "codigo" não bate com SKU)
    # (ex.: você busca por código fabricante, mas o SKU é outro)
    li = page.locator("li.item.product.product-item.loaded").first
    if await li.count() > 0:
        form = li.locator("form[data-role='tocart-form']").first
        if await form.count() > 0:
            return form, li

    # 4) Último fallback: qualquer form tocart-form
    form = page.locator("form[data-role='tocart-form']").first
    if await form.count() > 0:
        li = form.locator("xpath=ancestor::li[contains(@class,'product-item')]").first
        return form, li

    return None, None


async def _get_stock_from_li(li) -> Optional[int]:
    """
    No seu HTML: <li ... data-stock="24">
    """
    if not li:
        return None
    try:
        stock_attr = await li.get_attribute("data-stock")
        if stock_attr is None:
            return None
        return _to_int(stock_attr, None)
    except Exception:
        return None


async def _get_max_allowed_from_qty_input(qty_input) -> Optional[int]:
    """
    No seu HTML: data-validate='{"validate-item-quantity":{"minAllowed":1,"maxAllowed":24}}'
    """
    try:
        dv = await qty_input.get_attribute("data-validate")
        if not dv:
            return None
        m = re.search(r'"maxAllowed"\s*:\s*(\d+)', dv)
        if not m:
            return None
        return _to_int(m.group(1), None)
    except Exception:
        return None


async def _set_qty_in_form(form, quantidade: int) -> Dict[str, Any]:
    """
    Magento RMP:
    - input name="qty" pode vir readonly (não aceita fill).
    - deve usar botões increment/decrement.
    - respeita minAllowed/maxAllowed e aplica quantidade final.
    """
    quantidade = _to_int(quantidade, 1)
    if quantidade < 1:
        quantidade = 1

    qty_input = form.locator("input[name='qty']").first
    await qty_input.wait_for(state="visible", timeout=15000)

    # lê min/maxAllowed do data-validate (quando existir)
    max_allowed = await _get_max_allowed_from_qty_input(qty_input)

    # minAllowed pode vir no data-validate também (no seu HTML: minAllowed:2)
    min_allowed = None
    try:
        dv = await qty_input.get_attribute("data-validate")
        if dv:
            import re
            m = re.search(r'"minAllowed"\s*:\s*(\d+)', dv)
            if m:
                min_allowed = _to_int(m.group(1), None)
    except Exception:
        pass

    # valor atual
    try:
        atual = _to_int(await qty_input.input_value(), 0)
    except Exception:
        atual = 0

    # aplica limites
    qtd_final = quantidade
    if isinstance(min_allowed, int) and min_allowed > 0 and qtd_final < min_allowed:
        qtd_final = min_allowed

    if isinstance(max_allowed, int) and max_allowed > 0 and qtd_final > max_allowed:
        qtd_final = max_allowed

    # readonly?
    readonly_attr = await qty_input.get_attribute("readonly")
    is_readonly = readonly_attr is not None

    # se não for readonly, tenta fill normal
    if not is_readonly:
        await qty_input.click()
        await qty_input.fill(str(qtd_final))
        try:
            await qty_input.press("Tab")
        except Exception:
            pass

        try:
            atual2 = _to_int(await qty_input.input_value(), qtd_final)
        except Exception:
            atual2 = qtd_final

        return {
            "quantidade_solicitada": quantidade,
            "quantidade_aplicada": qtd_final,
            "quantidade_no_input": atual2,
            "min_allowed": min_allowed,
            "max_allowed": max_allowed,
            "modo": "fill"
        }

    # se for readonly, usa botões +/- até chegar
    btn_plus = form.locator("button.increment-qty").first
    btn_minus = form.locator("button.decrement-qty").first

    # garante que existem
    await btn_plus.wait_for(state="visible", timeout=15000)

    # se atual estiver acima do alvo, tenta diminuir (se o site permitir)
    # (alguns readonly deixam decrementar, outros não; então é best-effort)
    max_steps = 200  # evita loop infinito
    steps = 0

    # primeiro, tenta aproximar para baixo (caso atual > alvo)
    while atual > qtd_final and steps < max_steps:
        try:
            if await btn_minus.count() > 0:
                await btn_minus.click()
                await asyncio.sleep(0.15)
        except Exception:
            break

        try:
            atual = _to_int(await qty_input.input_value(), atual)
        except Exception:
            break

        steps += 1

    # agora sobe até o alvo (ou até travar)
    travou = False
    while atual < qtd_final and steps < max_steps:
        antes = atual
        await btn_plus.click()
        await asyncio.sleep(0.15)

        try:
            atual = _to_int(await qty_input.input_value(), atual)
        except Exception:
            travou = True
            break

        # se não mudou, trava
        if atual == antes:
            travou = True
            break

        # respeita max_allowed
        if isinstance(max_allowed, int) and max_allowed > 0 and atual >= max_allowed:
            break

        steps += 1

    return {
        "quantidade_solicitada": quantidade,
        "quantidade_aplicada": qtd_final,
        "quantidade_no_input": atual,
        "min_allowed": min_allowed,
        "max_allowed": max_allowed,
        "modo": "click_plus_minus",
        "steps": steps,
        "travou": travou
    }



async def _submit_add_to_cart(form, page) -> Dict[str, Any]:
    """
    Clica no botão submit do form:
      <button type="submit" class="action tocart primary"><span>Adicionar</span></button>
    Captura mensagens comuns do Magento.
    """
    btn = form.locator("button.action.tocart.primary[type='submit']").first
    await btn.wait_for(state="visible", timeout=15000)

    # Limpa mensagens antigas (best-effort)
    try:
        await page.evaluate("""
          document.querySelectorAll('.messages .message, .page.messages .message').forEach(el => el.remove());
        """)
    except Exception:
        pass

    await btn.click()

    # Magento costuma renderizar mensagens em:
    # .messages .message-success / .messages .message-error
    msg_success = None
    msg_error = None

    try:
        success_el = page.locator(".messages .message-success, .page.messages .message-success").first
        await success_el.wait_for(state="visible", timeout=8000)
        msg_success = (await success_el.inner_text()).strip()
    except Exception:
        pass

    if not msg_success:
        try:
            error_el = page.locator(".messages .message-error, .page.messages .message-error").first
            await error_el.wait_for(state="visible", timeout=4000)
            msg_error = (await error_el.inner_text()).strip()
        except Exception:
            pass

    return {
        "success_message": msg_success,
        "error_message": msg_error,
        "ok": bool(msg_success) and not bool(msg_error)
    }


async def adicionar_itens_ao_carrinho_rmp(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    resultados = []

    for item in itens:
        codigo = str(item.get("codigo") or "").strip()
        quantidade = _to_int(item.get("quantidade"), 1)

        if not codigo:
            resultados.append({
                "codigo": None,
                "success": False,
                "error": "Item sem código.",
                "payload": item
            })
            continue

        try:
            # 1) Ir para a busca
            url = SEARCH_URL.format(q=quote_plus(codigo))
            await page.goto(url, wait_until="networkidle", timeout=45000)

            # 2) Aguardar algum resultado (ou detectar “sem resultados”)
            # Ajuste se o RMP tiver seletor específico de “nenhum resultado”
            await asyncio.sleep(0.6)

            # 3) Encontrar o form correto
            form, li = await _find_form_for_codigo(page, codigo)
            if not form:
                resultados.append({
                    "codigo": codigo,
                    "success": False,
                    "error": "Nenhum formulário tocart-form encontrado (produto não apareceu na busca)."
                })
                continue

            # 4) Estoque (se houver no li)
            stock = await _get_stock_from_li(li)
            qtd_desejada = quantidade

            # Se o site dá data-stock, já limitamos
            qtd_usar = qtd_desejada
            if isinstance(stock, int) and stock >= 0 and qtd_usar > stock:
                qtd_usar = stock if stock > 0 else 1

            # 5) Setar quantidade
            qty_info = await _set_qty_in_form(form, qtd_usar)

            # 6) Enviar (Adicionar ao carrinho)
            add_info = await _submit_add_to_cart(form, page)

            resultados.append({
                "codigo": codigo,
                "stock": stock,
                "quantidade": qty_info,
                "carrinho": add_info,
                "success": bool(add_info.get("ok"))
            })

        except Exception as e:
            resultados.append({
                "codigo": codigo,
                "success": False,
                "error": str(e)
            })

    total_ok = sum(1 for r in resultados if r.get("success"))
    total_fail = len(resultados) - total_ok

    return {
        "success": (total_fail == 0),
        "total_itens": len(itens),
        "total_ok": total_ok,
        "total_fail": total_fail,
        "resultados": resultados
    }
