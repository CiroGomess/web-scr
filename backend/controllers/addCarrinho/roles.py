# controllers/addCarrinho/roles.py
import asyncio
import re
from typing import Dict, Any, List, Optional

def _to_int(v, default=0):
    try:
        return int(str(v).strip())
    except Exception:
        return default


async def _buscar_produto_roles(page, codigo: str) -> None:
    """
    Preenche o campo de busca e aciona a pesquisa.
    Depois aguarda a tabela trazer uma linha com o código (quando existir).
    """
    codigo = (codigo or "").strip()
    if not codigo:
        return

    search = page.locator("#search-prod").first
    btn = page.locator("#btn-search-btn-prod").first

    await search.wait_for(state="visible", timeout=20000)

    await search.click()
    await search.fill("")
    await search.fill(codigo)

    await btn.click()

    # Aguarda algo da tabela aparecer (ou timeout)
    # Se não encontrar, não quebra aqui; quem valida é o _achar_linha_por_codigo.
    try:
        await page.locator("table#table-produtos-CatalogoNovo tbody tr", has_text=codigo).first.wait_for(
            state="visible",
            timeout=12000
        )
    except Exception:
        await asyncio.sleep(0.8)


async def _achar_linha_por_codigo(page, codigo: str):
    """
    A linha contém o código em um <span> (ex: 01543BR).
    Busca por TR que contenha o texto do código.
    """
    codigo = (codigo or "").strip()
    if not codigo:
        return None

    candidatos = page.locator("table#table-produtos-CatalogoNovo tbody tr", has_text=codigo)
    count = await candidatos.count()
    if count == 0:
        # fallback geral caso o id da tabela mude
        candidatos = page.locator("tbody tr", has_text=codigo)
        count = await candidatos.count()
        if count == 0:
            return None

    for i in range(min(count, 10)):
        row = candidatos.nth(i)
        ws = row.locator("[data-wsid]").first
        if await ws.count() > 0:
            return row

    return candidatos.first


async def _get_wsid_from_row(row) -> Optional[str]:
    """
    Extrai o wsid de qualquer elemento da linha que tenha data-wsid.
    """
    el = row.locator("[data-wsid]").first
    if await el.count() == 0:
        return None
    return await el.get_attribute("data-wsid")


async def _set_quantidade_roles(row, wsid: str, quantidade: int) -> Dict[str, Any]:
    """
    Ajusta quantidade no Roles.
    - Primeiro tenta fill no input #qtde-{wsid} (se não for readonly)
    - Se falhar (ou readonly), usa botões +/− (bootstrap-touchspin)
    """
    quantidade = _to_int(quantidade, 1)
    if quantidade < 1:
        quantidade = 1

    qty_input = row.locator(f"#qtde-{wsid}").first
    btn_plus = row.locator(f"button.bootstrap-touchspin-up[data-wsid='{wsid}']").first
    btn_minus = row.locator(f"button.bootstrap-touchspin-down[data-wsid='{wsid}']").first

    await qty_input.wait_for(state="visible", timeout=20000)

    # valor atual
    try:
        atual = _to_int(await qty_input.input_value(), 1)
    except Exception:
        atual = 1

    # se readonly, pula fill direto
    readonly_attr = None
    try:
        readonly_attr = await qty_input.get_attribute("readonly")
    except Exception:
        readonly_attr = None

    if readonly_attr is None:
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

    # 2) modo botões (+/-)
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


async def _get_cart_count_roles(page) -> Optional[int]:
    """
    Tenta capturar um contador/badge do carrinho (se existir).
    Como não temos o HTML do topo, tenta uma lista de seletores comuns.
    Retorna int ou None se não encontrar.
    """
    seletores = [
        "#cart-count",
        ".cart-count",
        ".badge-cart",
        ".badge.badge-cart",
        "[data-cart-count]",
        ".shopping-cart .badge",
        ".btn-carrinho .badge",
        ".header-cart .badge",
        "a[href*='carrinho'] .badge",
        "a[href*='cart'] .badge",
    ]

    for sel in seletores:
        loc = page.locator(sel).first
        try:
            if await loc.count() > 0 and await loc.is_visible():
                txt = (await loc.inner_text()).strip()
                m = re.search(r"\d+", txt)
                if m:
                    return int(m.group(0))
        except Exception:
            continue

    return None


