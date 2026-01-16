import asyncio
from typing import Dict, Any, List

# controle para fechar tutorial 1x
bloqueios_removidos = False


def log_interno(msg: str) -> None:
    print(f"   [SAMA Bot] {msg}")


def _to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return default


# ---------------------------
# 0) FECHAR TUTORIAL (1x)
# ---------------------------
async def verificar_bloqueios_unico(page) -> None:
    global bloqueios_removidos

    if bloqueios_removidos:
        return

    log_interno("Verificando bloqueios (tutorial) - primeira vez...")
    try:
        await asyncio.sleep(3)
        btn_fechar = page.locator(".driver-popover-close-btn").first
        if await btn_fechar.count() > 0 and await btn_fechar.is_visible():
            log_interno("Pop-up detectado. Fechando...")
            await btn_fechar.click(force=True)
            await asyncio.sleep(1)
            log_interno("Pop-up fechado.")
        else:
            log_interno("Nenhum pop-up/tutoriais detectados.")
    except Exception as e:
        log_interno(f"Falha ao tentar fechar tutorial: {e}")
    finally:
        bloqueios_removidos = True


# ---------------------------
# 1) BUSCA
# ---------------------------
async def buscar_produto_sama(page, codigo: str) -> None:
    selector_busca = "#search-prod"
    log_interno(f"Buscando SKU: {codigo}")

    await page.wait_for_selector(selector_busca, state="visible", timeout=20000)

    campo = page.locator(selector_busca).first
    await campo.click(force=True)
    try:
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
    except Exception:
        pass

    await campo.fill(str(codigo))
    await asyncio.sleep(0.3)

    # Enter para pesquisar
    try:
        await page.keyboard.press("Enter")
    except Exception:
        pass

    # fecha tutorial 1x (se existir)
    await verificar_bloqueios_unico(page)

    # espera pelo resultado (linha odd/even)
    try:
        await page.wait_for_selector("table tbody tr.odd, table tbody tr.even", timeout=10000)
    except Exception:
        # segue mesmo assim; a validação acontece no "achar_linha"
        pass

    await asyncio.sleep(0.6)


# ---------------------------
# 2) ACHAR LINHA DO PRODUTO
# ---------------------------
async def achar_linha_produto(page, codigo: str):
    codigo = (codigo or "").strip().upper()

    linhas = page.locator("table tbody tr.odd, table tbody tr.even")

    if await linhas.count() == 0:
        return None

    # prioridade: linha que contenha o código no texto (procedencia costuma aparecer)
    linha = linhas.filter(has_text=codigo).first
    if await linha.count() > 0:
        return linha

    # fallback: primeira linha (se o site não renderizar o código “limpo”)
    return linhas.first


# ---------------------------
# 3) SETAR QUANTIDADE
# ---------------------------
async def setar_quantidade_sama(page, linha, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 1)
    log_interno(f"Setando quantidade: {quantidade}")

    # input típico do layout (id qtde-xxxx) + classes
    qty_input = linha.locator("input.vit-qtde-table.catalogo-qtde").first

    try:
        await qty_input.wait_for(state="visible", timeout=8000)
        await qty_input.scroll_into_view_if_needed()

        await qty_input.click(force=True)

        # limpar e preencher
        try:
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
        except Exception:
            pass

        try:
            await qty_input.fill(str(quantidade))
        except Exception:
            # fallback JS (inputs “travados”)
            await qty_input.evaluate(
                """(el, v) => {
                    el.value = v;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.blur();
                }""",
                str(quantidade),
            )

        # garantir eventos
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
                "error": f"Quantidade não persistiu (final={final_val}).",
                "qtd_enviada": quantidade,
                "qtd_final": final_val,
            }

        return {"success": True, "qtd": final_int}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 4) CLICAR ADICIONAR NO CARRINHO
# ---------------------------
async def clicar_adicionar_sama(page, linha) -> Dict[str, Any]:
    log_interno("Clicando no botão adicionar ao carrinho...")

    # botão azul com ícone de carrinho (classe btn-qtde + vit-qtde-table)
    btn_add = linha.locator("button.btn-qtde.vit-qtde-table").first

    try:
        await btn_add.wait_for(state="visible", timeout=8000)
        await btn_add.scroll_into_view_if_needed()

        if await btn_add.is_disabled():
            return {"success": False, "error": "Botão adicionar está desabilitado."}

        await btn_add.click(force=True)
        await asyncio.sleep(1.2)

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 5) FUNÇÃO PRINCIPAL
# ---------------------------
async def processar_lista_produtos_sama(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    global bloqueios_removidos
    bloqueios_removidos = False

    resultados = []
    log_interno(f"Processando {len(itens)} itens (SAMA) para o carrinho...")

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip().upper()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        log_interno(f"--- SAMA: {codigo} / Qtd: {quantidade} ---")

        try:
            await buscar_produto_sama(page, codigo)

            linha = await achar_linha_produto(page, codigo)
            if not linha:
                resultados.append({"success": False, "codigo": codigo, "error": "Produto não encontrado na tabela."})
                continue

            qtd_res = await setar_quantidade_sama(page, linha, quantidade)
            if not qtd_res.get("success"):
                resultados.append({"success": False, "codigo": codigo, "quantidade": quantidade, "detalhes": qtd_res})
                continue

            add_res = await clicar_adicionar_sama(page, linha)

            resultados.append({
                "success": add_res.get("success", False),
                "codigo": codigo,
                "quantidade": quantidade,
                "detalhes": add_res,
            })

        except Exception as e:
            resultados.append({"success": False, "codigo": codigo, "error": str(e)})

    log_interno("Aguardando 3 segundos antes de encerrar...")
    await asyncio.sleep(3)

    return {"success": True, "itens": resultados}
