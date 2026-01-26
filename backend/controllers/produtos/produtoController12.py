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
    preco = re.sub(r'[^\d,]', '', preco_str)
    preco = preco.replace(",", ".")
    try: return float(preco)
    except: return 0.0

def format_brl(valor):
    if valor is None or valor == 0: return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def clean_stock(stock_str):
    if not stock_str: return 0.0
    stock = re.sub(r'[^\d]', '', stock_str)
    try: return float(stock)
    except: return 0.0

# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        selector_busca = "input#inputSearch"
        
        # TIMEOUT AUMENTADO (60s) - Site lento
        await page.wait_for_selector(selector_busca, state="visible", timeout=90000)
        
        campo = page.locator(selector_busca)
        
        # Limpa e Digita (garantindo que o campo limpou)
        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.5)
        
        await campo.fill(str(codigo))
        await asyncio.sleep(1) # Pausa para o site reconhecer a digitação
        
        print(f"⌛ Pesquisando {codigo}...")
        await page.keyboard.press("Enter")
        
        # --- ESPERA ESTRATÉGICA (SITE LENTO) ---
        print("⏳ Aguardando carregamento dos cards (Takao é lento)...")
        
        # Espera o componente do card aparecer (AUMENTADO PARA 45s)
        try:
            await page.wait_for_selector("app-card-produto-home", timeout=90000)
            # Espera extra para renderização final dos preços
            await asyncio.sleep(8) 
        except:
            print("⚠️ Timeout aguardando cards (pode não ter resultados).")
            pass 
            
    except Exception as e:
        print(f"❌ Erro na busca Takao: {e}")

# ===================== EXTRAÇÃO ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    
    card_selector = "app-card-produto-home"
    
    # Verifica rápido se tem card
    if await page.locator(card_selector).count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado (Nenhum card visível).")
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
        
        # Nome/Modelo
        nome_element = card.locator("span.modelo b")
        # Timeout interno no locator caso o elemento demore a renderizar dentro do card
        if await nome_element.count() > 0:
            nome_text = (await nome_element.inner_text()).strip()
        else:
            nome_text = str(codigo_solicitado)

        # Descrição
        try:
            desc_el = card.locator("div.descricao")
            descricao = (await desc_el.inner_text()).strip()
            nome_completo = f"{nome_text} - {descricao}"
        except:
            nome_completo = nome_text

        codigo_fab = nome_text
        marca_text = "Takao"

        # Imagem
        img_element = card.locator("img.image")
        link_img = None
        if await img_element.count() > 0:
            link_img = await img_element.get_attribute("src")

        # Preço
        # Aumentei a tolerância para pegar o preço
        preco_raw = "0,00"
        try:
            preco_element = card.locator("span.preco").first
            await preco_element.wait_for(state="visible", timeout=5000)
            text_p = await preco_element.inner_text()
            preco_raw = text_p.split("\n")[0].strip()
        except:
            pass
            
        preco_num = clean_price(preco_raw)
        
        # Estoque
        qtd_disponivel = 0.0
        try:
            linha_valores = card.locator(".tabela-body .row").first
            if await linha_valores.count() > 0:
                colunas = linha_valores.locator("div[class*='col-']")
                count = await colunas.count()
                if count > 0:
                    # Varrer de trás pra frente
                    for i in range(count - 2, -1, -1):
                        texto = await colunas.nth(i).inner_text()
                        if texto.strip():
                            val = clean_stock(texto)
                            if val > 0:
                                qtd_disponivel = val
                                break
        except Exception as ex_stock:
            print(f"⚠️ Erro ao ler estoque: {ex_stock}")

        # Disponibilidade
        btn_add = card.locator("button.btn-adicionar")
        tem_estoque = await btn_add.is_visible() and (qtd_disponivel > 0 or preco_num > 0)

    except Exception as e:
        print(f"⚠ Erro na extração do card: {e}")
        return None

    # --- CONSOLIDAÇÃO ---
    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque

    regiao_es = {
        "uf": "RJ",
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "podeComprar": pode_comprar,
        "mensagem": None if pode_comprar else "Indisponível",
        "disponivel": tem_estoque
    }

    item_formatado = {
        "codigo": codigo_fab,
        "nome": nome_completo,
        "marca": marca_text,
        "imagem": link_img,
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "uf": "ES",
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar,
        "mensagem": regiao_es["mensagem"],
        "disponivel": tem_estoque,
        "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_es]
    }
    
    print(f"✅ SUCESSO TAKAO: {codigo_fab} | {format_brl(preco_num)} | Estoque: {qtd_disponivel}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Takao",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial12(login_data_ou_page, lista_produtos):
    itens_extraidos = []
    
    # --- CORREÇÃO DO ERRO DE TUPLA ---
    # Se receber (browser, context, page), pega só a page
    if isinstance(login_data_ou_page, (tuple, list)) and len(login_data_ou_page) >= 3:
        page = login_data_ou_page[2]
    else:
        page = login_data_ou_page

    if not page:
        print("❌ Erro: page inválida (não veio do login).")
        return []
    # ---------------------------------
    
    if not lista_produtos:
        # Produto de teste padrão se vier vazio
        lista_produtos = [{"codigo": "31968", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]
    elif isinstance(lista_produtos, list):
         # Normaliza lista de strings para dicts
        normalized = []
        for item in lista_produtos:
            if isinstance(item, str):
                normalized.append({"codigo": item, "quantidade": 1})
            elif isinstance(item, dict):
                normalized.append(item)
        lista_produtos = normalized

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Takao -> Buscando: {codigo}")
        
        try:
            await buscar_produto(page, codigo)
            
            # Pequeno delay antes de extrair para garantir que o DOM estabilizou
            await asyncio.sleep(2)
            
            resultado = await extrair_dados_produto(page, codigo, qtd)
            
            if resultado:
                itens_extraidos.append(resultado)
            
            # Delay entre produtos para não travar o site lento
            await asyncio.sleep(3) 

        except Exception as e:
            print(f"❌ Erro crítico no loop F12: {e}")
            try:
                await page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(5)
            except:
                pass

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