# controllers/addCarrinho/odapel.py
# Fluxo (PLS Web / Odapel) - SEM CLICAR NO "SIM"
# 1) Garantir tela /Movimentacao
# 2) Ir na aba Produtos (#tabs-2)
# 3) Buscar no input #codPeca e ENTER
# 4) Selecionar 1a linha tr.jqgrow e ENTER (abre popup)
# 5) Preencher #ultCmpQuantidade
# 6) Confirmar com ENTER (NÃO clica no botão "Sim")
# 7) Espera curta e segue

import asyncio
from typing import Dict, Any, List


def log_interno(msg: str) -> None:
    print(f"   [Odapel Bot] {msg}")


def _to_int(v, default: int = 1) -> int:
    try:
        n = int(str(v).strip())
        return n if n > 0 else default
    except Exception:
        return default


# ---------------------------
# 0) GARANTIR TELA /Movimentacao
# ---------------------------
async def garantir_tela_movimentacao(page) -> None:
    try:
        if "/Movimentacao" in (page.url or ""):
            return
    except Exception:
        pass

    # tenta via menu
    try:
        menu = page.locator("a[href='/Movimentacao']").first
        if await menu.count() > 0 and await menu.is_visible():
            log_interno("Navegando pelo menu para /Movimentacao...")
            await menu.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1.2)
            return
    except Exception:
        pass

    # fallback via URL
    try:
        log_interno("Fallback: tentando abrir /Movimentacao via goto...")
        await page.goto("/Movimentacao", wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1.2)
    except Exception:
        log_interno("Aviso: não consegui garantir /Movimentacao automaticamente.")


# ---------------------------
# 1) ATIVAR ABA PRODUTOS
# ---------------------------
async def ativar_aba_produtos(page) -> None:
    try:
        if await page.locator("#codPeca").count() > 0 and await page.locator("#codPeca").is_visible():
            return

        aba = page.locator("a[href='#tabs-2']").first
        if await aba.count() > 0 and await aba.is_visible():
            log_interno("Clicando na aba Produtos (#tabs-2)...")
            await aba.click()
            await asyncio.sleep(0.8)
    except Exception:
        pass


# ---------------------------
# 2) BUSCAR PRODUTO (ENTER)
# ---------------------------
async def buscar_produto_odapel(page, codigo: str) -> None:
    await garantir_tela_movimentacao(page)
    await ativar_aba_produtos(page)

    codigo = (codigo or "").strip()
    selector_busca = "#codPeca"

    log_interno(f"Buscando pelo código: {codigo}")

    await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
    campo = page.locator(selector_busca).first

    await campo.click(force=True)
    try:
        await campo.fill("")
    except Exception:
        pass

    await campo.fill(str(codigo))
    await asyncio.sleep(0.25)

    # ENTER para buscar
    try:
        await campo.press("Enter")
    except Exception:
        await page.keyboard.press("Enter")

    # espera grid aparecer
    try:
        await page.wait_for_selector("tr.jqgrow", state="attached", timeout=10000)
    except Exception:
        log_interno("Nenhuma linha apareceu no jqGrid (tr.jqgrow).")

    await asyncio.sleep(1.0)  # vai com calma


# ---------------------------
# 3) PEGAR PRIMEIRA LINHA DO GRID
# ---------------------------
async def pegar_primeira_linha_grid(page):
    tr = page.locator("tr.jqgrow").first
    if await tr.count() == 0:
        return None
    return tr


# ---------------------------
# 4) SELECIONAR LINHA + ENTER (abre popup)
# ---------------------------
async def abrir_popup_quantidade(page, tr) -> Dict[str, Any]:
    try:
        await tr.scroll_into_view_if_needed()
        await tr.click(force=True)
        await asyncio.sleep(0.3)

        log_interno("ENTER na linha selecionada (abrir popup)...")
        try:
            await tr.press("Enter")
        except Exception:
            await page.keyboard.press("Enter")

        await page.wait_for_selector("#ultCmpQuantidade", state="visible", timeout=12000)
        await asyncio.sleep(0.6)

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 5) SETAR QUANTIDADE (#ultCmpQuantidade)
# ---------------------------
async def setar_quantidade_popup(page, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 1)

    qty = page.locator("#ultCmpQuantidade").first
    if await qty.count() == 0:
        return {"success": False, "error": "Input #ultCmpQuantidade não encontrado no popup."}

    try:
        await qty.scroll_into_view_if_needed()
        await qty.click(force=True)

        # limpa e seta
        try:
            await qty.fill("")
        except Exception:
            pass

        await qty.fill(str(quantidade))

        # eventos (alguns fluxos precisam)
        try:
            await qty.dispatch_event("input")
            await qty.dispatch_event("change")
        except Exception:
            pass

        await asyncio.sleep(1.2)  # espera um pouco após preencher

        final_val = None
        try:
            final_val = await qty.input_value()
        except Exception:
            pass

        return {"success": True, "qtd_enviada": quantidade, "qtd_final": final_val}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 6) CONFIRMAR COM ENTER (sem clicar no "Sim")
# ---------------------------
async def confirmar_com_enter(page) -> Dict[str, Any]:
    try:
        qty = page.locator("#ultCmpQuantidade").first
        if await qty.count() > 0:
            try:
                await qty.press("Enter")
            except Exception:
                await page.keyboard.press("Enter")
        else:
            await page.keyboard.press("Enter")

        log_interno("ENTER enviado para confirmar. Aguardando 1.5s...")
        await asyncio.sleep(1.5)

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 7) FUNÇÃO PRINCIPAL (PRODUÇÃO)
# ---------------------------
async def processar_lista_produtos_odapel(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    resultados: List[Dict[str, Any]] = []
    log_interno(f"Processando {len(itens)} itens (Odapel/PLS) para carrinho...")

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        log_interno(f"--- ODP/PLS: {codigo} / Qtd: {quantidade} ---")

        try:
            # 1) Buscar
            await buscar_produto_odapel(page, codigo)

            # 2) Linha do grid
            tr = await pegar_primeira_linha_grid(page)
            if not tr:
                resultados.append({
                    "success": False,
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "error": "Nenhuma linha encontrada no jqGrid (tr.jqgrow).",
                })
                continue

            # 3) Abrir popup (ENTER)
            pop_res = await abrir_popup_quantidade(page, tr)
            if not pop_res.get("success"):
                resultados.append({
                    "success": False,
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "detalhes": {"popup": pop_res},
                })
                continue

            # 4) Setar quantidade
            qtd_res = await setar_quantidade_popup(page, quantidade)
            if not qtd_res.get("success"):
                resultados.append({
                    "success": False,
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "detalhes": {"quantidade": qtd_res},
                })
                continue

            # 5) Confirmar com ENTER (sem clicar em "Sim")
            conf_res = await confirmar_com_enter(page)
            if not conf_res.get("success"):
                resultados.append({
                    "success": False,
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "detalhes": {"quantidade": qtd_res, "confirmacao": conf_res},
                })
                continue

            # espera curta antes do próximo item
            await asyncio.sleep(0.8)

            resultados.append({
                "success": True,
                "codigo": codigo,
                "quantidade": quantidade,
                "detalhes": {
                    "popup": pop_res,
                    "quantidade": qtd_res,
                    "confirmacao_enter": conf_res,
                },
            })

        except Exception as e:
            resultados.append({
                "success": False,
                "codigo": codigo,
                "quantidade": quantidade,
                "error": str(e),
            })

    log_interno("Aguardando 2 segundos antes de encerrar...")
    await asyncio.sleep(2.0)

    return {"success": True, "itens": resultados}
