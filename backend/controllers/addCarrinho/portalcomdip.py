# controllers/addCarrinho/portalcomdip.py
import asyncio
import re
from typing import List, Dict, Any, Optional

# Reaproveita sua busca já validada
from controllers.produtos.produtoController1 import buscar_produto

PESQUISA_URL = "https://www.portalcomdip.com.br/comdip/compras/pesquisa"


def _only_digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


async def _selecionar_uf_no_card(card, uf: str) -> bool:
    """
    Seleciona a UF dentro do card (se existir lista de UFs).
    Retorna True se conseguiu selecionar, False caso não tenha ou não achou a UF.
    """
    if not uf:
        return False

    uf = uf.strip().upper()
    lista_li = card.locator(".card-preco ul.precos li")
    total = await lista_li.count()
    if total <= 0:
        return False

    for i in range(total):
        li = lista_li.nth(i)
        span = li.locator("span.text-muted.small")
        if await span.count() > 0:
            txt = (await span.inner_text()).strip().upper()
            if txt == uf:
                await li.click()
                await asyncio.sleep(0.25)
                return True

    return False


async def _set_quantidade_no_card(card, quantidade: int) -> Dict[str, Any]:
    """
    Ajusta a quantidade do produto no card.
    Estratégia:
      1) tenta fill direto no input
      2) valida se ficou correto
      3) se não ficou, faz fallback clicando + / -
    """
    quantidade = int(quantidade or 1)
    if quantidade < 1:
        quantidade = 1

    qtd_input = card.locator("input[aria-label='Quantidade do produto']")
    plus_btn = card.locator("button[aria-label='Aumentar quantidade do produto']")
    minus_btn = card.locator("button[aria-label='Reduzir quantidade do produto']")

    # Garante que o input existe
    await qtd_input.wait_for(state="visible", timeout=15000)

    # 1) Tenta setar direto no input
    try:
        await qtd_input.click()
        await qtd_input.fill(str(quantidade))
        # força eventos de blur/commit (Angular costuma precisar)
        await qtd_input.press("Tab")
        await asyncio.sleep(0.2)
    except Exception:
        pass

    # 2) Confere valor
    atual_str = ""
    try:
        atual_str = await qtd_input.input_value()
    except Exception:
        atual_str = ""

    atual = int(_only_digits(atual_str) or "1")

    # 3) Fallback: ajusta via botões
    tentativas_max = 60
    tent = 0

    while atual != quantidade and tent < tentativas_max:
        tent += 1

        if atual < quantidade:
            await plus_btn.click()
        else:
            await minus_btn.click()

        await asyncio.sleep(0.12)

        try:
            atual_str = await qtd_input.input_value()
            atual = int(_only_digits(atual_str) or str(atual))
        except Exception:
            # se não conseguir ler, assume que avançou 1 (melhor esforço)
            atual = atual + 1 if atual < quantidade else max(1, atual - 1)

    return {
        "quantidade_solicitada": quantidade,
        "quantidade_no_input": atual,
        "ok": (atual == quantidade),
        "tentativas": tent
    }


async def _clicar_adicionar_carrinho(card, page) -> Dict[str, Any]:
    """
    Clica no botão 'Adicionar ao carrinho' e tenta capturar algum feedback visual.
    """
    btn_add = card.locator("button[aria-label='Adicionar ao carrinho']").first
    await btn_add.wait_for(state="visible", timeout=15000)

    # tenta limpar alertas anteriores (se existirem)
    try:
        await page.evaluate("document.querySelectorAll('div.alert').forEach(el => el.remove());")
    except Exception:
        pass

    await btn_add.click()

    # tenta capturar mensagem de retorno (site usa alerts em alguns fluxos)
    msg = None
    try:
        alert = page.locator("div.alert").first
        await alert.wait_for(state="visible", timeout=5000)
        msg = (await alert.inner_text()).strip()
    except Exception:
        msg = None

    return {"mensagem": msg}


async def adicionar_itens_ao_carrinho_portalcomdip(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Para cada item:
      - busca por código
      - (opcional) seleciona UF se vier no payload
      - ajusta quantidade
      - adiciona ao carrinho
    """
    resultados = []

    for item in itens:
        codigo = str(item.get("codigo") or "").strip()
        quantidade = int(item.get("quantidade") or 1)
        uf = (item.get("uf") or "").strip().upper()  # opcional

        if not codigo:
            resultados.append({
                "codigo": None,
                "success": False,
                "error": "Item sem código.",
                "payload": item
            })
            continue

        try:
            # Vai para página de pesquisa
            await page.goto(PESQUISA_URL, wait_until="networkidle", timeout=30000)

            # Busca produto (reaproveita seu método)
            await buscar_produto(page, codigo, quantidade)

            # Aguarda card aparecer
            card_locator = page.locator("isthmus-produto-b2b-card")
            await card_locator.first.wait_for(timeout=15000)
            card = card_locator.first

            # Opcional: valida se o card retornado contém o código
            try:
                title = await card.locator(".card-imagem a").get_attribute("title")
                if title and codigo not in title:
                    # Não aborta automaticamente, mas registra warning
                    warning = f"Card encontrado, porém title não contém o código {codigo}."
                else:
                    warning = None
            except Exception:
                warning = None

            # Seleciona UF (se vier)
            uf_ok = False
            if uf:
                uf_ok = await _selecionar_uf_no_card(card, uf)

            # Ajusta quantidade
            qtd_info = await _set_quantidade_no_card(card, quantidade)

            # Adiciona ao carrinho
            add_info = await _clicar_adicionar_carrinho(card, page)

            resultados.append({
                "codigo": codigo,
                "uf_solicitada": uf or None,
                "uf_selecionada": uf_ok if uf else None,
                "quantidade": qtd_info,
                "carrinho": add_info,
                "warning": warning,
                "success": True
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
