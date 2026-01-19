import asyncio
import re
from datetime import datetime

# ===================== IMPORTAÇÃO DO SERVIÇO DE BANCO ===================== #
try:
    from services.db_saver import salvar_lote_sqlite
except ImportError:
    print("⚠️ Aviso: 'services.db_saver' não encontrado. O salvamento no banco será pulado.")
    salvar_lote_sqlite = None

# ===================== AUXILIARES ===================== #
def clean_price(preco_str):
    if not preco_str:
        return 0.0
    preco = re.sub(r"[^\d,]", "", str(preco_str))
    preco = preco.replace(",", ".")
    try:
        return float(preco)
    except:
        return 0.0

def format_brl(valor):
    if valor is None or valor == 0:
        return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def clean_stock(stock_str):
    if not stock_str:
        return 0.0
    stock = re.sub(r"[^\d]", "", str(stock_str))
    try:
        return float(stock)
    except:
        return 0.0

# ===================== HELPERS “COM CALMA” ===================== #
async def click_com_calma(locator, pre=0.4, post=0.6, force=True):
    """Clique com pequenas esperas para evitar race condition/UI lenta."""
    try:
        await asyncio.sleep(pre)
        await locator.scroll_into_view_if_needed()
    except:
        pass
    await asyncio.sleep(pre)
    await locator.click(force=force)
    await asyncio.sleep(post)

async def limpar_e_digitar_com_calma(page, selector, texto, delay_keypress=70):
    """
    Limpa e digita no campo com delays (mais confiável que fill direto em UIs sensíveis).
    """
    await page.wait_for_selector(selector, state="visible", timeout=20000)
    campo = page.locator(selector).first

    await click_com_calma(campo, pre=0.25, post=0.25)

    # limpa com ctrl+a/backspace
    await asyncio.sleep(0.2)
    await page.keyboard.press("Control+A")
    await asyncio.sleep(0.15)
    await page.keyboard.press("Backspace")
    await asyncio.sleep(0.25)

    # digita “humano”
    await campo.type(str(texto), delay=delay_keypress)
    await asyncio.sleep(0.3)

# ===================== NAVEGAÇÃO E BUSCA ===================== #
# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def navegar_para_pedido(page):
    """Navega até a tela de PVW - Pedido (/Movimentacao) com tentativas e fallback."""
    try:
        url_atual = page.url or ""
        if "/Movimentacao" in url_atual:
            return

        print("📂 Navegando para o menu 'PVW - Pedido'...")

        selector_menu = "a[href='/Movimentacao']"
        menu_pedido = page.locator(selector_menu).first

        # 1) Garante que o link existe/está visível
        await page.wait_for_selector(selector_menu, state="attached", timeout=20000)
        try:
            await menu_pedido.wait_for(state="visible", timeout=15000)
        except Exception:
            pass

        # 2) Tentativas de clique com verificação real de navegação
        tentativas = 3
        for tentativa in range(1, tentativas + 1):
            if "/Movimentacao" in (page.url or ""):
                return

            print(f"➡️ Tentativa {tentativa}/{tentativas} para entrar em /Movimentacao...")

            try:
                # "com calma"
                await asyncio.sleep(0.8)  # <-- tempo extra antes do clique (solicitado)
                await menu_pedido.scroll_into_view_if_needed()
                await asyncio.sleep(0.4)

                # clique principal
                await menu_pedido.click(force=True, timeout=8000)
            except Exception:
                # fallback: click via JS
                try:
                    await page.evaluate(
                        """() => {
                            const a = document.querySelector("a[href='/Movimentacao']");
                            if (a) a.click();
                        }"""
                    )
                except Exception:
                    pass

            # 3) Aguarda URL mudar OU algo típico da tela aparecer
            try:
                await page.wait_for_url("**/Movimentacao**", timeout=12000)
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(1.2)
                return
            except Exception:
                # às vezes a SPA muda sem "wait_for_url" captar; checa por elementos da tela
                try:
                    # Se algum elemento da tela de movimentação existir, considera OK
                    # (mantive genérico: aba produtos ou input codPeca costuma aparecer depois)
                    await page.wait_for_selector("a[href='#tabs-2'], #codPeca, tr.jqgrow", timeout=6000)
                    await asyncio.sleep(0.8)
                    return
                except Exception:
                    print("⚠️ Ainda não entrou. Vou tentar novamente...")

        # 4) Fallback final: força navegação por URL (pega a origem atual)
        if "/Movimentacao" not in (page.url or ""):
            base = ""
            try:
                # tenta montar base a partir do origin atual
                base = await page.evaluate("() => window.location.origin")
            except Exception:
                pass

            # se não conseguir origin, usa url atual “até o host”
            if not base:
                try:
                    m = re.match(r"^(https?://[^/]+)", page.url or "")
                    base = m.group(1) if m else ""
                except Exception:
                    base = ""

            if base:
                url_forcada = base.rstrip("/") + "/Movimentacao"
                print(f"🛠️ Fallback: forçando navegação para {url_forcada}")
                await page.goto(url_forcada, wait_until="networkidle")
                await asyncio.sleep(1.5)

    except Exception as e:
        print(f"⚠️ Erro ao navegar para Pedido: {e}")


