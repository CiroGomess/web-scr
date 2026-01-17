# controllers/addCarrinho/furacao.py
import asyncio
from typing import Dict, Any, List


def log_interno(msg: str) -> None:
    print(f"   [Furacao Bot] {msg}")


def _to_int(v, default: int = 1) -> int:
    try:
        n = int(str(v).strip())
        return n if n > 0 else default
    except Exception:
        return default


# ---------------------------
# 0) GARANTIR TELA DE PESQUISA (onde existe input#gsearch)
# ---------------------------
async def garantir_tela_pesquisa_furacao(page) -> None:
    selector_busca = "input#gsearch"
    try:
        await page.wait_for_selector(selector_busca, state="visible", timeout=15000)
        return
    except Exception:
        pass

    possiveis_urls = [
        "https://vendas.furacao.com.br/",
        "https://vendas.furacao.com.br/#/",
        "https://vendas.furacao.com.br/#/produtos",
    ]

    for url in possiveis_urls:
        try:
            log_interno(f"Tentando abrir tela de pesquisa: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(1.0)
            if await page.locator(selector_busca).count() > 0:
                await page.wait_for_selector(selector_busca, state="visible", timeout=15000)
                return
        except Exception:
            continue

    log_interno("Aviso: não consegui garantir a tela de pesquisa automaticamente.")


# ---------------------------
# 1) BUSCA
# ---------------------------
async def buscar_produto_furacao(page, codigo: str) -> None:
    await garantir_tela_pesquisa_furacao(page)

    selector_busca = "input#gsearch"
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
    await asyncio.sleep(0.3)

    try:
        await campo.press("Enter")
    except Exception:
        await page.keyboard.press("Enter")

    # Espera aparecer pelo menos uma linha de resultado
    try:
        await page.wait_for_selector("tr[ng-controller='RowCtrl']", state="attached", timeout=15000)
    except Exception:
        log_interno("Nenhum resultado apareceu (tr[RowCtrl] não carregou).")

    # "vai com calma"
    await asyncio.sleep(2.0)


# ---------------------------
# 2) NO RESULTADO: PEGAR PRIMEIRO ROW DO GRID
# ---------------------------
async def pegar_primeiro_row_resultado(page):
    row = page.locator("tr[ng-controller='RowCtrl']").first
    if await row.count() == 0:
        return None
    return row


# ---------------------------
# 3) SETAR QUANTIDADE (input ng-model="$row.quantidade")
# ---------------------------
async def setar_quantidade_no_row(row, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 1)

    qty_input = row.locator('input[ng-model="$row.quantidade"]').first
    if await qty_input.count() == 0:
        # fallback por classes (caso ng-model mude)
        qty_input = row.locator("input.prod-input").first

    if await qty_input.count() == 0:
        return {"success": False, "error": "Input de quantidade não encontrado no row."}

    try:
        await qty_input.scroll_into_view_if_needed()
        await qty_input.click(force=True)

        # Primeiro tenta fill normal
        try:
            await qty_input.fill(str(quantidade))
        except Exception:
            # fallback via JS (Angular às vezes precisa)
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

        log_interno(f"Quantidade setada para {quantidade}. Aguardando 3 segundos...")
        await asyncio.sleep(3.0)

        # valida leitura
        final_val = None
        try:
            final_val = await qty_input.input_value()
        except Exception:
            pass

        return {"success": True, "qtd_enviada": quantidade, "qtd_final": final_val}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 4) CLICAR NO BOTÃO COMPRAR/ADICIONAR (no próprio row)
# ---------------------------
async def clicar_comprar_no_row(row) -> Dict[str, Any]:
    # Seu botão:
    # <button type="submit" class="btn btn-default" ...>
    #   <span ...> Adicionar </span>
    #   <span ...> <strong>Comprar</strong> </span>
    # </button>

    # 1) tenta pelo type submit dentro do row
    btn = row.locator("button[type='submit']").first

    # 2) fallback por texto "Comprar" ou "Adicionar"
    if await btn.count() == 0:
        btn = row.locator("button:has-text('Comprar')").first
    if await btn.count() == 0:
        btn = row.locator("button:has-text('Adicionar')").first

    if await btn.count() == 0:
        return {"success": False, "error": "Botão Comprar/Adicionar não encontrado no row."}

    try:
        await btn.scroll_into_view_if_needed()
        log_interno("Clicando no botão Comprar/Adicionar...")
        await btn.click(force=True)

        # espera “com calma” após clicar
        log_interno("Aguardando 3 segundos após clicar no botão...")
        await asyncio.sleep(3.0)

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 5) FUNÇÃO PRINCIPAL (PRODUÇÃO)
# ---------------------------
async def processar_lista_produtos_furacao(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    resultados = []
    log_interno(f"Processando {len(itens)} itens (Furacão) para carrinho...")

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        log_interno(f"--- FURAÇÃO: {codigo} / Qtd: {quantidade} ---")

        try:
            # 1) Buscar
            await buscar_produto_furacao(page, codigo)

            # 2) Primeiro row
            row = await pegar_primeiro_row_resultado(page)
            if not row:
                resultados.append({"success": False, "codigo": codigo, "quantidade": quantidade, "error": "Nenhum resultado encontrado."})
                continue

            # 3) Setar quantidade
            qtd_res = await setar_quantidade_no_row(row, quantidade)
            if not qtd_res.get("success"):
                resultados.append({"success": False, "codigo": codigo, "quantidade": quantidade, "detalhes": qtd_res})
                continue

            # 4) Clicar Comprar/Adicionar
            click_res = await clicar_comprar_no_row(row)
            if not click_res.get("success"):
                resultados.append({"success": False, "codigo": codigo, "quantidade": quantidade, "detalhes": click_res})
                continue

            resultados.append({
                "success": True,
                "codigo": codigo,
                "quantidade": quantidade,
                "detalhes": {
                    "quantidade": qtd_res,
                    "click": click_res,
                }
            })

        except Exception as e:
            resultados.append({"success": False, "codigo": codigo, "quantidade": quantidade, "error": str(e)})

    log_interno("Aguardando 3 segundos antes de encerrar...")
    await asyncio.sleep(3.0)

    return {"success": True, "itens": resultados}
