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
    # Remove tudo exceto números e vírgula
    preco = re.sub(r'[^\d,]', '', preco_str)
    # Troca vírgula por ponto
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
async def navegar_para_pedido(page):
    """Navega até a tela de PVW - Pedido e aba Produtos"""
    try:
        # Se já estiver na URL certa, não faz nada
        if "/Movimentacao" in page.url:
            return

        print("📂 Navegando para o menu 'PVW - Pedido'...")
        # Clica no link do menu
        menu_pedido = page.locator("a[href='/Movimentacao']")
        if await menu_pedido.is_visible():
            await menu_pedido.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"⚠️ Erro ao navegar para Pedido: {e}")

async def ativar_aba_produtos(page):
    """Clica na aba 'Produtos' (#tabs-2)"""
    try:
        # Verifica se a aba já está ativa ou visível
        aba_produtos = page.locator("a[href='#tabs-2']")
        
        # Clica na aba se o input de busca ainda não estiver visível
        if not await page.locator("#codPeca").is_visible():
            print("📑 Clicando na aba 'Produtos'...")
            await aba_produtos.click()
            await asyncio.sleep(1) # Tempo para aba trocar
    except Exception as e:
        print(f"⚠️ Erro ao ativar aba Produtos: {e}")

async def buscar_produto(page, codigo):
    try:
        await navegar_para_pedido(page)
        await ativar_aba_produtos(page)
        
        # Localiza o campo de busca
        selector_busca = "#codPeca"
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
        
        campo = page.locator(selector_busca)
        
        # Limpa e Digita
        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        
        print(f"⌨️ Digitando código: {codigo}")
        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)
        
        print("🚀 Pressionando ENTER...")
        await page.keyboard.press("Enter")
        
        # Espera a grid carregar (jqGrid usa tr.jqgrow)
        print("⏳ Aguardando resultados...")
        try:
            # Espera aparecer alguma linha na tabela
            await page.wait_for_selector("tr.jqgrow", timeout=5000)
        except:
            pass 
            
        await asyncio.sleep(1.5)
        
    except Exception as e:
        print(f"❌ Erro na busca PLS: {e}")

# ===================== EXTRAÇÃO DOS DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    
    # Seletor da linha da grid (jqGrid)
    linhas = page.locator("tr.jqgrow")
    
    if await linhas.count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado.")
        return {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "SP", # PLS Web (Odapel) geralmente é SP/MG, ajuste se souber
            "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }

    # Pega a PRIMEIRA linha
    tr = linhas.first
    
    try:
        # --- EXTRAÇÃO POR POSIÇÃO DAS COLUNAS (TDs) ---
        colunas = tr.locator("td")
        
        # Índice 0: Código (1867.8)
        codigo_fab = (await colunas.nth(0).inner_text()).strip()
        
        # Índice 1: Cód. Fábrica (2122E) - opcional, útil
        # cod_fabrica = (await colunas.nth(1).inner_text()).strip()
        
        # Índice 2: Descrição (MAQUINA- LATARIA)
        nome_text = (await colunas.nth(2).inner_text()).strip()
        
        # Índice 3: Fabricante (ZINNI E GUELL LTDA)
        marca_text = (await colunas.nth(3).inner_text()).strip()
        
        # Índice 7: Quantidade (9) -> Estoque
        estoque_raw = (await colunas.nth(7).inner_text()).strip()
        qtd_disponivel = clean_stock(estoque_raw)
        
        # Índice 9: Valor Líquido (101,58) -> Preço
        preco_raw = (await colunas.nth(9).inner_text()).strip()
        preco_num = clean_price(preco_raw)
        
        # Imagem: Não disponível diretamente na grid desse sistema
        link_img = None 

        # Disponibilidade
        tem_estoque = qtd_disponivel > 0 and preco_num > 0

    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

    # --- CONSOLIDAÇÃO ---
    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque and (qtd_disponivel >= quantidade_solicitada)

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
        "uf": "SP",
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar,
        "mensagem": regiao_sp["mensagem"],
        "disponivel": tem_estoque,
        "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_sp]
    }
    
    print(f"✅ SUCESSO PLS: {codigo_fab} | {format_brl(preco_num)} | Estoque: {qtd_disponivel}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "PlsWeb", # <--- NOME SOLICITADO
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial17(page, lista_produtos):
    itens_extraidos = []
    
    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste: 1867.8")
        lista_produtos = [{"codigo": "1867.8", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] PLS -> Buscando: {codigo}")
        
        try:
            await buscar_produto(page, codigo)
            resultado = await extrair_dados_produto(page, codigo, qtd)
            
            if resultado:
                itens_extraidos.append(resultado)
            
            await asyncio.sleep(1) 

        except Exception as e:
            print(f"❌ Erro crítico no loop F17: {e}")
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