# controllers/addCarrinho/solroom.py
import asyncio
from typing import Dict, Any, List


def log_interno(msg: str) -> None:
    print(f"   [Solroom Bot] {msg}")


def _to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return default


# ---------------------------
# 0) GARANTIR TELA DE PESQUISA (onde existe input#pesquisa)
# ---------------------------
async def garantir_tela_pesquisa_solroom(page) -> None:
    selector_busca = "input#pesquisa"

    # se já está na tela certa
    try:
        if await page.locator(selector_busca).count() > 0:
            await page.wait_for_selector(selector_busca, state="visible", timeout=8000)
            return
    except Exception:
        pass

    # fallbacks
    possiveis_urls = [
        "https://solroom.com.br/produto",
        "https://solroom.com.br/produto/index",
        "https://solroom.com.br/produtos",
        "https://solroom.com.br/",
    ]

    for url in possiveis_urls:
        try:
            log_interno(f"Tentando abrir tela de pesquisa: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(1.0)
            if await page.locator(selector_busca).count() > 0:
                await page.wait_for_selector(selector_busca, state="visible", timeout=8000)
                return
        except Exception:
            continue

    log_interno("Aviso: não consegui garantir a tela de pesquisa automaticamente.")


# ---------------------------
# 1) BUSCA (preenche input#pesquisa e ENTER)
# ---------------------------
async def buscar_produto_solroom(page, codigo: str) -> None:
    await garantir_tela_pesquisa_solroom(page)

    selector_busca = "input#pesquisa"
    codigo = (codigo or "").strip()

    log_interno(f"Buscando pelo código: {codigo}")

    await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
    campo = page.locator(selector_busca).first

    await campo.click(force=True)
    try:
        await campo.fill("")
    except Exception:
        pass

    await campo.fill(str(codigo))
    await asyncio.sleep(0.2)

    try:
        await campo.press("Enter")
    except Exception:
        await page.keyboard.press("Enter")

    # aguarda cards aparecerem
    try:
        await page.wait_for_selector("div.card", state="attached", timeout=12000)
    except Exception:
        log_interno("Nenhum resultado apareceu após a busca (div.card não carregou).")
        return

    await asyncio.sleep(0.6)


# ---------------------------
# 2) NA LISTAGEM: CLICAR DIRETO NO "COMPRAR" DO CARD DO CÓDIGO
# ---------------------------
async def clicar_comprar_no_card(page, codigo: str) -> bool:
    codigo = (codigo or "").strip()

    # card que contém o texto "3250237 - ..."
    card = page.locator("div.card").filter(has_text=codigo).first
    if await card.count() == 0:
        log_interno(f"Card não encontrado para o código {codigo}.")
        return False

    # botão comprar dentro do card
    btn = card.locator("a.btn.btn-primary[href^='/pedido/carrinho/']").first
    if await btn.count() == 0:
        # fallback: qualquer link /pedido/carrinho/ dentro do card
        btn = card.locator("a[href^='/pedido/carrinho/']").filter(has_text="Comprar").first

    if await btn.count() == 0:
        log_interno(f"Botão Comprar não encontrado dentro do card do código {codigo}.")
        return False

    try:
        await btn.scroll_into_view_if_needed()
    except Exception:
        pass

    log_interno("Clicando em Comprar (no card) para ir ao carrinho...")

    # aguarda navegação para /pedido/carrinho/
    try:
        async with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
            await btn.click(force=True)
    except Exception:
        # fallback: click + wait_for_url
        try:
            await btn.click(force=True)
            await page.wait_for_url("**/pedido/carrinho/**", timeout=15000)
        except Exception as e:
            log_interno(f"Falha ao navegar para carrinho: {e}")
            return False

    # aguarda tabela do carrinho
    try:
        await page.wait_for_selector("tbody.list tr", state="attached", timeout=15000)
    except Exception:
        log_interno("Carrinho abriu, mas tbody.list tr não apareceu.")
        return False

    await asyncio.sleep(0.6)
    return True


# ---------------------------
# 3) NO CARRINHO: ACHAR TR PELO CÓDIGO E SETAR QUANTIDADE + ATUALIZAR
# ---------------------------
async def setar_quantidade_no_carrinho(page, codigo: str, quantidade: int) -> Dict[str, Any]:
    codigo = (codigo or "").strip()
    quantidade = _to_int(quantidade, 1)

    tbody = page.locator("tbody.list").first
    if await tbody.count() == 0:
        return {"success": False, "error": "tbody.list não encontrado no carrinho"}

    row = page.locator("tbody.list tr").filter(has_text=codigo).first
    if await row.count() == 0:
        return {"success": False, "error": f"TR do carrinho não encontrado para o código {codigo}"}

    qty_input = row.locator("input.quantidade").first
    if await qty_input.count() == 0:
        return {"success": False, "error": "Input de quantidade (.quantidade) não encontrado na linha do carrinho"}

    btn_update = row.locator("button[onclick*='SetQuantidade']").first
    if await btn_update.count() == 0:
        return {"success": False, "error": "Botão de atualizar quantidade (SetQuantidade) não encontrado na linha"}

    try:
        await qty_input.scroll_into_view_if_needed()
        await qty_input.click(force=True)

        # setar valor
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

        # redundância de eventos
        try:
            await qty_input.dispatch_event("input")
            await qty_input.dispatch_event("change")
        except Exception:
            pass

        await asyncio.sleep(0.2)

        # clicar no atualizar
        log_interno(f"Atualizando quantidade para {quantidade} (código {codigo})...")
        try:
            async with page.expect_navigation(wait_until="domcontentloaded", timeout=8000):
                await btn_update.click(force=True)
        except Exception:
            await btn_update.click(force=True)

        await asyncio.sleep(0.8)

        # re-localiza (re-render)
        row2 = page.locator("tbody.list tr").filter(has_text=codigo).first
        qty_input2 = row2.locator("input.quantidade").first

        final_val = await qty_input2.input_value()
        final_int = _to_int(final_val, -1)

        if final_int != quantidade:
            return {
                "success": False,
                "error": f"Quantidade não persistiu no carrinho. Final={final_val}, esperado={quantidade}",
                "qtd_enviada": quantidade,
                "qtd_final": final_val,
            }

        return {"success": True, "qtd": final_int}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 4) FUNÇÃO PRINCIPAL (PRODUÇÃO)
