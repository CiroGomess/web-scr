import asyncio
import re
from datetime import datetime

# ===================== IMPORTAÇÃO DO SERVIÇO DE BANCO ===================== #
try:
    from services.db_saver import salvar_lote_postgres
except ImportError:
    print("⚠️ Aviso: 'services.db_saver' não encontrado. O salvamento no banco será pulado.")
    salvar_lote_postgres = None

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
    # Remove 'un' e espaços
    stock = re.sub(r'[^\d]', '', stock_str)
    try: return float(stock)
    except: return 0.0

# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        # Seletor do campo de busca
        selector_busca = "input#codigo"
        
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
        
        campo = page.locator(selector_busca)
        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        
        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)
        await page.keyboard.press("Enter")
        
        print(f"⌛ Pesquisando {codigo}...")
        
        # Espera carregar os cards de produto
        try:
            await page.wait_for_selector(".product-card-modern-pedido", timeout=8000)
        except:
            pass # Pode não ter encontrado nada
            
        await asyncio.sleep(1.5)
        
    except Exception as e:
        print(f"❌ Erro na busca: {e}")

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
            "uf": "RJ", # Matriz geralmente é RJ (ajuste se precisar)
            "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }

    # Pega o PRIMEIRO card
    card = page.locator(card_selector).first
    
    try:
        # --- EXTRAÇÃO ---
        
        # Nome
        # HTML: <h5 class="product-title">CORREIA V - 10A1075C - DAYCO</h5>
        nome_text = (await card.locator(".product-title").inner_text()).strip()
        
        # Código
        # HTML: <span>...<strong>Código:</strong> 10A1075C</span>
        # Vamos pegar do atributo data-produto do botão se possível, é mais limpo
        btn_add = card.locator("button.add-to-cart")
        codigo_fab = await btn_add.get_attribute("data-produto")
        if not codigo_fab:
            codigo_fab = codigo_solicitado

        # Marca
        # HTML: <span>...<strong>Marca:</strong> DAYCO</span>
        # Ou do data-fabricante
        marca_text = await btn_add.get_attribute("data-fabricante")
        if not marca_text: marca_text = "N/A"

        # Imagem
        # HTML: <div class="product-image-container" data-img="/produtos_img/10A1075C.jpg">
        img_container = card.locator(".product-image-container")
        link_img = await img_container.get_attribute("data-img")
        if link_img:
            # Ajusta URL relativa
            if not link_img.startswith("http"):
                link_img = "http://suportematriz.ddns.net:5006" + link_img
        else:
            link_img = None

        # Preço
        # HTML: <div class="product-price">R$ 19,05</div>
        # Ou data-preco="19.05"
        preco_raw = await btn_add.get_attribute("data-preco") # "19.05"
        if preco_raw:
            preco_num = float(preco_raw)
            preco_visivel = f"R$ {preco_raw.replace('.', ',')}"
        else:
            # Fallback visual
            preco_visivel = (await card.locator(".product-price").inner_text()).strip()
            preco_num = clean_price(preco_visivel)
        
        # Estoque
        # HTML: <span-estoque-carrinho>67 un</span-estoque-carrinho>
        # Ou data-qtdatual="67"
        estoque_raw = await btn_add.get_attribute("data-qtdatual")
        if estoque_raw:
            qtd_disponivel = float(estoque_raw)
        else:
            # Fallback visual
            texto_estoque = (await card.locator("span-estoque-carrinho").inner_text()).strip()
            qtd_disponivel = clean_stock(texto_estoque)

        # Disponibilidade
        tem_estoque = qtd_disponivel > 0

    except Exception as e:
        print(f"⚠ Erro na extração do card: {e}")
        return None

    # --- CONSOLIDAÇÃO ---
    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque and (qtd_disponivel >= quantidade_solicitada)

    regiao_rj = {
        "uf": "RJ",
        "preco": preco_visivel,
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
        "preco": preco_visivel,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "uf": "RJ",
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar,
        "mensagem": regiao_rj["mensagem"],
        "disponivel": tem_estoque,
        "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_rj]
    }
    
    print(f"✅ SUCESSO: {codigo_fab} | {format_brl(preco_num)} | Estoque: {qtd_disponivel}")
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
async def processar_lista_produtos_sequencial10(page, lista_produtos):
    itens_extraidos = []
    
    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste: 10A1075C")
        lista_produtos = [{"codigo": "10A1075C", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Matriz -> Buscando: {codigo}")
        
        try:
            await buscar_produto(page, codigo)
            resultado = await extrair_dados_produto(page, codigo, qtd)
            
            if resultado:
                itens_extraidos.append(resultado)
            
            await asyncio.sleep(1) 

        except Exception as e:
            print(f"❌ Erro crítico no loop F10: {e}")
            await page.reload(wait_until="networkidle")

    # SALVAMENTO
    if itens_extraidos:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]
        
        if validos:
            if salvar_lote_postgres:
                print(f"⏳ Salvando {len(validos)} itens no banco...")
                if salvar_lote_postgres(preparar_dados_finais(validos)):
                    print("✅ Banco atualizado!")
                else:
                    print("❌ Erro ao salvar no banco.")
            else:
                print("ℹ️ Banco não configurado.")
        else:
            print("⚠️ Nada encontrado para salvar.")
    
    return itens_extraidos