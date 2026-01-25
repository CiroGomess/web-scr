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

# ===================== TRATAMENTO LOADING (TRAVAMENTO) ===================== #
async def verificar_e_recuperar_loading(page) -> bool:
    """
    Verifica se a tela de loading está travada ou se a página quebrou.
    Se necessário: Dá refresh na página e aguarda o Angular carregar.
    """
    try:
        # Tenta detectar loading (Furacão costuma ter máscaras de loading ou #loading)
        # Seletor genérico + especifico se houver
        loading_visible = await page.locator("#loading, .loading-mask, .block-ui-overlay").is_visible(timeout=1000)
        
        if loading_visible:
            print("⚠️ TELA DE LOADING TRAVADA DETECTADA! Iniciando recuperação...")
            await page.reload()
            
            # Espera o reload
            try: await page.wait_for_load_state("networkidle", timeout=10000)
            except: pass

            # Espera o Angular "hidratar" (importante no Furacão)
            print("⏳ Aguardando 5s para o sistema voltar...")
            await asyncio.sleep(5)
            
            print("🔄 Página atualizada. Retomando fluxo...")
            return True
    except Exception:
        pass
    
    return False

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        # Seletor do campo de busca
        selector_busca = "input#gsearch"
        
        # Garante que o campo está visível antes de interagir
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
        
        campo = page.locator(selector_busca)
        
        # Clica e limpa com garantia (force=True ajuda se tiver overlay invisivel)
        await campo.click(force=True)
        await asyncio.sleep(0.3)
        await page.keyboard.press("Control+A")
        await asyncio.sleep(0.1)
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.2)
        
        # Digita e pesquisa
        print(f"⌨️ Digitando: {codigo}")
        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)
        
        print("🚀 Enter para pesquisar...")
        await page.keyboard.press("Enter")
        
        # Espera carregar os cards OU mensagem de erro
        # (Adicionei verificação de loading aqui também)
        print("⏳ Aguardando resultados...")
        
        # Corrida: Resultado vs Loading Travado
        try:
            task_result = asyncio.create_task(page.wait_for_selector("tr[ng-controller='RowCtrl']", timeout=10000))
            task_loading = asyncio.create_task(page.wait_for_selector(".loading-mask", state="visible", timeout=2000))
            
            done, pending = await asyncio.wait({task_result, task_loading}, return_when=asyncio.FIRST_COMPLETED)
            for t in pending: t.cancel()
        except:
            pass
            
        await asyncio.sleep(1.5)
        
    except Exception as e:
        print(f"❌ Erro na busca Furação: {e}")
        # Não lança erro aqui para permitir que o loop principal trate com reload

# ===================== EXTRAÇÃO DOS DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    
    # Seletor do CARD DO PRODUTO (tr que contém o gridview)
    card_selector = "tr[ng-controller='RowCtrl']"
    
    if await page.locator(card_selector).count() == 0:
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

    # Pega o PRIMEIRO card
    card = page.locator(card_selector).first
    
    try:
        # --- EXTRAÇÃO ---
        
        # Nome / Descrição
        nome_element = card.locator("div.descricao span.ng-binding").last
        nome_text = (await nome_element.inner_text()).strip()
        
        # Código
        try:
            cod_el = card.locator("span.ng-binding").first 
            codigo_fab = (await cod_el.inner_text()).strip()
        except:
            codigo_fab = codigo_solicitado

        # Marca
        marca_text = "N/A"
        try:
            marca_el = card.locator("strong:has-text('Marca:') + span")
            if await marca_el.count() > 0:
                marca_text = (await marca_el.inner_text()).strip()
        except: pass

        # Imagem
        try:
            img_element = card.locator("div.img img").first
            link_img = await img_element.get_attribute("src")
            if link_img and not link_img.startswith("http"):
                link_img = "https://vendas.furacao.com.br" + link_img
        except: link_img = None

        # Preço
        try:
            preco_element = card.locator("span.h3.ng-binding").last
            preco_raw = (await preco_element.inner_text()).strip()
        except: preco_raw = "0,00"
        
        preco_num = clean_price(preco_raw)
        
        # Estoque
        qtd_disponivel = 0.0
        try:
            estoque_el = card.locator("span:has-text('Estoque:')")
            if await estoque_el.count() > 0:
                texto_estoque = await estoque_el.inner_text()
                qtd_disponivel = clean_stock(texto_estoque)
        except: pass
        
        # Disponibilidade
        tem_estoque = qtd_disponivel > 0 and preco_num > 0

    except Exception as e:
        print(f"⚠ Erro na extração do card: {e}")
        return None

    # --- CONSOLIDAÇÃO ---
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
    
    print(f"✅ SUCESSO FURAÇÃO: {codigo_fab} | {format_brl(preco_num)} | Marca: {marca_text}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Furacão",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial16(login_data_ou_page, lista_produtos):
    itens_extraidos = []
    
    # === CORREÇÃO: Extração correta do objeto 'page' da tupla de login ===
    if isinstance(login_data_ou_page, (tuple, list)):
        if len(login_data_ou_page) >= 3:
            page = login_data_ou_page[2]
        else:
            page = login_data_ou_page[-1]
    else:
        page = login_data_ou_page
    
    # Validação
    if not page or not hasattr(page, 'goto'):
        print("❌ Erro: Objeto 'page' inválido recebido.")
        return []

    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste: IWP065")
      
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Furação -> Buscando: {codigo}")
        
        # === LOOP DE RETRY (Tenta o mesmo produto se der erro) ===
        while True:
            try:
                # 1. Verifica se já está travado antes de começar
                if await verificar_e_recuperar_loading(page):
                    continue

                await buscar_produto(page, codigo)
                
                # 2. Verifica se travou durante a busca
                if await verificar_e_recuperar_loading(page):
                    continue

                resultado = await extrair_dados_produto(page, codigo, qtd)
                
                if resultado:
                    itens_extraidos.append(resultado)
                
                await asyncio.sleep(1.5)
                
                # Se chegou aqui, deu tudo certo, sai do loop de retry
                break 

            except Exception as e:
                print(f"❌ Erro crítico no loop F16: {e}")
                
                # Tenta recuperar se for loading
                if await verificar_e_recuperar_loading(page):
                    continue
                
                # Se for outro erro, dá reload e aborta esse item para não travar o robô inteiro
                try: await page.reload(wait_until="networkidle")
                except: pass
                break

    # SALVAMENTO
    if itens_extraidos and salvar_lote_sqlite:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]
        
        if validos:
            print(f"⏳ Salvando {len(validos)} itens no banco...")
            if salvar_lote_sqlite(preparar_dados_finais(validos)):
                print("✅ Banco atualizado!")
            else:
                print("❌ Erro ao salvar no banco.")
    
    return itens_extraidos