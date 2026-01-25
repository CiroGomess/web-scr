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
    if not preco_str: return 0.0
    preco = re.sub(r"[^\d,]", "", str(preco_str))
    preco = preco.replace(",", ".")
    try: return float(preco)
    except: return 0.0

def format_brl(valor):
    if valor is None or valor == 0: return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_codigo(texto):
    if not texto: return ""
    return re.sub(r"[^a-zA-Z0-9]", "", str(texto)).upper()

def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Sky Peças", 
        "total_itens": len(lista_itens),
        "itens": lista_itens,
    }


# ===================== TRATAMENTO MODAL SWEETALERT2 ===================== #
async def verificar_e_fechar_modal(page) -> bool:
    """
    Verifica se o modal do SweetAlert2 está na tela e fecha ele.
    Retorna True se fechou, False se não tinha nada.
    """
    modal_selector = "div.swal2-popup.swal2-modal.swal2-show"
    btn_ok_selector = "button.swal2-confirm.swal2-styled"

    try:
        # Check rápido (500ms) para ver se o modal está visível
        if await page.locator(modal_selector).is_visible(timeout=500):
            
            # Tenta pegar a mensagem só para log
            try:
                msg = await page.locator("#swal2-html-container").inner_text()
                print(f"🛑 Modal Detectado: '{msg}' - Tentando fechar...")
            except:
                print("🛑 Modal Detectado - Tentando fechar...")

            # Clica no OK
            if await page.locator(btn_ok_selector).is_visible():
                await page.locator(btn_ok_selector).click(force=True)
            else:
                await page.evaluate(f"document.querySelector('{btn_ok_selector}').click()")

            # Espera sumir
            try:
                await page.wait_for_selector(modal_selector, state="hidden", timeout=2000)
            except:
                pass
            
            return True
            
    except Exception:
        pass
        
    return False


# ===================== EXTRAÇÃO DE DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    cards = page.locator(".bx_produto")
    count_cards = await cards.count()

    if count_cards == 0:
        print(f"❌ {codigo_solicitado} não encontrado (Nenhum card).")
        return None

    print(f"🔎 Encontrados {count_cards} itens. Buscando match...")
    item_alvo = None
    cod_buscado_limpo = limpar_codigo(codigo_solicitado)

    for i in range(count_cards):
        card = cards.nth(i)
        try:
            cod_fab_site = ""
            if await card.locator(".codfab strong").count() > 0:
                cod_fab_site = await card.locator(".codfab strong").inner_text()
            
            cod_site_limpo = limpar_codigo(cod_fab_site)
            match_found = False
            
            if cod_buscado_limpo == cod_site_limpo:
                match_found = True
            else:
                if await card.locator(".codnn").count() > 0:
                    cod_nn_text = await card.locator(".codnn").inner_text()
                    if cod_buscado_limpo in limpar_codigo(cod_nn_text):
                        match_found = True

            if match_found:
                item_alvo = card
                break
        except:
            continue
    
    if not item_alvo and count_cards == 1:
        item_alvo = cards.first

    if not item_alvo:
        print("⚠️ Card encontrado, mas código não confere.")
        return None

    try:
        nome_text = await item_alvo.locator(".nome").inner_text()
        try: marca_text = await item_alvo.locator(".fornecedor").inner_text()
        except: marca_text = "N/A"
        try:
            link_img_rel = await item_alvo.locator(".foto img").first.get_attribute("src")
            link_img = ("https://cliente.skypecas.com.br" + link_img_rel) if link_img_rel and not link_img_rel.startswith("http") else (link_img_rel or "")
        except: link_img = ""
        try: preco_raw = await item_alvo.locator(".preco_final").inner_text()
        except: preco_raw = "0,00"
        
        preco_num = clean_price(preco_raw)
        
        qtd_disponivel = 0
        try:
            estoque_text = await item_alvo.locator(".lkEstoqueProduto").inner_text()
            match_estoque = re.search(r"(\d+)", estoque_text or "")
            if match_estoque: qtd_disponivel = int(match_estoque.group(1))
        except: pass

        qtd_solic = int(quantidade_solicitada or 1)
        tem_estoque = (qtd_disponivel > 0) and (preco_num > 0)
        valor_total = preco_num * qtd_solic
        pode_comprar = tem_estoque

        regiao_rj = {
            "uf": "RJ", "preco": str(preco_raw).strip(), "preco_num": preco_num,
            "preco_formatado": format_brl(preco_num), "qtdSolicitada": qtd_solic,
            "qtdDisponivel": qtd_disponivel, "valor_total": valor_total,
            "valor_total_formatado": format_brl(valor_total), "podeComprar": pode_comprar,
            "mensagem": None if pode_comprar else "Sem estoque", "disponivel": tem_estoque,
        }

        return {
            "codigo": str(codigo_solicitado).strip(), "nome": str(nome_text).strip(),
            "marca": str(marca_text).strip(), "imagem": link_img,
            "preco": str(preco_raw).strip(), "preco_num": preco_num,
            "preco_formatado": format_brl(preco_num), "valor_total": valor_total,
            "valor_total_formatado": format_brl(valor_total), "uf": "RJ",
            "qtdSolicitada": qtd_solic, "qtdDisponivel": qtd_disponivel,
            "podeComprar": pode_comprar, "mensagem": regiao_rj["mensagem"],
            "disponivel": tem_estoque, "status": "Disponível" if tem_estoque else "Indisponível",
            "regioes": [regiao_rj],
        }
    except Exception as e:
        print(f"⚠ Erro na extração: {e}")
        return None


