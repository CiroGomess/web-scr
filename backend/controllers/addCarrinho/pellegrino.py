# controllers/addCarrinho/pellegrino.py
import asyncio
from typing import Dict, Any, List


def log_interno(msg: str) -> None:
    print(f"   [Pellegrino Bot] {msg}")


def _to_int(v, default=1) -> int:
    try:
        n = int(str(v).strip())
        return n if n > 0 else default
    except Exception:
        return default


# Controle para fechar o tutorial Driver.js apenas uma vez por sessão
_bloqueios_removidos = False


async def verificar_bloqueios_unico(page) -> None:
    """
    Fecha o pop-up do Driver.js (tutorial) APENAS UMA VEZ por sessão.
    """
    global _bloqueios_removidos
    if _bloqueios_removidos:
        return

    log_interno("Verificando possíveis bloqueios (tutorial/popup)...")
    try:
        await asyncio.sleep(3)

        btn_fechar = page.locator(".driver-popover-close-btn").first
        if await btn_fechar.count() > 0 and await btn_fechar.is_visible():
            log_interno("Pop-up detectado. Fechando...")
            await btn_fechar.click(force=True)
            await asyncio.sleep(1)
            log_interno("Pop-up fechado.")
        else:
            log_interno("Nenhum pop-up detectado.")

        _bloqueios_removidos = True
    except Exception as e:
        log_interno(f"Aviso: falha ao tentar fechar pop-up: {e}")
        _bloqueios_removidos = True


async def garantir_tela_busca(page) -> None:
    """
    Garante que o campo #search-prod está disponível.
    """
    selector_busca = "#search-prod"
    try:
        await page.wait_for_selector(selector_busca, state="visible", timeout=15000)
        return
    except Exception:
        pass

    # Fallback simples (caso caia em outra rota após login)
    urls = [
        "https://compreonline.pellegrino.com.br/",
        "https://compreonline.pellegrino.com.br/catalogo",
        "https://compreonline.pellegrino.com.br/home",
    ]
    for url in urls:
        try:
            log_interno(f"Tentando abrir tela de busca: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(1)
            if await page.locator(selector_busca).count() > 0:
                await page.wait_for_selector(selector_busca, state="visible", timeout=15000)
                return
        except Exception:
            continue

    log_interno("Aviso: não consegui garantir a tela de busca automaticamente.")


# ---------------------------
# 1) BUSCA
# ---------------------------
async def buscar_produto_pellegrino(page, codigo: str) -> None:
    await garantir_tela_busca(page)

    selector_busca = "#search-prod"
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
    await asyncio.sleep(0.4)

    # Enter para pesquisar
    try:
        await campo.press("Enter")
    except Exception:
        await page.keyboard.press("Enter")

    # fecha popup só 1x
    await verificar_bloqueios_unico(page)

    # Espera alguma linha aparecer (odd/even)
    try:
        await page.wait_for_selector("table tbody tr.odd, table tbody tr.even", state="attached", timeout=12000)
    except Exception:
        log_interno("Nenhuma linha apareceu após a busca (tabela vazia).")

    # Pequena folga para render
    await asyncio.sleep(1.0)


# ---------------------------
# 2) PEGAR PRIMEIRA LINHA E ADICIONAR QUANTIDADE + BOTÃO
# ---------------------------
async def adicionar_quantidade_e_clicar(page, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 1)

    linha_selector = "table tbody tr.odd, table tbody tr.even"
    tr = page.locator(linha_selector).first
    if await tr.count() == 0:
        return {"success": False, "error": "Tabela sem resultados (nenhuma linha odd/even)."}

    # Input de quantidade (dentro da linha)
    # Exemplo: input.vit-qtde-table.catalogo-qtde.notmodalprd
    input_qtd = tr.locator("input.vit-qtde-table").first
    if await input_qtd.count() == 0:
        return {"success": False, "error": "Input de quantidade (.vit-qtde-table) não encontrado na linha."}

    # Vincula pelo data-wsid, se existir (mais robusto)
    data_wsid = None
    try:
        data_wsid = await input_qtd.get_attribute("data-wsid")
    except Exception:
        data_wsid = None

    # Botão de confirmar quantidade (na linha), idealmente com mesmo data-wsid
    btn_add = None
    if data_wsid:
        btn_add = tr.locator(f"button.btn-qtde[data-wsid='{data_wsid}']").first

    if not btn_add or (await btn_add.count() == 0):
        # fallback: qualquer btn-qtde dentro da linha
        btn_add = tr.locator("button.btn-qtde").first

    if await btn_add.count() == 0:
        return {"success": False, "error": "Botão de adicionar (button.btn-qtde) não encontrado na linha."}

    # Setar quantidade
    try:
        await input_qtd.scroll_into_view_if_needed()
        await input_qtd.click(force=True)

        # limpar e preencher
        try:
            await input_qtd.fill("")
        except Exception:
            pass

        try:
            await input_qtd.fill(str(quantidade))
        except Exception:
            # fallback JS (inputs com máscara)
            await input_qtd.evaluate(
                """(el, v) => {
                    el.value = v;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.blur();
                }""",
                str(quantidade),
            )

        # reforça eventos
        try:
            await input_qtd.dispatch_event("input")
            await input_qtd.dispatch_event("change")
        except Exception:
            pass

        log_interno(f"Quantidade setada para {quantidade}. Aguardando 3s antes de clicar no botão...")
        await asyncio.sleep(3)

        # Clicar no botão de adicionar
        log_interno("Clicando no botão de adicionar ao carrinho...")
        await btn_add.click(force=True)

        log_interno("Aguardando 3s após clicar no botão de adicionar...")
        await asyncio.sleep(3)

        # validação simples (opcional): mantém retorno positivo se não houve exceção
        return {"success": True, "qtd": quantidade, "data_wsid": data_wsid}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------
# 3) FUNÇÃO PRINCIPAL (PRODUÇÃO)
# ---------------------------
async def processar_lista_produtos_pellegrino(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    global _bloqueios_removidos
    _bloqueios_removidos = False

    resultados = []
    log_interno(f"Processando {len(itens)} itens (Pellegrino) para carrinho...")

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        log_interno(f"--- PELLEGRINO: {codigo} / Qtd: {quantidade} ---")

        try:
            # 1) Buscar
            await buscar_produto_pellegrino(page, codigo)

            # 2) Setar quantidade e clicar no botão
            res = await adicionar_quantidade_e_clicar(page, quantidade)

            resultados.append(
                {
                    "success": bool(res.get("success")),
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "detalhes": res,
                }
            )

        except Exception as e:
            resultados.append({"success": False, "codigo": codigo, "quantidade": quantidade, "error": str(e)})

        # pequena folga entre itens
        await asyncio.sleep(0.8)

    log_interno("Aguardando 3 segundos antes de encerrar...")
    await asyncio.sleep(3)

    return {"success": True, "itens": resultados}
