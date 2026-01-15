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

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def garantir_tela_produtos(page):
    """Garante que está na tela de produtos (#/unit004)"""
    if "unit004" in page.url:
        return

    print("📂 Navegando para o menu 'Produtos'...")
    try:
        # Tenta clicar no menu
        menu_produtos = page.locator('a[href="#/unit004"]')
        if await menu_produtos.is_visible():
            await menu_produtos.click(force=True)
        else:
            # Se não achar o menu, força pela URL
            print("⚠️ Menu não visível, forçando URL...")
            await page.goto("https://ecommerce.gb.com.br/#/unit004", wait_until="networkidle")
        
        await asyncio.sleep(3) # Tempo para o Vue.js montar a tela
        
    except Exception as e:
        print(f"⚠️ Erro navegação: {e}")
        await page.goto("https://ecommerce.gb.com.br/#/unit004", wait_until="networkidle")

async def buscar_produto(page, codigo):
    """
    BLINDAGEM: Usa JS para inserir o valor se o input normal falhar
    """
    try:
        # 1. Garante a tela
        await garantir_tela_produtos(page)
        
        # 2. Define o seletor exato
        selector_busca = "#txt-search-simples"
        
        print(f"🔎 Localizando campo de busca: {selector_busca}")
        
        # Espera o input estar no DOM (mesmo que oculto)
        await page.wait_for_selector(selector_busca, state="attached", timeout=20000)
        
        # Tenta clicar no LABEL se o input estiver coberto (comum em Materialize/Vue)
        try:
            await page.click("label[for='txt-search-simples']", force=True, timeout=2000)
        except:
            # Se falhar clicar no label, tenta clicar no input direto com força
            await page.locator(selector_busca).click(force=True)

        await asyncio.sleep(0.5)

        # --- ESTRATÉGIA DE PREENCHIMENTO ---
        print(f"⌨️ Inserindo código: {codigo}")
        
        # Método 1: Playwright padrão
        try:
            await page.fill(selector_busca, str(codigo))
        except:
            print("⚠️ Fill padrão falhou, usando Injeção JS...")
            # Método 2: JavaScript direto (Infalível para inputs travados)
            await page.evaluate(f"""
                var input = document.getElementById('txt-search-simples');
                input.value = '{codigo}';
                input.dispatchEvent(new Event('input', {{bubbles: true}}));
                input.dispatchEvent(new Event('change', {{bubbles: true}}));
            """)
        
        await asyncio.sleep(0.5)
        
        # --- PESQUISAR ---
        print("🚀 Pressionando ENTER...")
        await page.keyboard.press("Enter")
        
        # Clica no ícone de lupa também, só pra garantir
        try:
            await page.click("i.material-icons.prefix:has-text('search')", timeout=1000, force=True)
        except: pass

        print("⏳ Aguardando resultados da tabela...")
        # Espera a tabela (sucesso) OU o aviso de nada encontrado
        try:
            await page.wait_for_selector("tr.destacavel, .alert-warning, .card-panel.red", timeout=10000)
        except:
            pass # Segue para verificação na extração
            
        await asyncio.sleep(2)
        
    except Exception as e:
        print(f"❌ Erro na rotina de busca: {e}")

# ===================== EXTRAÇÃO DOS DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    
    # 1. Verifica se a tabela apareceu
    # O HTML mostra que a linha tem a classe 'destacavel'
    selector_linha = "tr.destacavel"
    
    if await page.locator(selector_linha).count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado (Tabela vazia).")
        return {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "SP", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }

    # 2. Pega a primeira linha
    tr = page.locator(selector_linha).first
    
    try:
        # --- EXTRAÇÃO ---
        # Nome: <h6><b>...</b></h6>
        nome_text = (await tr.locator("h6 b").inner_text()).strip()
        
        # Imagem: div#gb411 img
        link_img = await tr.locator("td:nth-child(1) img").get_attribute("src")
        if link_img and not link_img.startswith("http"):
            link_img = "https://ecommerce.gb.com.br/" + link_img.lstrip("/")

        # Marca
        marca_text = "N/A"
        # Busca a div que tem 'Marca:' e pega o <b> dentro dela
        try:
            marca_el = tr.locator("div.col.s6:has-text('Marca:') b")
            if await marca_el.count() > 0:
                marca_text = (await marca_el.inner_text()).strip()
        except: pass

        # Código GB (Confirmação)
        codigo_fab = codigo_solicitado
        try:
            cod_el = tr.locator("div.col.s6:has-text('Código GB:') b")
            if await cod_el.count() > 0:
                codigo_fab = (await cod_el.inner_text()).strip()
        except: pass

        # Preço: <h5>R$ 50,18</h5> na última coluna
        preco_element = tr.locator("td:last-child h5")
        preco_raw = (await preco_element.inner_text()).strip()
        preco_num = clean_price(preco_raw)
        
        # Disponibilidade (Se aparece na lista com preço, tem estoque)
        tem_estoque = preco_num > 0
        qtd_disponivel = 1.0 if tem_estoque else 0.0

    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

    # --- CONSOLIDAÇÃO ---
    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque

    regiao_sp = {
        "uf": "SP",
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
        "nome": nome_text,
        "marca": marca_text,
        "imagem": link_img,
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "uf": "SP",
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar,
        "mensagem": regiao_sp["mensagem"],
        "disponivel": tem_estoque,
        "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_sp]
    }
    
    print(f"✅ SUCESSO: {codigo_fab} | {format_brl(preco_num)} | {marca_text}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "G&B",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial4(page, lista_produtos):
    itens_extraidos = []
    
    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste: 73512")
        lista_produtos = [{"codigo": "73512", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] GB -> Buscando: {codigo}")
        
        try:
            await buscar_produto(page, codigo)
            resultado = await extrair_dados_produto(page, codigo, qtd)
            
            if resultado:
                itens_extraidos.append(resultado)
            
            await asyncio.sleep(1) 

        except Exception as e:
            print(f"❌ Erro crítico no loop F4: {e}")
            await page.reload(wait_until="networkidle")

    # SALVAMENTO
    if itens_extraidos:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]
        
        if validos:
            if salvar_lote_postgres:
                print(f"⏳ Salvando {len(validos)} itens no banco...")
                if salvar_lote_postgres(preparar_dados_finais(validos)):
                    print("✅ Banco atualizado com sucesso!")
                else:
                    print("❌ Erro ao salvar no banco.")
            else:
                print("ℹ️ Banco não configurado.")
        else:
            print("⚠️ Nenhum produto válido encontrado. Nada será salvo.")
    
    return itens_extraidos