# ===================== EXECUTOR PRINCIPAL ===================== #
async def processar_lista_produtos_sequencial_sky(login_data_ou_page, lista_produtos):
    itens_extraidos = []
    
    if isinstance(login_data_ou_page, (tuple, list)) and len(login_data_ou_page) >= 3:
        page = login_data_ou_page[2]
    else:
        page = login_data_ou_page

    if not page:
        print("❌ Erro: page inválida.")
        return []

    # Normalização da lista
    if not lista_produtos: lista_produtos = []
    if isinstance(lista_produtos, str): lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]
    normalized = []
    for item in lista_produtos:
        if isinstance(item, str): normalized.append({"codigo": item, "quantidade": 1})
        elif isinstance(item, dict): normalized.append(item)
    lista_produtos = normalized

    selector_input = "#inpCodigo"

    for idx, item in enumerate(lista_produtos):
        codigo = str(item.get("codigo", "")).strip()
        qtd = int(item.get("quantidade", 1) or 1)

        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] SKY -> Buscando: {codigo}")
        if not codigo: continue

        try:
            # ==============================================================================
            # 🛡️ ROTINA DE LIMPEZA DE MODAL (SOLICITADA: 3x com intervalo de 1.2s)
            # ==============================================================================
            print("🛡️ Verificando modais antes de digitar...")
            for tentativa in range(3):
                fechou = await verificar_e_fechar_modal(page)
                if fechou:
                    print(f"   ↳ Modal fechado na tentativa {tentativa+1}.")
                # Intervalo solicitado
                await asyncio.sleep(1.2)
            # ==============================================================================

            # Aguarda input e clica com FORCE=TRUE para ignorar "pointer events" se sobrar resquício
            await page.wait_for_selector(selector_input, state="visible", timeout=20000)
            
            # Clica (force=True vence o erro "intercepts pointer events")
            await page.click(selector_input, force=True) 
            
            await page.fill(selector_input, "")
            await asyncio.sleep(0.2)
            await page.type(selector_input, codigo, delay=50) 
            await page.keyboard.press("Enter")

            print("⏳ Aguardando resultado...")

            # Corrida: Sucesso vs Modal de Erro
            task_sucesso = asyncio.create_task(page.wait_for_selector(".bx_produto", timeout=10000))
            task_modal = asyncio.create_task(page.wait_for_selector("div.swal2-popup.swal2-modal.swal2-show", timeout=10000))

            done, pending = await asyncio.wait({task_sucesso, task_modal}, return_when=asyncio.FIRST_COMPLETED)
            for t in pending: t.cancel()

            if task_modal in done:
                try:
                    await task_modal
                    print("🛑 Modal de 'Não Encontrado' apareceu.")
                    # Como apareceu um novo modal, fechamos ele imediatamente
                    await verificar_e_fechar_modal(page)
                    continue 
                except: pass

            elif task_sucesso in done:
                try:
                    await task_sucesso
                    # Verificação de segurança pós-carregamento
                    if await verificar_e_fechar_modal(page):
                         print("⚠️ Modal apareceu sobre o produto. Pulando.")
                         continue
                except: continue
            
            else:
                print("⚠️ Timeout na busca.")
                await verificar_e_fechar_modal(page)
                continue

            await asyncio.sleep(0.5)
            resultado = await extrair_dados_produto(page, codigo, qtd)

            if resultado:
                itens_extraidos.append(resultado)
                print(f"✅ SUCESSO SKY: {resultado['codigo']} | {resultado['preco_formatado']}")

        except Exception as e:
            print(f"❌ Falha crítica no loop Sky ({codigo}): {e}")
            await verificar_e_fechar_modal(page)
            try: await page.reload()
            except: pass

    # Salvamento
    if itens_extraidos and salvar_lote_sqlite:
        validos = [r for r in itens_extraidos if r and r.get("codigo")]
        if validos:
            print("⏳ Salvando no banco...")
            if salvar_lote_sqlite(preparar_dados_finais(validos)): print("✅ Salvo!")
            else: print("❌ Erro ao salvar.")

    return itens_extraidos