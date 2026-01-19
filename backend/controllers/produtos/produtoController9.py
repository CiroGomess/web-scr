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

# ===================== BUSCA E NAVEGAÇÃO ===================== #
async def buscar_e_abrir_produto(context, page, codigo):
    try:
        # Seletor do campo de busca
        selector_busca = "input#pesquisa"
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
        
        campo = page.locator(selector_busca)
        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        
        print(f"⌨️ Digitando código: {codigo}")
        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)
        
        print("🚀 Pesquisando...")
        await page.keyboard.press("Enter")
        
        # Espera carregar os resultados (cards)
        try:
            await page.wait_for_selector(".card-body", timeout=10000)
        except:
            print("⚠️ Nenhum resultado encontrado na busca.")
            return None

        # Clica no PRIMEIRO resultado para ver detalhes
        link_detalhe = page.locator("div.card a[href*='/produto/detalhe/']").first
        
        if await link_detalhe.count() == 0:
            print("❌ Card de produto não encontrado.")
            return None

        print("🖱️ Clicando no produto para ver detalhes...")
        
        # Gerencia nova aba
        try:
            async with context.expect_page(timeout=5000) as new_page_info:
                await link_detalhe.click()
            
            nova_pagina = await new_page_info.value
            await nova_pagina.wait_for_load_state("domcontentloaded")
            print(f"✅ Detalhes abertos em NOVA ABA: {nova_pagina.url}")
            return nova_pagina
            
        except:
            # Se não abrir nova aba, assume mesma página
            print("ℹ️ Navegação na MESMA ABA.")
            await page.wait_for_load_state("networkidle")
            return page

    except Exception as e:
        print(f"❌ Erro na busca Solroom: {e}")
        return None

# ===================== EXTRAÇÃO DOS DADOS (DETALHE) ===================== #
async def extrair_dados_detalhe(page, codigo_solicitado, quantidade_solicitada=1):
    try:
        # Garante que carregou os inputs principais
        await page.wait_for_selector("#Codigo", timeout=10000)
        
        # --- EXTRAÇÃO VIA INPUTS ---
        
        # Código Solroom (#Codigo)
        codigo_fab = await page.locator("#Codigo").get_attribute("value")
        if not codigo_fab: codigo_fab = codigo_solicitado
        
        # Descrição (#Descricao)
        nome_text = await page.locator("#Descricao").get_attribute("value")
        
        # Ref. Fábrica (#ReferenciaDeFabrica)
        ref_fabrica = await page.locator("#ReferenciaDeFabrica").get_attribute("value")
        
        # Montadora/Marca (#NumeroOriginal_Fabrica_Descricao)
        marca_text = await page.locator("#NumeroOriginal_Fabrica_Descricao").get_attribute("value")
        if not marca_text: marca_text = "N/A"

        # Preço (h1.display-3 ou display-4)
        preco_element = page.locator("h1[class*='display-']")
        preco_raw = (await preco_element.first.inner_text()).strip()
        preco_num = clean_price(preco_raw)
        
        # Imagem
        img_element = page.locator("img.card-img-top").first
        link_img = await img_element.get_attribute("src")
        if link_img and not link_img.startswith("http"):
            link_img = "https://solroom.com.br" + link_img

        # Estoque / Disponibilidade
        # Se tem botão de comprar/adicionar carrinho, assumimos disponível
        btn_comprar = page.locator("a[href*='/pedido/carrinho/']")
        tem_estoque = await btn_comprar.count() > 0 and preco_num > 0
        qtd_disponivel = 1.0 if tem_estoque else 0.0

        # --- CONSOLIDAÇÃO ---
        valor_total = preco_num * quantidade_solicitada
        pode_comprar = tem_estoque

        regiao_rj = {
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
            "cod_fabrica": ref_fabrica,
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
            "mensagem": regiao_rj["mensagem"],
            "disponivel": tem_estoque,
            "status": "Disponível" if tem_estoque else "Indisponível",
            "regioes": [regiao_rj]
        }
        
        print(f"✅ SUCESSO SOLROOM: {codigo_fab} | {format_brl(preco_num)} | {marca_text}")
        return item_formatado

    except Exception as e:
        print(f"⚠ Erro ao extrair detalhes: {e}")
        return None

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "Fornecedor 9 (Solroom)",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial9(login_data, lista_produtos):
    browser, context, page_inicial = login_data
    
    itens_extraidos = []
    
    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste: 3250237")
        lista_produtos = [{"codigo": "3250237", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Solroom -> Buscando: {codigo}")
        
        # Busca e abre nova aba
        nova_aba = await buscar_e_abrir_produto(context, page_inicial, codigo)
        
        if nova_aba:
            resultado = await extrair_dados_detalhe(nova_aba, codigo, qtd)
            
            if resultado:
                itens_extraidos.append(resultado)
            
            # Fecha a aba de detalhes
            if nova_aba != page_inicial:
                await nova_aba.close()
            
            # Foca na inicial
            await page_inicial.bring_to_front()
            await asyncio.sleep(1) 
        else:
            print("⚠️ Produto não encontrado ou erro na abertura.")

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