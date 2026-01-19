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

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        # Seletor do campo de busca
        selector_busca = "input#gsearch"
        
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
        
        campo = page.locator(selector_busca)
        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        
        # Digita e pesquisa
        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)
        
        print(f"⌛ Pesquisando {codigo}...")
        await page.keyboard.press("Enter")
        
        # Espera carregar os cards
        try:
            await page.wait_for_selector("tr[ng-controller='RowCtrl']", timeout=10000)
        except:
            pass 
            
        await asyncio.sleep(2)
        
    except Exception as e:
        print(f"❌ Erro na busca Furação: {e}")

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
        # HTML: <span ... class="ng-binding">BICO INJ.EL.PALIO ... </span>
        nome_element = card.locator("div.descricao span.ng-binding").last
        nome_text = (await nome_element.inner_text()).strip()
        
        # Código
        # HTML: <span ... class="ng-binding">IWP065</span>
        try:
            cod_el = card.locator("span.ng-binding").first 
            codigo_fab = (await cod_el.inner_text()).strip()
        except:
            codigo_fab = codigo_solicitado

        # Marca (AJUSTADO)
        # HTML: <div><strong>Marca:</strong> <span class="ng-binding">ORIGINAL-Bicos Inj</span></div>
        marca_text = "N/A"
        try:
            # Pega o <span> que é irmão direto (+) do <strong> que contém o texto 'Marca:'
            marca_el = card.locator("strong:has-text('Marca:') + span")
            if await marca_el.count() > 0:
                marca_text = (await marca_el.inner_text()).strip()
        except: pass

        # Imagem
        img_element = card.locator("div.img img").first
        link_img = await img_element.get_attribute("src")
        if link_img and not link_img.startswith("http"):
            link_img = "https://vendas.furacao.com.br" + link_img

        # Preço
        preco_element = card.locator("span.h3.ng-binding").last
        preco_raw = (await preco_element.inner_text()).strip()
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
        tem_estoque = qtd_disponivel > 0

    except Exception as e:
        print(f"⚠ Erro na extração do card: {e}")
        return None

    # --- CONSOLIDAÇÃO ---
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
async def processar_lista_produtos_sequencial16(page, lista_produtos):
    itens_extraidos = []
    
    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste: IWP065")
        lista_produtos = [{"codigo": "IWP065", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Furação -> Buscando: {codigo}")
        
        try:
            await buscar_produto(page, codigo)
            resultado = await extrair_dados_produto(page, codigo, qtd)
            
            if resultado:
                itens_extraidos.append(resultado)
            
            await asyncio.sleep(1.5) 

        except Exception as e:
            print(f"❌ Erro crítico no loop F16: {e}")
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