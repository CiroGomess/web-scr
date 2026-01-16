# controllers/addCarrinho/dpk.py
import asyncio
from typing import Dict, Any, List


def log_interno(msg: str) -> None:
    print(f"   [DPK Bot] {msg}")


def _to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return default


# ---------------------------
# 1) BUSCA (Angular)
# ---------------------------
async def buscar_produto_dpk(page, codigo: str) -> None:
    selector_busca = "input[formcontrolname='searchTerm']"
    codigo = (codigo or "").strip()

    log_interno(f"Buscando pelo código: {codigo}")

    await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
    campo = page.locator(selector_busca).first

    await campo.click(force=True)
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")

    await campo.type(str(codigo), delay=40)
    await asyncio.sleep(0.3)

    btn_buscar = page.locator("button.search-button:has-text('Buscar')").first
    if await btn_buscar.count() > 0 and await btn_buscar.is_visible():
        await btn_buscar.click(force=True)
    else:
        await page.keyboard.press("Enter")

    # dá tempo para Angular renderizar o card/área de compra
    log_interno("Pesquisa enviada. Aguardando renderização do resultado...")
    await asyncio.sleep(2.0)


# ---------------------------
# 2) ACHAR INPUT QTD (mat-input-xx muda) E BOTÃO
# ---------------------------
async def _get_qty_input(page):
    # o id muda, então pegamos por atributos estáveis
    return page.locator("input[matinput][type='number']").first


async def _get_btn_add(page):
    return page.locator("#adicionarCarrinhoBtn").first


async def aguardar_area_compra(page) -> bool:
    qty = await _get_qty_input(page)
    btn = await _get_btn_add(page)

    try:
        await qty.wait_for(state="visible", timeout=20000)
    except Exception:
        log_interno("Input de quantidade (input[matinput][type=number]) não apareceu.")
        return False

    try:
        await btn.wait_for(state="visible", timeout=20000)
    except Exception:
        log_interno("Botão #adicionarCarrinhoBtn não apareceu/ficou visível.")
        return False

    return True


# ---------------------------
# 3) SETAR QUANTIDADE (ROBUSTO PARA ANGULAR MATERIAL)
# ---------------------------
async def setar_quantidade(page, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 1)
    qty = await _get_qty_input(page)

    try:
        await qty.scroll_into_view_if_needed()
        await qty.click(force=True)

        # limpa do jeito mais confiável
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")

        # digita de verdade (melhor que fill para Angular)
        await page.keyboard.type(str(quantidade), delay=60)

        # redundância: força eventos e blur (Angular costuma "commit" no blur)
        await qty.evaluate(
            """(el) => {
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
            }"""
        )

        # confirma valor
        await asyncio.sleep(0.4)
        final_val = await qty.input_value()
        final_int = _to_int(final_val, -1)

        if final_int != quantidade:
            # tentativa 2: força via JS value + eventos
            log_interno(f"Qtd não confirmou (final={final_val}). Tentando via JS...")
            await qty.evaluate(
                """(el, v) => {
                    el.value = v;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur', { bubbles: true }));
                }""",
                str(quantidade),
            )
            await asyncio.sleep(0.4)
            final_val = await qty.input_value()
            final_int = _to_int(final_val, -1)

        if final_int != quantidade:
            return {
                "success": False,
                "error": f"Quantidade não persistiu no input. Final={final_val}, esperado={quantidade}",
                "qtd_enviada": quantidade,
                "qtd_final": final_val,
            }

        return {"success": True, "qtd": final_int}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 4) CLICAR EM ADICIONAR AO CARRINHO
# ---------------------------
async def clicar_adicionar(page) -> Dict[str, Any]:
    btn = await _get_btn_add(page)

    if await btn.count() == 0:
        return {"success": False, "error": "Botão '#adicionarCarrinhoBtn' não encontrado."}

    try:
        await btn.scroll_into_view_if_needed()
        await btn.click(force=True)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 5) FUNÇÃO PRINCIPAL (PRODUÇÃO)
# ---------------------------
async def processar_lista_produtos_dpk(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    resultados = []
    log_interno(f"Processando {len(itens)} itens (DPK) para carrinho...")

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        log_interno(f"--- DPK: {codigo} / Qtd: {quantidade} ---")

        try:
            # 1) Buscar
            await buscar_produto_dpk(page, codigo)

            # 2) Aguardar input + botão
            ok_area = await aguardar_area_compra(page)
            if not ok_area:
                resultados.append({
                    "success": False,
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "detalhes": {"success": False, "error": "Área de compra (input+botão) não carregou."},
                })
                continue

            # 3) Setar quantidade
            qtd_res = await setar_quantidade(page, quantidade)
            if not qtd_res.get("success"):
                resultados.append({
                    "success": False,
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "detalhes": qtd_res,
                })
                continue

            # 4) Espera 3s após adicionar a quantidade (como você pediu)
            log_interno("Quantidade setada. Esperando 3s antes de clicar em adicionar ao carrinho...")
            await asyncio.sleep(3)

            # 5) Clicar no botão
            add_res = await clicar_adicionar(page)

            # 6) Espera 3s após clicar no botão (como você pediu)
            log_interno("Clique no botão realizado. Esperando 3s após adicionar ao carrinho...")
            await asyncio.sleep(3)

            resultados.append({
                "success": bool(add_res.get("success")),
                "codigo": codigo,
                "quantidade": quantidade,
                "detalhes": {
                    "quantidade": qtd_res,
                    "adicionar": add_res,
                },
            })

        except Exception as e:
            resultados.append({"success": False, "codigo": codigo, "quantidade": quantidade, "error": str(e)})

    # 7) Espera 3s antes do runner fechar o browser (extra segurança)
    log_interno("Aguardando 3 segundos antes de encerrar...")
    await asyncio.sleep(3)

    return {"success": True, "itens": resultados}
