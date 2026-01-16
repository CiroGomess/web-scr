# controllers/addCarrinho/suportematriz.py
import asyncio
from typing import Dict, Any, List


def log_interno(msg: str) -> None:
    print(f"   [Matriz Bot] {msg}")


def _to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return default


# ---------------------------
# 0) GARANTIR TELA (onde existe input#codigo)
# ---------------------------
async def garantir_tela_busca_matriz(page) -> None:
    selector_busca = "input#codigo"

    try:
        await page.wait_for_selector(selector_busca, state="visible", timeout=8000)
        return
    except Exception:
        pass

    possiveis_urls = [
        "http://suportematriz.ddns.net:5006/",
        "http://suportematriz.ddns.net:5006/pedido",
        "http://suportematriz.ddns.net:5006/pedido/index",
    ]

    for url in possiveis_urls:
        try:
            log_interno(f"Tentando abrir tela de busca: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(1.0)
            if await page.locator(selector_busca).count() > 0:
                await page.wait_for_selector(selector_busca, state="visible", timeout=8000)
                return
        except Exception:
            continue

    log_interno("Aviso: não consegui garantir a tela de busca automaticamente.")


# ---------------------------
# 1) BUSCAR PRODUTO (input#codigo + Enter)
# ---------------------------
async def buscar_produto_matriz(page, codigo: str) -> None:
    await garantir_tela_busca_matriz(page)

    codigo = (codigo or "").strip()
    selector_busca = "input#codigo"

    log_interno(f"Buscando produto: {codigo}")

    await page.wait_for_selector(selector_busca, state="visible", timeout=20000)

    campo = page.locator(selector_busca).first
    await campo.click(force=True)

    try:
        await campo.fill("")
    except Exception:
        pass

    await campo.fill(codigo)
    await asyncio.sleep(0.2)

    try:
        await campo.press("Enter")
    except Exception:
        await page.keyboard.press("Enter")

    # Aguarda aparecer card
    try:
        await page.wait_for_selector(".product-card-modern-pedido", state="attached", timeout=10000)
    except Exception:
        log_interno("Nenhum card apareceu após a busca (pode ser não encontrado).")

    await asyncio.sleep(0.6)


# ---------------------------
# 2) ACHAR CARD PELO CÓDIGO (preferindo data-produto do botão add-to-cart)
# ---------------------------
async def achar_card_por_codigo(page, codigo: str):
    codigo = (codigo or "").strip().upper()

    cards = page.locator(".product-card-modern-pedido")
    total = await cards.count()
    if total == 0:
        return None

    # Primeiro: tenta pelo atributo data-produto do botão (mais confiável)
    for i in range(total):
        card = cards.nth(i)
        btn = card.locator("button.add-to-cart").first
        if await btn.count() == 0:
            continue

        data_produto = await btn.get_attribute("data-produto")
        if data_produto and data_produto.strip().upper() == codigo:
            return card

    # Fallback: tenta achar o código no texto do card
    card_by_text = cards.filter(has_text=codigo).first
    if await card_by_text.count() > 0:
        return card_by_text

    return None


# ---------------------------
# 3) CLICAR NO BOTÃO "Adicionar ao Carrinho" DO CARD
# ---------------------------
async def clicar_add_to_cart_no_card(card) -> bool:
    btn = card.locator("button.add-to-cart").first
    if await btn.count() == 0:
        return False

    try:
        await btn.scroll_into_view_if_needed()
        await btn.click(force=True)
        return True
    except Exception:
        return False


# ---------------------------
# 4) NO MODAL: SETAR QUANTIDADE E CONFIRMAR
# ---------------------------
async def setar_quantidade_e_confirmar(page, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 1)

    qty_selector = "#quantidade-input"
    confirm_selector = "button#confirmar-quantidade"

    try:
        await page.wait_for_selector(qty_selector, state="visible", timeout=12000)
    except Exception:
        return {"success": False, "error": "Modal de quantidade não apareceu (#quantidade-input não ficou visível)"}

    qty_input = page.locator(qty_selector).first

    # Se existir min="6", garantir respeitar
    try:
        min_attr = await qty_input.get_attribute("min")
        min_val = _to_int(min_attr, 0)
        if min_val and quantidade < min_val:
            log_interno(f"Quantidade solicitada ({quantidade}) menor que min ({min_val}). Ajustando para {min_val}.")
            quantidade = min_val
    except Exception:
        pass

    # Preencher quantidade
    try:
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
    except Exception as e:
        return {"success": False, "error": f"Falha ao setar quantidade: {e}"}

    await asyncio.sleep(0.2)

    # Confirmar
    btn_confirm = page.locator(confirm_selector).first
    if await btn_confirm.count() == 0:
        return {"success": False, "error": "Botão de confirmar não encontrado (#confirmar-quantidade)"}

    try:
        log_interno(f"Confirmando quantidade no modal: {quantidade}")
        await btn_confirm.click(force=True)
    except Exception as e:
        return {"success": False, "error": f"Falha ao clicar em confirmar: {e}"}

    await asyncio.sleep(0.8)

    # Valida valor final do input (quando o modal não fecha, ainda dá pra ler)
    try:
        final_val = await qty_input.input_value()
        final_int = _to_int(final_val, -1)
        if final_int != quantidade:
            return {
                "success": False,
                "error": f"Quantidade não persistiu no input do modal. Final={final_val}, esperado={quantidade}",
                "qtd_enviada": quantidade,
                "qtd_final": final_val,
            }
        return {"success": True, "qtd": final_int}
    except Exception:
        # se o modal fechou rápido, assume sucesso
        return {"success": True, "qtd": quantidade, "info": "Modal fechou antes de validar input; assumindo OK."}


# ---------------------------
# 5) FUNÇÃO PRINCIPAL (PRODUÇÃO)
# ---------------------------
async def processar_lista_produtos_suportematriz(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    resultados = []
    log_interno(f"Processando {len(itens)} itens (Suporte Matriz) para carrinho...")

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        log_interno(f"--- MATRIZ: {codigo} / Qtd: {quantidade} ---")

        try:
            # 1) Buscar
            await buscar_produto_matriz(page, codigo)

            # 2) Achar card do produto
            card = await achar_card_por_codigo(page, codigo)
            if not card:
                resultados.append({"success": False, "codigo": codigo, "error": "Produto não encontrado (card não localizado)"})
                continue

            # 3) Clicar no botão do card
            ok_click = await clicar_add_to_cart_no_card(card)
            if not ok_click:
                resultados.append({"success": False, "codigo": codigo, "error": "Botão add-to-cart não clicável no card"})
                continue

            # 4) Modal: setar qtd e confirmar
            qtd_res = await setar_quantidade_e_confirmar(page, quantidade)

            resultados.append({
                "success": bool(qtd_res.get("success")),
                "codigo": codigo,
                "quantidade": quantidade,
                "detalhes": qtd_res,
            })

        except Exception as e:
            resultados.append({"success": False, "codigo": codigo, "error": str(e)})

    # Espera 3 segundos antes do runner fechar o browser
    log_interno("Aguardando 3 segundos antes de encerrar...")
    await asyncio.sleep(3)

    return {"success": True, "itens": resultados}
