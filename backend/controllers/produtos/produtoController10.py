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
    # Remove 'un' e espaços
    stock = re.sub(r'[^\d]', '', str(stock_str))
    try: return float(stock)
    except: return 0.0

# ===================== TRATAMENTO LOADING (TRAVAMENTO) ===================== #
async def verificar_e_recuperar_loading(page) -> bool:
    """
    Verifica se a tela de loading está travada.
    Se estiver visível: Dá refresh na página e aguarda.
    Retorna True se houve recuperação (refresh), False se está tudo ok.
    """
    try:
        # Tenta detectar loading (ajuste o seletor conforme o site, #loading é o padrão)
        if await page.locator("#loading").is_visible(timeout=1000):
            print("⚠️ TELA DE LOADING TRAVADA DETECTADA! Iniciando recuperação...")
            
            # Atualiza a página
            await page.reload()
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass
            
            print("🔄 Página atualizada. Retomando fluxo...")
            return True
    except Exception:
        pass
    
    return False

# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        # Seletor do campo de busca
        selector_busca = "input#codigo"
        
        # Garante que o campo está visível
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
        
        campo = page.locator(selector_busca)
        
        # Limpa e digita com segurança
        await campo.click(force=True)
        await asyncio.sleep(0.2)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        
        print(f"⌨️ Digitando: {codigo}")
        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)
        
        print("🚀 Enter para pesquisar...")
        await page.keyboard.press("Enter")
        
        print(f"⌛ Aguardando resultados para {codigo}...")
        
        # Espera carregar os cards OU o loading travar
        try:
            task_card = asyncio.create_task(page.wait_for_selector(".product-card-modern-pedido", timeout=8000))
            task_loading = asyncio.create_task(page.wait_for_selector("#loading", state="visible", timeout=3000))
            
            done, pending = await asyncio.wait({task_card, task_loading}, return_when=asyncio.FIRST_COMPLETED)
            for t in pending: t.cancel()
        except:
            pass # Pode não ter encontrado nada ou timeout

        await asyncio.sleep(1.5)
        
    except Exception as e:
        print(f"❌ Erro na busca Matriz: {e}")

# ===================== EXTRAÇÃO ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    
    # Seletor do CARD DO PRODUTO
    card_selector = ".product-card-modern-pedido"
    
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
        
        # Nome
        try:
            nome_text = (await card.locator(".product-title").inner_text()).strip()
        except: nome_text = "Produto sem nome"
        
        # Botão ADD (contém metadados)
        btn_add = card.locator("button.add-to-cart")

        # Código
        codigo_fab = await btn_add.get_attribute("data-produto")
        if not codigo_fab:
            codigo_fab = codigo_solicitado

        # Marca
        marca_text = await btn_add.get_attribute("data-fabricante")
        if not marca_text: marca_text = "N/A"

        # Imagem
        link_img = None
        try:
            img_container = card.locator(".product-image-container")
            link_img_attr = await img_container.get_attribute("data-img")
            if link_img_attr:
                if not link_img_attr.startswith("http"):
                    link_img = "http://suportematriz.ddns.net:5006" + link_img_attr
                else:
                    link_img = link_img_attr
        except: pass

        # Preço
        preco_raw = await btn_add.get_attribute("data-preco") # Ex: "19.05"
        if preco_raw:
            preco_num = float(preco_raw)
            preco_visivel = f"R$ {preco_raw.replace('.', ',')}"
        else:
            # Fallback visual
            try:
                preco_visivel = (await card.locator(".product-price").inner_text()).strip()
                preco_num = clean_price(preco_visivel)
            except:
                preco_num = 0.0
                preco_visivel = "R$ 0,00"
        
        # Estoque
        qtd_disponivel = 0.0
        estoque_raw = await btn_add.get_attribute("data-qtdatual")
        if estoque_raw:
            qtd_disponivel = float(estoque_raw)
        else:
            # Fallback visual
            try:
                texto_estoque = (await card.locator("span-estoque-carrinho").inner_text()).strip()
                qtd_disponivel = clean_stock(texto_estoque)
            except: pass

        # Disponibilidade
        tem_estoque = qtd_disponivel > 0

    except Exception as e:
        print(f"⚠ Erro na extração do card: {e}")
        return None

    # --- CONSOLIDAÇÃO ---
    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque and (qtd_disponivel >= quantidade_solicitada)

    regiao_rj = {
        "uf": "RJ", "preco": preco_visivel, "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num), "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel, "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total), "podeComprar": pode_comprar,
        "mensagem": None if pode_comprar else "Estoque insuficiente", "disponivel": tem_estoque
    }

    item_formatado = {
        "codigo": codigo_fab, "nome": nome_text, "marca": marca_text, "imagem": link_img,
        "preco": preco_visivel, "preco_num": preco_num, "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total, "valor_total_formatado": format_brl(valor_total),
        "uf": "RJ", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar, "mensagem": regiao_rj["mensagem"],
        "disponivel": tem_estoque, "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_rj]
    }
    
    print(f"✅ SUCESSO MATRIZ: {codigo_fab} | {format_brl(preco_num)} | Estoque: {qtd_disponivel}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Suporte Matriz",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial10(login_data_ou_page, lista_produtos):
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
        print("⚠️ Lista vazia. Usando teste: 10A1075C")
        lista_produtos = [{"codigo": "10A1075C", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Matriz -> Buscando: {codigo}")
        
        # === LOOP DE RETRY (Para recuperar de travamentos) ===
        while True:
            try:
                # 1. Verifica loading antes
                if await verificar_e_recuperar_loading(page):
                    continue

                await buscar_produto(page, codigo)
                
                # 2. Verifica loading depois
                if await verificar_e_recuperar_loading(page):
                    continue

                resultado = await extrair_dados_produto(page, codigo, qtd)
                
                if resultado:
                    itens_extraidos.append(resultado)
                
                await asyncio.sleep(1) 
                
                # Se deu certo, sai do loop de retry
                break

            except Exception as e:
                print(f"❌ Erro crítico no loop F10: {e}")
                
                # Se for loading, tenta recuperar
                if await verificar_e_recuperar_loading(page):
                    continue
                
                # Se for erro grave, recarrega e pula este item
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