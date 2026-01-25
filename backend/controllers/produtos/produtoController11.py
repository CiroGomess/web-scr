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
    preco = re.sub(r'[^\d,]', '', str(preco_str))
    preco = preco.replace(",", ".")
    try: return float(preco)
    except: return 0.0

def format_brl(valor):
    if valor is None or valor == 0: return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def clean_stock(stock_str):
    if not stock_str: return 0.0
    stock = re.sub(r'[^\d]', '', str(stock_str))
    try: return float(stock)
    except: return 0.0

# ===================== TRATAMENTO LOADING ===================== #
async def verificar_e_recuperar_loading(page) -> bool:
    try:
        is_loading = await page.locator("#loading, .loading, .mat-progress-spinner, .spinner-border").is_visible(timeout=1000)
        
        if is_loading:
            print("⚠️ LOADING TRAVADO! Recuperando...")
            await page.reload()
            try: await page.wait_for_load_state("networkidle", timeout=10000)
            except: pass
            print("⏳ Aguardando 4s pós-refresh...")
            await asyncio.sleep(4)
            return True
    except Exception:
        pass
    return False

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def buscar_produto(page, codigo):
    """
    Retorna True se achou resultado (ou carregou a página de resultados).
    Retorna False se deu TIMEOUT de 8 segundos.
    """
    try:
        selector_busca = "input[formcontrolname='searchTerm']"
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
        
        campo = page.locator(selector_busca)
        await campo.click(force=True)
        await asyncio.sleep(0.2)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)
        
        btn_buscar = page.locator("button.search-button:has-text('Buscar')")
        print(f"⌛ Pesquisando {codigo}...")
        
        if await btn_buscar.is_visible():
            await btn_buscar.click(force=True)
        else:
            await page.keyboard.press("Enter")
        
        print("⏳ Aguardando resultados...")

        # === AQUI ESTÁ A LÓGICA DE 8 SEGUNDOS ===
        try:
            # Espera no MÁXIMO 8000ms (8s) pelo card do produto
            await page.wait_for_selector(".column-view-card", timeout=8000)
            # Se achou antes de 8s, segue o baile
            await asyncio.sleep(1.5) # Pequeno delay para renderizar imagens
            return True
            
        except Exception:
            # Se estourou 8s e não apareceu o card
            print(f"⚠️ Timeout de 8s excedido para {codigo}! Pulando...")
            return False 
        # ========================================
        
    except Exception as e:
        print(f"❌ Erro na busca DPK: {e}")
        return False

# ===================== EXTRAÇÃO DOS DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    
    card_selector = ".column-view-card"
    
    # Se chegou aqui, teoricamente a busca achou algo ou a página carregou vazio
    # Mas validamos de novo
    if await page.locator(card_selector).count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado (Grid vazio).")
        return {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "RJ", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado", "regioes": []
        }

    card = page.locator(card_selector).first
    
    try:
        nome_element = card.locator("h2 a")
        nome_text = (await nome_element.inner_text()).strip()
        
        marca_text = "N/A"
        try:
            marca_el = card.locator("strong:near(p:has-text('Fabricante:'))").first
            if await marca_el.count() == 0:
                 marca_el = card.locator("p:has-text('Fabricante:') + strong")
            if await marca_el.count() > 0:
                marca_text = (await marca_el.inner_text()).strip()
        except: pass

        codigo_fab = codigo_solicitado
        try:
            cod_el = card.locator("p:has-text('Cód do produto:') + strong")
            if await cod_el.count() > 0:
                codigo_fab = (await cod_el.inner_text()).strip()
            else:
                cod_fab = card.locator("p:has-text('Cód de Fábrica:') + strong")
                if await cod_fab.count() > 0:
                    codigo_fab = (await cod_fab.inner_text()).strip()
        except: pass

        img_element = card.locator("img[app-img]")
        try: link_img = await img_element.get_attribute("src")
        except: link_img = None

        try:
            preco_element = card.locator("span.cor-preco")
            preco_raw = (await preco_element.inner_text()).strip()
            preco_num = clean_price(preco_raw)
        except:
            preco_raw = "0,00"; preco_num = 0.0
        
        qtd_disponivel = 0.0
        try:
            estoque_el = card.locator("small.cor-similar:has-text('estoque')")
            if await estoque_el.count() > 0:
                texto_estoque = await estoque_el.inner_text() 
                qtd_disponivel = clean_stock(texto_estoque)
        except: pass
        
        tem_estoque = False
        try:
            btn_add = card.locator("button#adicionarCarrinhoBtn")
            tem_estoque = await btn_add.is_visible() and qtd_disponivel > 0
        except: pass

    except Exception as e:
        print(f"⚠ Erro na extração do card: {e}")
        return None

    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque and (qtd_disponivel >= quantidade_solicitada)

    regiao_sp = {
        "uf": "RJ", "preco": preco_raw, "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num), "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel, "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total), "podeComprar": pode_comprar,
        "mensagem": None if pode_comprar else "Estoque insuficiente", "disponivel": tem_estoque
    }

    item_formatado = {
        "codigo": codigo_fab, "nome": nome_text, "marca": marca_text, "imagem": link_img,
        "preco": preco_raw, "preco_num": preco_num, "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total, "valor_total_formatado": format_brl(valor_total),
        "uf": "RJ", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar, "mensagem": regiao_sp["mensagem"],
        "disponivel": tem_estoque, "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_sp]
    }
    
    print(f"✅ SUCESSO DPK: {codigo_fab} | {format_brl(preco_num)} | Estoque: {qtd_disponivel}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "DPK",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial11(login_data_ou_page, lista_produtos):
    itens_extraidos = []
    
    if isinstance(login_data_ou_page, (tuple, list)):
        if len(login_data_ou_page) >= 3:
            page = login_data_ou_page[2]
        else:
            page = login_data_ou_page[-1]
    else:
        page = login_data_ou_page
    
    if not page or not hasattr(page, 'goto'):
        print("❌ Erro: Objeto 'page' inválido recebido.")
        return []

    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste: 84111")
        lista_produtos = [{"codigo": "84111", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] DPK -> Buscando: {codigo}")
        
        while True:
            try:
                if await verificar_e_recuperar_loading(page): continue

                # 1. Realiza a busca
                # Agora retorna TRUE se achou, ou FALSE se deu timeout de 8s
                encontrou = await buscar_produto(page, codigo)
                
                # SE NÃO ENCONTROU EM 8 SEGUNDOS, SAI DO LOOP WHILE E VAI PRO PROXIMO ITEM (FOR)
                if not encontrou:
                    print("⏩ Pulei para o próximo item devido ao timeout.")
                    break 

                if await verificar_e_recuperar_loading(page): continue

                # 2. Se a busca deu certo, tenta extrair
                resultado = await extrair_dados_produto(page, codigo, qtd)
                if resultado:
                    itens_extraidos.append(resultado)
                
                await asyncio.sleep(1.0)
                break # Sai do while e vai pro próximo item do for

            except Exception as e:
                print(f"❌ Erro crítico no loop F11: {e}")
                if await verificar_e_recuperar_loading(page): continue
                try: await page.reload(wait_until="networkidle")
                except: pass
                break

    if itens_extraidos and salvar_lote_sqlite:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]
        if validos:
            print(f"⏳ Salvando {len(validos)} itens no banco...")
            if salvar_lote_sqlite(preparar_dados_finais(validos)):
                print("✅ Banco atualizado!")
            else:
                print("❌ Erro ao salvar no banco.")
    
    return itens_extraidos