async def _esperar_confirmacao_add_roles(page, wsid: str, cart_before: Optional[int], timeout_ms: int = 12000) -> Dict[str, Any]:
    """
    Espera um sinal de que adicionou ao carrinho:
    - contador de carrinho aumenta (se existir)
    - aparece alguma mensagem/toast/alert contendo "carrinho/adicionado/incluído"
    - fallback: networkidle + delay curto
    """
    start = page.context._loop.time()  # event loop time
    timeout_s = max(1, int(timeout_ms / 1000))

    # Locators de mensagens comuns
    msg_locators = [
        page.locator("text=/adicionad|inclu[ií]d|carrinho|inclu[ií]do no carrinho/i").first,
        page.locator(".toast, .toast-message, .noty_bar, .alert, .swal2-popup, [role='alert']").first,
    ]

    for _ in range(timeout_s * 4):  # checa a cada 250ms
        # 1) contador subiu?
        cart_now = await _get_cart_count_roles(page)
        if cart_before is not None and cart_now is not None and cart_now > cart_before:
            return {"confirmacao": "cart_count_increment", "cart_before": cart_before, "cart_now": cart_now}

        # 2) apareceu mensagem?
        for ml in msg_locators:
            try:
                if await ml.count() > 0 and await ml.is_visible():
                    txt = ""
                    try:
                        txt = (await ml.inner_text()).strip()
                    except Exception:
                        txt = ""
                    if txt:
                        return {"confirmacao": "mensagem_ui", "mensagem": txt[:180]}
            except Exception:
                pass

        await asyncio.sleep(0.25)

        # evita loop infinito em ambientes estranhos
        if (page.context._loop.time() - start) > (timeout_s + 1):
            break

    # 3) fallback final: aguarda estabilizar rede
    try:
        await page.wait_for_load_state("networkidle", timeout=4000)
    except Exception:
        pass

    await asyncio.sleep(0.6)
    cart_after = await _get_cart_count_roles(page)

    return {
        "confirmacao": "fallback",
        "cart_before": cart_before,
        "cart_after": cart_after
    }


async def _selecionar_carrinho_roles(row, wsid: str, carrinho_id: str) -> bool:
    """
    Opcional: adicionar em carrinho específico do dropdown.
    Ex: div.carrinho-comprar-item[data-carrinhoid="..."]
    """
    carrinho_id = (carrinho_id or "").strip()
    if not carrinho_id:
        return False

    dropdown_btn = row.locator(f"#btn-carrinho-comprar{wsid}").first
    await dropdown_btn.wait_for(state="visible", timeout=15000)
    await dropdown_btn.click()
    await asyncio.sleep(0.3)

    item = row.locator(f".carrinho-comprar-item[data-carrinhoid='{carrinho_id}'][data-wsid='{wsid}']").first
    if await item.count() == 0:
        item = row.locator(f".carrinho-comprar-item[data-carrinhoid='{carrinho_id}']").first

    if await item.count() == 0:
        return False

    await item.click()
    await asyncio.sleep(0.8)
    return True

async def _clicar_adicionar_roles(page, row, wsid: str) -> Dict[str, Any]:
    """
    Clica no botão azul principal (ícone carrinho) que adiciona no carrinho padrão
    e aguarda ~3s (tempo observado no site).
    """
    btn_add = row.locator(f"button.btn-qtde.vit-qtde-table[data-wsid='{wsid}']").first
    await btn_add.wait_for(state="visible", timeout=20000)

    await btn_add.click()

    # o site demora ~3 segundos para efetivar
    await asyncio.sleep(3.2)

    # opcional: tenta aguardar rede estabilizar (não quebra se falhar)
    try:
        await page.wait_for_load_state("networkidle", timeout=4000)
    except Exception:
        pass

    return {
        "confirmacao": "sleep_3s"
    }


async def processar_lista_produtos_roles(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Processa lista de itens no Roles:
    item esperado:
      - codigo (str)
      - quantidade (int)
      - carrinho_id (opcional) -> se quiser adicionar no dropdown
    """
    resultados = []

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)
        carrinho_id = (item.get("carrinho_id") or "").strip()

        if not codigo:
            resultados.append({"success": False, "error": "Item sem codigo", "item": item})
            continue

        await _buscar_produto_roles(page, codigo)

        row = await _achar_linha_por_codigo(page, codigo)
        if row is None:
            resultados.append({"success": False, "error": "Produto não encontrado", "codigo": codigo})
            continue

        wsid = await _get_wsid_from_row(row)
        if not wsid:
            resultados.append({"success": False, "error": "wsid não encontrado na linha", "codigo": codigo})
            continue

        qty_info = await _set_quantidade_roles(row, wsid, quantidade)

        # Se carrinho_id informado, tenta adicionar pelo dropdown; se não, usa botão padrão
        added_dropdown = False
        confirmacao = None

        if carrinho_id:
            added_dropdown = await _selecionar_carrinho_roles(row, wsid, carrinho_id)
            if added_dropdown:
                # mesmo no dropdown, tenta aguardar confirmação (se houver contador/mensagem)
                confirmacao = await _esperar_confirmacao_add_roles(page, wsid, await _get_cart_count_roles(page), timeout_ms=9000)

        if not added_dropdown:
            confirmacao = await _clicar_adicionar_roles(page, row, wsid)

        resultados.append({
            "success": True,
            "codigo": codigo,
            "wsid": wsid,
            "quantidade": quantidade,
            "qty_info": qty_info,
            "carrinho_id": carrinho_id or None,
            "modo_add": "dropdown" if (carrinho_id and added_dropdown) else "botao_padrao",
            "confirmacao_add": confirmacao
        })

    return {"success": True, "itens": resultados}
