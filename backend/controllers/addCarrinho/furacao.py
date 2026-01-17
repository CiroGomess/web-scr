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
# 0) GARANTIR TELA DE "NOVO PEDIDO" (onde existe o input de busca do pedido)
# ---------------------------
async def garantir_tela_pedido_furacao(page) -> None:
    """
    Garante que estamos na tela do pedido (fast pedido),
    onde existe o input com placeholder "Digite o código, descrição, similar ou marca do produto".
    Se não estiver, navega via:
      Pedidos -> Novo Pedido -> Continuar
    """
    busca_selector = "input[placeholder^='Digite o código, descrição, similar ou marca do produto']"

    # Já está no pedido?
    try:
        if await page.locator(busca_selector).count() > 0:
            await page.wait_for_selector(busca_selector, state="visible", timeout=8000)
            return
    except Exception:
        pass

    # Tenta abrir home/app (caso esteja em outra rota)
    possiveis_urls = [
        "https://vendas.furacao.com.br/",
        "https://vendas.furacao.com.br/#/",
    ]

    for url in possiveis_urls:
        try:
            log_interno(f"Tentando abrir: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(1.2)
            if await page.locator(busca_selector).count() > 0:
                await page.wait_for_selector(busca_selector, state="visible", timeout=10000)
                return
        except Exception:
            continue

    # Se ainda não está, força o fluxo do menu Pedidos -> Novo Pedido -> Continuar
    try:
        # Abrir dropdown "Pedidos"
        dropdown_pedidos = page.locator("li.dropdown > a.dropdown-toggle:has-text('Pedidos')").first
        if await dropdown_pedidos.count() > 0:
            log_interno("Abrindo menu: Pedidos")
            await dropdown_pedidos.click(force=True)
            await asyncio.sleep(0.6)
        else:
            log_interno("Aviso: não achei o dropdown 'Pedidos' de primeira.")

        # Clicar em "Novo Pedido" (abre modal)
        link_novo_pedido = page.locator("a:has-text('Novo Pedido')").first
        if await link_novo_pedido.count() == 0:
            # fallback pelo data-target do modal
            link_novo_pedido = page.locator("a[data-target='#selecionarClienteModalCli']").first

        if await link_novo_pedido.count() > 0:
            log_interno("Clicando em: Novo Pedido")
            await link_novo_pedido.click(force=True)
            await asyncio.sleep(1.0)
        else:
            log_interno("Aviso: link 'Novo Pedido' não encontrado.")
            # tenta mesmo assim achar o campo depois
            await asyncio.sleep(1.0)

        # Clicar "Continuar" no modal
        btn_continuar = page.locator("button.btn.btn-primary:has-text('Continuar')").first
        if await btn_continuar.count() == 0:
            # fallback pelo ng-click
            btn_continuar = page.locator("button[ng-click*='abrir_pedido_cliente']").first

        if await btn_continuar.count() > 0:
            log_interno("Clicando em: Continuar (modal)")
            await btn_continuar.click(force=True)
            await asyncio.sleep(1.5)
        else:
            log_interno("Aviso: botão 'Continuar' não encontrado no modal.")
            await asyncio.sleep(1.0)

        # Agora espera o input do pedido aparecer
        log_interno("Aguardando campo de busca do pedido aparecer...")
        await page.wait_for_selector(busca_selector, state="visible", timeout=20000)
        await asyncio.sleep(1.0)

    except Exception as e:
        log_interno(f"Aviso: falha ao garantir tela de pedido via menu: {e}")


# ---------------------------
# 1) BUSCAR PRODUTO NO PEDIDO (digita + ENTER para adicionar)
# ---------------------------
async def buscar_produto_no_pedido(page, codigo: str) -> Dict[str, Any]:
    codigo = (codigo or "").strip()
    busca_selector = "input[placeholder^='Digite o código, descrição, similar ou marca do produto']"
    qty_selector = "#fast_pedido_quant"

    try:
        await garantir_tela_pedido_furacao(page)

        await page.wait_for_selector(busca_selector, state="visible", timeout=20000)
        campo = page.locator(busca_selector).first

        log_interno(f"Buscando (pedido): {codigo}")
        await campo.click(force=True)

        # limpa
        try:
            await campo.fill("")
        except Exception:
            pass

        await campo.fill(codigo)
        await asyncio.sleep(0.7)

        # ENTER para adicionar o produto (como você pediu)
        log_interno("Pressionando ENTER para adicionar o produto...")
        try:
            await campo.press("Enter")
        except Exception:
            await page.keyboard.press("Enter")

        # vai com calma: espera o produto “assentar”
        await asyncio.sleep(1.2)

        # Em alguns casos o autocomplete exige mais uma confirmação
        # (mantive para robustez; se não precisar, não atrapalha)
        log_interno("Pressionando ENTER novamente (confirmação, se necessário)...")
        try:
            await campo.press("Enter")
        except Exception:
            await page.keyboard.press("Enter")

        await asyncio.sleep(1.2)

        # Espera o input de quantidade existir (mesmo que ainda esteja disabled)
        await page.wait_for_selector(qty_selector, state="attached", timeout=15000)

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": f"Erro ao buscar/adicionar produto no pedido: {e}"}


# ---------------------------
# 2) SETAR QUANTIDADE (input #fast_pedido_quant)
# ---------------------------
async def setar_quantidade_fast(page, quantidade: int) -> Dict[str, Any]:
    quantidade = _to_int(quantidade, 1)
    qty_selector = "#fast_pedido_quant"

    try:
        await page.wait_for_selector(qty_selector, state="attached", timeout=15000)
        qty_input = page.locator(qty_selector).first

        # esperar habilitar (disabled some quando produto foi adicionado)
        for _ in range(30):
            disabled = await qty_input.get_attribute("disabled")
            if disabled is None:
                break
            await asyncio.sleep(0.35)

        await qty_input.scroll_into_view_if_needed()
        await qty_input.click(force=True)

        # tenta fill normal
        try:
            await qty_input.fill(str(quantidade))
        except Exception:
            # fallback JS (Angular)
            await qty_input.evaluate(
                """(el, v) => {
                    el.value = v;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.blur();
                }""",
                str(quantidade),
            )

        # redundância
        try:
            await qty_input.dispatch_event("input")
            await qty_input.dispatch_event("change")
        except Exception:
            pass

        log_interno(f"Quantidade setada para {quantidade}. Aguardando 3 segundos...")
        await asyncio.sleep(3.0)

        final_val = None
        try:
            final_val = await qty_input.input_value()
        except Exception:
            pass

        return {"success": True, "qtd_enviada": quantidade, "qtd_final": final_val}

    except Exception as e:
        return {"success": False, "error": f"Erro ao setar quantidade: {e}"}


# ---------------------------
# 3) CLICAR NO BOTÃO "+" (adicionar item no pedido)
# ---------------------------
async def clicar_botao_mais(page) -> Dict[str, Any]:
    # seu botão:
    # <button ... class="btn btn-primary btn-block" style="width: 40px"><i class="fa fa-plus"></i></button>

    try:
        btn = page.locator("button[type='submit']:has(i.fa.fa-plus)").first
        if await btn.count() == 0:
            btn = page.locator("button:has(i.fa-plus)").first
        if await btn.count() == 0:
            btn = page.locator("button.btn.btn-primary.btn-block").first

        if await btn.count() == 0:
            return {"success": False, "error": "Botão (+) não encontrado."}

        # esperar habilitar (ng-disabled)
        for _ in range(30):
            disabled = await btn.get_attribute("disabled")
            if disabled is None:
                break
            await asyncio.sleep(0.35)

        await btn.scroll_into_view_if_needed()

        log_interno("Clicando no botão (+) para adicionar item...")
        await btn.click(force=True)

        log_interno("Aguardando 3 segundos após clicar no (+)...")
        await asyncio.sleep(3.0)

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": f"Erro ao clicar no (+): {e}"}


# ---------------------------
# 4) FUNÇÃO PRINCIPAL (PRODUÇÃO)
# ---------------------------
async def processar_lista_produtos_furacao(page, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    resultados: List[Dict[str, Any]] = []
    log_interno(f"Processando {len(itens)} itens (Furacão) para carrinho...")

    # garante tela do pedido antes do loop (melhor performance)
    await garantir_tela_pedido_furacao(page)

    for item in itens:
        codigo = (item.get("codigo") or item.get("sku") or "").strip()
        quantidade = _to_int(item.get("quantidade", 1), 1)

        log_interno(f"--- FURAÇÃO: {codigo} / Qtd: {quantidade} ---")

        try:
            # 1) Buscar e ENTER para adicionar o produto
            res_busca = await buscar_produto_no_pedido(page, codigo)
            if not res_busca.get("success"):
                resultados.append({
                    "success": False,
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "detalhes": res_busca,
                })
                continue

            # 2) Setar quantidade
            res_qtd = await setar_quantidade_fast(page, quantidade)
            if not res_qtd.get("success"):
                resultados.append({
                    "success": False,
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "detalhes": res_qtd,
                })
                continue

            # 3) Clicar no (+) para adicionar
            res_add = await clicar_botao_mais(page)
            if not res_add.get("success"):
                resultados.append({
                    "success": False,
                    "codigo": codigo,
                    "quantidade": quantidade,
                    "detalhes": res_add,
                })
                continue

            resultados.append({
                "success": True,
                "codigo": codigo,
                "quantidade": quantidade,
                "detalhes": {
                    "busca": res_busca,
                    "quantidade": res_qtd,
                    "add": res_add,
                }
            })

        except Exception as e:
            resultados.append({
                "success": False,
                "codigo": codigo,
                "quantidade": quantidade,
                "error": str(e),
            })

    log_interno("Aguardando 3 segundos antes de encerrar...")
    await asyncio.sleep(3.0)

    return {"success": True, "itens": resultados}
