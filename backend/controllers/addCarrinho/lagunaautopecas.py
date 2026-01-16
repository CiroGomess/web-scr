import asyncio
from typing import Dict, Any, List

def log_interno(msg: str) -> None:
    print(f"   [Laguna Bot] {msg}")

def _to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return default

# ---------------------------
# 0) FECHAR BLOQUEIO (driver.js) - mesma ideia do ProdutoController6
# ---------------------------
_bloqueios_removidos = False

async def _verificar_bloqueios_unico(page) -> None:
    global _bloqueios_removidos
    if _bloqueios_removidos:
        return

    log_interno("Verificando bloqueios (tutorial/popup) pela primeira vez...")
    try:
        await asyncio.sleep(3)  # você pediu no seu controller
        btn_fechar = page.locator(".driver-popover-close-btn").first
        if await btn_fechar.count() > 0 and await btn_fechar.is_visible():
            log_interno("Pop-up detectado. Fechando...")
            await btn_fechar.click(force=True)
            await asyncio.sleep(1)
            log_interno("Pop-up fechado.")
        else:
            log_interno("Nenhum pop-up.")
    except Exception as e:
        log_interno(f"Erro ao fechar bloqueio: {e}")
    finally:
        _bloqueios_removidos = True

# ---------------------------
# 1) BUSCA
# ---------------------------
async def _buscar_produto_laguna(page, codigo: str) -> None:
    selector_busca = "#search-prod"
    log_interno(f"Iniciando busca pelo código: {codigo}")

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

    log_interno("Pressionando Enter para pesquisar...")
    try:
        await page.keyboard.press("Enter")
    except Exception:
        await campo.press("Enter")

    # fecha o bloqueio (1x)
    await _verificar_bloqueios_unico(page)

    # aguarda resultado (linha odd) ou segue
    try:
        await page.wait_for_selector("table tbody tr.odd", timeout=12000)
    except Exception:
        pass

    await asyncio.sleep(0.6)

# ---------------------------
# 2) ACHAR LINHA DO PRODUTO PELO CÓDIGO
# ---------------------------
async def _achar_linha_por_codigo(page, codigo: str):
    codigo = (codigo or "").strip()

    # melhor: procurar tr.odd que contenha o código na procedencia (ou no texto)
    tr = page.locator("table tbody tr.odd").filter(has_text=codigo).first
    if await tr.count() > 0:
        return tr

    # fallback: pega primeira linha (se a busca já filtrou)
    tr_first = page.locator("table tbody tr.odd").first
    if await tr_first.count() > 0:
        return tr_first

    return None

# ---------------------------
# 3) SET QUANTIDADE PELO WSID
# ---------------------------
async def _set_quantidade_laguna(page, tr, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 1)

    try:
        # pega WSID do input
        qty_input = tr.locator("input.catalogo-qtde[data-wsid]").first
        await qty_input.wait_for(state="visible", timeout=8000)
        await qty_input.scroll_into_view_if_needed()

        wsid = await qty_input.get_attribute("data-wsid")
        if not wsid:
            return {"success": False, "error": "WSID não encontrado no input de quantidade."}

        # tenta preencher
        await qty_input.click(force=True)

        # alguns inputs são "type=text", então fill funciona; mas pode precisar de eventos
        await qty_input.fill(str(quantidade))
        try:
            await qty_input.dispatch_event("input")
            await qty_input.dispatch_event("change")
            await qty_input.evaluate("el => el.blur()")
        except Exception:
            pass

        await asyncio.sleep(0.25)

        # valida se persistiu
        final_val = await qty_input.input_value()
        final_int = _to_int(final_val, -1)

        if final_int != quantidade:
            # fallback JS
            log_interno(f"Quantidade não persistiu (atual={final_val}). Forçando via JS...")
            await qty_input.evaluate(
                """(el, v) => {
                    el.value = v;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.blur();
                }""",
                str(quantidade),
            )
            await asyncio.sleep(0.25)
            final_val = await qty_input.input_value()
            final_int = _to_int(final_val, -1)

        if final_int != quantidade:
            return {
                "success": False,
                "error": f"Não consegui setar a quantidade. Final={final_val}",
                "wsid": wsid,
            }

        return {"success": True, "qtd": final_int, "wsid": wsid}

    except Exception as e:
        return {"success": False, "error": str(e)}

# ---------------------------
# 4) CLICAR ADICIONAR AO CARRINHO (BOTÃO btn-qtde COM MESMO WSID)
# ---------------------------
async def _clicar_add_carrinho_laguna(page, tr, wsid: str) -> Dict[str, Any]:
    try:
        btn_add = tr.locator(f"button.btn-qtde[data-wsid='{wsid}']").first
        await btn_add.wait_for(state="visible", timeout=8000)
        await btn_add.scroll_into_view_if_needed()

        if await btn_add.is_disabled():
            return {"success": False, "error": "Botão adicionar está desabilitado.", "wsid": wsid}

        log_interno("Clicando no botão de adicionar ao carrinho...")
        await btn_add.click(force=True)

        # aguarda feedback mínimo (site pode async)
        await asyncio.sleep(1.2)

        return {"success": True, "wsid": wsid}

    except Exception as e:
        return {"success": False, "error": str(e), "wsid": wsid}

# ---------------------------
# 5) FUNÇÃO PRINCIPAL
# ---------------------------
async def processar_lista_produtos_laguna(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    global _bloqueios_removidos
    _bloqueios_removidos = False  # reseta por execução

    resultados = []
    log_interno(f"Processando {len(itens)} itens (Laguna) para o carrinho...")

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        log_interno(f"--- Laguna: {codigo} / Qtd: {quantidade} ---")

        try:
            await _buscar_produto_laguna(page, codigo)

            tr = await _achar_linha_por_codigo(page, codigo)
            if not tr:
                resultados.append({"success": False, "codigo": codigo, "error": "Produto não encontrado na tabela."})
                continue

            qtd_res = await _set_quantidade_laguna(page, tr, quantidade)
            if not qtd_res.get("success"):
                resultados.append({"success": False, "codigo": codigo, "error": qtd_res.get("error", "Erro ao setar quantidade"), "detalhes": qtd_res})
                continue

            wsid = qtd_res.get("wsid")
            add_res = await _clicar_add_carrinho_laguna(page, tr, wsid)

            resultados.append({
                "success": add_res.get("success", False),
                "codigo": codigo,
                "quantidade": quantidade,
                "detalhes": {
                    "quantidade": qtd_res,
                    "adicionar": add_res,
                },
            })

        except Exception as e:
            resultados.append({"success": False, "codigo": codigo, "error": str(e)})

    log_interno("Aguardando 3 segundos antes de encerrar...")
    await asyncio.sleep(3)

    return {"success": True, "itens": resultados}
