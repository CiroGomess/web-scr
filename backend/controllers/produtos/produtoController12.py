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
    # Remove R$, espaços e caracteres não numéricos exceto vírgula e ponto
    # Ex: "R$ 1.132,50" -> "1132.50"
    preco = re.sub(r'[^\d,]', '', preco_str)
    preco = preco.replace(",", ".")
    try: return float(preco)
    except: return 0.0

def format_brl(valor):
    if valor is None or valor == 0: return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def clean_stock(stock_str):
    if not stock_str: return 0.0
    # Se tiver "+100", remove o +
    stock = re.sub(r'[^\d]', '', stock_str)
    try: return float(stock)
    except: return 0.0

# ===================== BUSCA ===================== #
async def buscar_produto(page, codigo):
    try:
        # Seletor do campo de busca
        selector_busca = "input#inputSearch"
        
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
        
        campo = page.locator(selector_busca)
        
        # Limpa e Digita
        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        
        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)
        
        # Pesquisa
        print(f"⌛ Pesquisando {codigo}...")
        await page.keyboard.press("Enter")
        
        # --- ESPERA ESTRATÉGICA (SITE LENTO) ---
        print("⏳ Aguardando carregamento dos cards (Takao é lento)...")
        
        # Espera o componente do card aparecer
        try:
            await page.wait_for_selector("app-card-produto-home", timeout=15000)
            # Espera mais um pouco para o PREÇO renderizar (geralmente carrega depois do layout)
            await asyncio.sleep(4) 
        except:
            pass # Pode não ter encontrado nada
            
    except Exception as e:
        print(f"❌ Erro na busca Takao: {e}")

# ===================== EXTRAÇÃO ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    
    # Seletor do componente CARD
    card_selector = "app-card-produto-home"
    
    if await page.locator(card_selector).count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado.")
        return {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "RJ", # Takao tem várias filiais, assumindo padrão
            "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }

    # Pega o PRIMEIRO card
    card = page.locator(card_selector).first
    
    try:
        # --- EXTRAÇÃO ---
        
        # Nome/Modelo (Ex: JSCBR LR 30D)
        # HTML: <span class="modelo"><b>JSCBR LR 30D </b></span>
        nome_element = card.locator("span.modelo b")
        nome_text = (await nome_element.inner_text()).strip()
        
        # Descrição (Ex: Junta Completa...)
        # HTML: <div class="descricao"> Junta Completa... </div>
        try:
            desc_el = card.locator("div.descricao")
            descricao = (await desc_el.inner_text()).strip()
            # Concatena nome + descrição para ficar mais completo
            nome_completo = f"{nome_text} - {descricao}"
        except:
            nome_completo = nome_text

        # Código (Usa o nome/modelo extraído como código, pois na Takao é o SKU)
        codigo_fab = nome_text

        # Marca (Takao é fabricante próprio, então geralmente é Takao)
        marca_text = "Takao"

        # Imagem
        img_element = card.locator("img.image")
        link_img = await img_element.get_attribute("src")
        # Se precisar corrigir URL
        # if link_img and not link_img.startswith("http"): ...

        # Preço
        # HTML: <span class="preco"> R$ 1.132,50 ... </span>
        # Tem vários preços (por filial), pegamos o primeiro visível
        preco_element = card.locator("span.preco").first
        preco_raw = (await preco_element.inner_text()).split("\n")[0].strip() # Remove texto da filial se vier junto
        preco_num = clean_price(preco_raw)
        
        # Estoque (Total)
        # O HTML da tabela de variações mostra colunas. A coluna "TOTAL" tem o valor.
        # HTML: <div ... id="texto-total">TOTAL</div> ... <div ...> +100 </div>
        # Vamos tentar pegar o valor da última coluna da linha da tabela
        qtd_disponivel = 0.0
        try:
            # Pega a linha de valores da tabela
            # A estrutura é complexa, mas o valor total costuma ser o último div da linha 'row' dentro de 'tabela-body'
            linha_valores = card.locator(".tabela-body .row").first
            colunas = linha_valores.locator("div[class*='col-']")
            
            # O total geralmente é a penúltima ou última coluna antes do botão
            # Vamos tentar pegar o texto que tem números ou "+100"
            count = await colunas.count()
            if count > 0:
                # Tenta varrer as colunas de trás pra frente para achar o total
                for i in range(count - 2, -1, -1): # Pula o botão (última)
                    texto = await colunas.nth(i).inner_text()
                    if texto.strip():
                        val = clean_stock(texto)
                        if val > 0:
                            qtd_disponivel = val
                            break
        except Exception as ex_stock:
            print(f"⚠️ Erro ao ler estoque Takao: {ex_stock}")

        # Disponibilidade
        # Se tem botão "Adicionar" visível
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
async def processar_lista_produtos_sequencial12(page, lista_produtos):
    itens_extraidos = []
    
    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste: JSCBR LR 30D")
        lista_produtos = [{"codigo": "JSCBR LR 30D", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Takao -> Buscando: {codigo}")
        
        try:
            await buscar_produto(page, codigo)
            resultado = await extrair_dados_produto(page, codigo, qtd)
            
            if resultado:
                itens_extraidos.append(resultado)
            
            await asyncio.sleep(1.5) 

        except Exception as e:
            print(f"❌ Erro crítico no loop F12: {e}")
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