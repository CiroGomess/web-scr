# controllers/addCarrinho/skypecas.py
import asyncio
from typing import Dict, Any, List, Optional


def _to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return default


async def _buscar_produto_skypecas(page, codigo: str) -> None:
    codigo = (codigo or "").strip()
    if not codigo:
        return

    inp = page.locator("#inpCodigo").first
    await inp.wait_for(state="visible", timeout=20000)

    await inp.click()
    await inp.fill("")
    await inp.fill(codigo)

    # Em muitos layouts o "enter" dispara a busca
    await inp.press("Enter")

    # aguarda render do resultado
    await asyncio.sleep(1.2)


async def _achar_card_por_codigo(page, codigo: str):
    """
    Resultado típico:
      <div class="bx_produto"> ... <div class="codfab">Cód. Fáb: <strong>82696FLEX</strong> ...
    O "codigo" do front pode ser:
      - Cód. Fáb (strong)
      - N/N (div.codnn)
    """
    codigo = (codigo or "").strip()
    if not codigo:
        return None

    await page.wait_for_selector(".bx_produto", timeout=20000)

    # 1) tenta pelo Cód. Fáb
    card = page.locator(".bx_produto", has=page.locator(".codfab strong", has_text=codigo)).first
    if await card.count() > 0:
        return card

    # 2) tenta pelo N/N
    card = page.locator(".bx_produto", has=page.locator(".codnn", has_text=codigo)).first
    if await card.count() > 0:
        return card

    # 3) fallback: qualquer card que contenha o texto (menos preciso)
    card = page.locator(".bx_produto", has_text=codigo).first
    if await card.count() > 0:
        return card

    return None


async def _extrair_nn_do_card(card) -> Optional[str]:
    """
    No HTML:
      <div class="fleft codnn">N/N: 270942J</div>
    """
    el = card.locator(".codnn").first
    if await el.count() == 0:
        return None

    txt = (await el.inner_text()) or ""
    txt = txt.replace("\n", " ").strip()
    # espera "N/N: 270942J"
    if ":" in txt:
        return txt.split(":", 1)[1].strip() or None
    return txt.strip() or None


async def _tentar_setar_quantidade_no_card(card, quantidade: int) -> Dict[str, Any]:
    """
    Nem sempre existe input de quantidade no card.
    Se existir, tentamos setar. Se não existir, retornamos modo "click_repeat".
    """
    quantidade = _to_int(quantidade, 1)
    if quantidade < 1:
        quantidade = 1

    # heurísticas comuns
    possiveis = [
        "input[name='quantidade']",
        "input[name='qtde']",
        "input[name='qtd']",
        "input[id*='qtd']",
        "input[id*='qtde']",
        "input[class*='qtd']",
        "input[class*='qtde']",
    ]

    for sel in possiveis:
        ipt = card.locator(sel).first
        if await ipt.count() == 0:
            continue
        try:
            await ipt.wait_for(state="visible", timeout=1500)
            await ipt.click()
            await ipt.fill(str(quantidade))
            await ipt.press("Tab")
            await asyncio.sleep(0.2)
            return {
                "modo": "fill",
                "seletor": sel,
                "quantidade_solicitada": quantidade,
            }
        except Exception:
            continue

    return {
        "modo": "click_repeat",
        "quantidade_solicitada": quantidade,
    }


async def _clicar_adicionar(card, nn: Optional[str] = None) -> None:
    """
    Botão:
      <a href="" id="lkAdd270942J" class="lkAdicionar lkBotao">+ Adicionar no Carrinho</a>
    """
    btn = None
    if nn:
        btn = card.locator(f"#lkAdd{nn}").first
        if await btn.count() == 0:
            btn = None

    if btn is None:
        btn = card.locator("a.lkAdicionar.lkBotao").first

    await btn.wait_for(state="visible", timeout=20000)
    await btn.click()

    # você informou ~3 segundos de processamento após clicar
    await asyncio.sleep(3.0)


async def processar_lista_produtos_skypecas(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Espera itens no formato:
      [{"codigo":"82696FLEX","quantidade":2}]
    ou
      [{"codigo":"270942J","quantidade":2}]
    """
    resultados: List[Dict[str, Any]] = []

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        if not codigo:
            resultados.append({"success": False, "error": "Item sem codigo", "item": item})
            continue

        await _buscar_produto_skypecas(page, codigo)

        card = await _achar_card_por_codigo(page, codigo)
        if card is None:
            resultados.append({"success": False, "error": "Produto não encontrado", "codigo": codigo})
            continue

        nn = await _extrair_nn_do_card(card)

        qty_info = await _tentar_setar_quantidade_no_card(card, quantidade)

        # Se não tem input de quantidade, repetimos o clique (1 clique = +1 unidade)
        if qty_info.get("modo") == "click_repeat":
            max_clicks = min(max(quantidade, 1), 50)
            for i in range(max_clicks):
                await _clicar_adicionar(card, nn=nn)
        else:
            # se conseguiu setar a quantidade em input, clica uma vez para adicionar
            await _clicar_adicionar(card, nn=nn)

        resultados.append({
            "success": True,
            "codigo": codigo,
            "nn": nn,
            "quantidade": quantidade,
            "qty_info": qty_info,
        })

    return {"success": True, "itens": resultados}