# ---------------------------
async def processar_lista_produtos_solroom(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    resultados = []

    log_interno(f"Processando {len(itens)} itens (Solroom) para carrinho...")

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        log_interno(f"--- SOLROOM: {codigo} / Qtd: {quantidade} ---")

        try:
            # 1) Buscar
            await buscar_produto_solroom(page, codigo)

            # 2) Comprar direto no card (vai pro carrinho)
            ok = await clicar_comprar_no_card(page, codigo)
            if not ok:
                resultados.append({"success": False, "codigo": codigo, "error": "Falha ao clicar Comprar no card ou carrinho não carregou"})
                # tenta voltar pra pesquisa para o próximo item
                await garantir_tela_pesquisa_solroom(page)
                continue

            # 3) No carrinho, setar quantidade
            qtd_res = await setar_quantidade_no_carrinho(page, codigo, quantidade)

            resultados.append({
                "success": bool(qtd_res.get("success")),
                "codigo": codigo,
                "quantidade": quantidade,
                "detalhes": qtd_res,
            })

            # 4) Volta pra pesquisa para processar próximos itens
            await garantir_tela_pesquisa_solroom(page)

        except Exception as e:
            resultados.append({"success": False, "codigo": codigo, "error": str(e)})
            try:
                await garantir_tela_pesquisa_solroom(page)
            except Exception:
                pass

        await asyncio.sleep(0.6)

    success_geral = all(bool(r.get("success")) for r in resultados) if resultados else True

    log_interno("Aguardando 2 segundos antes de encerrar...")
    await asyncio.sleep(2)

    return {"success": success_geral, "itens": resultados}