async def ativar_aba_produtos(page):
    """Clica na aba 'Produtos' (#tabs-2) com calma"""
    try:
        aba_produtos = page.locator("a[href='#tabs-2']").first

        # se o input já estiver visível, a aba já está ok
        if await page.locator("#codPeca").is_visible():
            return

        print("📑 Clicando na aba 'Produtos'...")
        try:
            await aba_produtos.wait_for(state="visible", timeout=10000)
        except:
            pass

        if await aba_produtos.count() > 0 and await aba_produtos.is_visible():
            await click_com_calma(aba_produtos, pre=0.6, post=1.0)
            await asyncio.sleep(1.0)

        # garante que o campo apareceu
        await page.wait_for_selector("#codPeca", state="visible", timeout=15000)

    except Exception as e:
        print(f"⚠️ Erro ao ativar aba Produtos: {e}")

async def buscar_produto(page, codigo):
    """
    Busca com etapas e delays:
    - navega
    - ativa aba
    - limpa e digita
    - enter
    - aguarda jqGrid estabilizar
    """
    try:
        await navegar_para_pedido(page)
        await ativar_aba_produtos(page)

        selector_busca = "#codPeca"

        print(f"⌨️ Digitando código: {codigo}")
        await limpar_e_digitar_com_calma(page, selector_busca, codigo, delay_keypress=70)

        print("🚀 Pressionando ENTER...")
        await asyncio.sleep(0.4)
        await page.keyboard.press("Enter")

        # aguarda resultados ou “vazio” estabilizar
        print("⏳ Aguardando resultados...")
        # tenta aguardar uma linha jqgrow; se não vier, segue adiante
        try:
            await page.wait_for_selector("tr.jqgrow", timeout=6000)
        except:
            pass

        # tempo extra para jqGrid terminar renderização
        await asyncio.sleep(1.4)

    except Exception as e:
        print(f"❌ Erro na busca PLS: {e}")

# ===================== EXTRAÇÃO DOS DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    linhas = page.locator("tr.jqgrow")

    if await linhas.count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado.")
        return {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "RJ",
            "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }

    tr = linhas.first

    try:
        # (Opcional) garante que a primeira linha está “pronta”
        await asyncio.sleep(0.4)

        colunas = tr.locator("td")

        codigo_fab = (await colunas.nth(0).inner_text()).strip()
        nome_text = (await colunas.nth(2).inner_text()).strip()
        marca_text = (await colunas.nth(3).inner_text()).strip()

        estoque_raw = (await colunas.nth(7).inner_text()).strip()
        qtd_disponivel = clean_stock(estoque_raw)

        preco_raw = (await colunas.nth(9).inner_text()).strip()
        preco_num = clean_price(preco_raw)

        link_img = None

        tem_estoque = qtd_disponivel > 0 and preco_num > 0

    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque and (qtd_disponivel >= quantidade_solicitada)

    regiao_sp = {
        "uf": "RJ",
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "podeComprar": pode_comprar,
        "mensagem": None if pode_comprar else "Estoque insuficiente",
        "disponivel": tem_estoque
    }

    item_formatado = {
        "codigo": codigo_fab,
        "nome": nome_text,
        "marca": marca_text,
        "imagem": link_img,
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "uf": "RJ",
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar,
        "mensagem": regiao_sp["mensagem"],
        "disponivel": tem_estoque,
        "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_sp]
    }

    print(f"✅ SUCESSO PLS: {codigo_fab} | {format_brl(preco_num)} | Estoque: {qtd_disponivel}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Odapel",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial17(page, lista_produtos):
    itens_extraidos = []

    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste: 1867.8")
        lista_produtos = [{"codigo": "1867.8", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] PLS -> Buscando: {codigo}")

        try:
            await buscar_produto(page, codigo)
            resultado = await extrair_dados_produto(page, codigo, qtd)

            if resultado:
                itens_extraidos.append(resultado)

            await asyncio.sleep(1.1)

        except Exception as e:
            print(f"❌ Erro crítico no loop F17: {e}")
            await page.reload(wait_until="networkidle")

    # SALVAMENTO
    if itens_extraidos:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]

        if validos:
            if salvar_lote_sqlite:
                print(f"⏳ Salvando {len(validos)} itens no banco...")
                if salvar_lote_sqlite(preparar_dados_finais(validos)):
                    print("✅ Banco atualizado!")
                else:
                    print("❌ Erro ao salvar no banco.")
            else:
                print("ℹ️ Banco não configurado.")
        else:
            print("⚠️ Nada encontrado para salvar.")

    return itens_extraidos
