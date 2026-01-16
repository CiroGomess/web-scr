
# controllers/addCarrinho/takao.py
import asyncio
from typing import Dict, Any, List


def log_interno(msg: str) -> None:
    print(f"   [Takao Bot] {msg}")


def _to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return default


# ---------------------------
# 0) GARANTIR TELA DE PESQUISA
# ---------------------------
async def garantir_tela_pesquisa_takao(page) -> None:
    selector_busca = "input#inputSearch"

    try:
        await page.wait_for_selector(selector_busca, state="visible", timeout=8000)
        return
    except Exception:
        pass

    possiveis_urls = [
        # ajuste se você tiver uma URL específica pós-login
        "https://www.takao.com.br/",
        "https://www.takao.com.br/home",
        "https://www.takao.com.br/produtos",
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
# 1) BUSCA
# ---------------------------
async def buscar_produto_takao(page, codigo: str) -> None:
    await garantir_tela_pesquisa_takao(page)

    selector_busca = "input#inputSearch"
    codigo = (codigo or "").strip()

    log_interno(f"Buscando pelo código: {codigo}")

    await page.wait_for_selector(selector_busca, state="visible", timeout=20000)

    campo = page.locator(selector_busca).first
    await campo.click(force=True)
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")

    # Takao costuma ser lento; usar type ajuda a disparar eventos
    await page.keyboard.type(str(codigo), delay=45)
    await asyncio.sleep(0.3)
    await page.keyboard.press("Enter")

    log_interno("Pesquisa enviada. Aguardando card do produto (Takao é lento)...")

    # Espera o componente do card aparecer
    try:
        await page.wait_for_selector("app-card-produto-home", state="attached", timeout=20000)
    except Exception:
        log_interno("Nenhum card apareceu após a busca (app-card-produto-home).")
        return

    # Espera extra para o botão/preço renderizar (Angular)
    await asyncio.sleep(2.5)


# ---------------------------
# 2) CLICAR EM "ADICIONAR" NO CARD
# ---------------------------
async def clicar_adicionar_no_card(page) -> bool:
    # seu HTML: <div id="botao-adicionar"><button data-testid="btnAdicionar"...>
    btn = page.locator("#botao-adicionar button[data-testid='btnAdicionar'], button[data-testid='btnAdicionar']").first

    if await btn.count() == 0:
        log_interno("Botão Adicionar (data-testid='btnAdicionar') não encontrado no card.")
        return False

    try:
        await btn.scroll_into_view_if_needed()
        await btn.click(force=True)
        log_interno("Clique em 'Adicionar' realizado. Aguardando modal/quantidade...")
        await asyncio.sleep(1.2)
        return True
    except Exception as e:
        log_interno(f"Erro ao clicar em 'Adicionar': {e}")
        return False


# ---------------------------
# 3) SETAR QUANTIDADE (INPUT DO MODAL) + CONFIRMAR
# ---------------------------
async def setar_quantidade_e_confirmar(page, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 1)

    qty_input = page.locator("input[name='quantidade']").first
    btn_confirm = page.locator("button[data-testid='btnAdicionarConfirm']").first

    try:
        # espera o input aparecer (modal)
        await qty_input.wait_for(state="visible", timeout=20000)

        # foco + limpar + digitar (mais confiável que fill em angular)
        await qty_input.scroll_into_view_if_needed()
        await qty_input.click(force=True)

        # alguns inputs são type="text", então ctrl+a funciona
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.type(str(quantidade), delay=55)

        # redundância: dispara eventos
        await qty_input.evaluate(
            """(el) => {
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
            }"""
        )

        # valida valor
        await asyncio.sleep(0.4)
        final_val = (await qty_input.input_value()).strip()
        if _to_int(final_val, -1) != quantidade:
            log_interno(f"Qtd não confirmou (final='{final_val}'). Tentando via JS...")
            await qty_input.evaluate(
                """(el, v) => {
                    el.value = v;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur', { bubbles: true }));
                }""",
                str(quantidade),
            )
            await asyncio.sleep(0.4)
            final_val = (await qty_input.input_value()).strip()

        if _to_int(final_val, -1) != quantidade:
            return {
                "success": False,
                "error": f"Quantidade não persistiu no input. Final='{final_val}', esperado={quantidade}",
                "qtd_enviada": quantidade,
                "qtd_final": final_val,
            }

        # espera um pouco antes de confirmar
        await asyncio.sleep(0.8)

        # confirmar
        if await btn_confirm.count() == 0:
            return {"success": False, "error": "Botão confirmar (data-testid='btnAdicionarConfirm') não encontrado."}

        await btn_confirm.scroll_into_view_if_needed()
        await btn_confirm.click(force=True)

        # aguarda o site processar
        await asyncio.sleep(1.5)

        return {"success": True, "qtd": quantidade}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 4) FUNÇÃO PRINCIPAL (PRODUÇÃO)
# ---------------------------
async def processar_lista_produtos_takao(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    resultados = []

    log_interno(f"Processando {len(itens)} itens (Takao) para carrinho...")

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        log_interno(f"--- TAKAO: {codigo} / Qtd: {quantidade} ---")

        try:
            # 1) Buscar
            await buscar_produto_takao(page, codigo)

            # 2) Garantir que card apareceu
            if await page.locator("app-card-produto-home").count() == 0:
                resultados.append({
                    "success": False,
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "detalhes": {"success": False, "error": "Produto não encontrado (sem app-card-produto-home)"},
                })
                continue

            # 3) Clicar em Adicionar
            ok_add = await clicar_adicionar_no_card(page)
            if not ok_add:
                resultados.append({
                    "success": False,
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "detalhes": {"success": False, "error": "Falha ao clicar no botão Adicionar do card."},
                })
                continue

            # 4) Setar quantidade e confirmar
            qtd_res = await setar_quantidade_e_confirmar(page, quantidade)

            resultados.append({
                "success": bool(qtd_res.get("success")),
                "codigo": codigo,
                "quantidade": quantidade,
                "detalhes": qtd_res,
            })

            # pequena folga entre itens
            await asyncio.sleep(1.0)

        except Exception as e:
            resultados.append({"success": False, "codigo": codigo, "quantidade": quantidade, "error": str(e)})

    # espera antes do runner fechar
    log_interno("Aguardando 3 segundos antes de encerrar...")
    await asyncio.sleep(3)

    return {"success": True, "itens": resultados}
