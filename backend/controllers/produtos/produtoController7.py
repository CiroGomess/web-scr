import asyncio
import re
from datetime import datetime

# ===================== IMPORTAÇÃO DO SERVIÇO DE BANCO ===================== #
try:
    # Tenta importar a função de salvar no Postgres
    from services.db_saver import salvar_lote_postgres
except ImportError:
    print("⚠️ Aviso: 'services.db_saver' não encontrado. O salvamento no banco será pulado.")
    salvar_lote_postgres = None

# ===================== AUXILIARES DE FORMATAÇÃO ===================== #
def clean_price(preco_str):
    if not preco_str: return 0.0
    preco = re.sub(r'[^\d,]', '', preco_str)
    preco = preco.replace(",", ".")
    try: return float(preco)
    except: return 0.0

def format_brl(valor):
    if valor is None or valor == 0: return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ===================== EXTRAÇÃO DE DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    # 1. Verifica se a mensagem de "Nenhum resultado encontrado" apareceu
    if await page.locator(".message.notice").count() > 0:
        print(f"❌ {codigo_solicitado} não encontrado (Aviso de correspondência próxima).")
        return None

    # 2. Localiza o card do produto principal
    item = page.locator("ol.product-items > li.product-item").first
    
    if await item.count() == 0:
        return None

    try:
        # --- AGUARDAR CARREGAMENTO ---
        selector_preco_real = ".price-action-wrapper .price"
        await item.locator(selector_preco_real).first.wait_for(state="visible", timeout=15000)
        
        # Extração do Nome
        nome_text = (await item.locator(".product-item-name .product-item-link").first.inner_text()).strip()
        
        # Código do Fabricante e Marca
        try:
            cod_fab_site = (await item.locator(".cod-fabricante span").inner_text()).strip()
            marca_text = (await item.locator(".fabricante span").inner_text()).strip()
        except:
            cod_fab_site = codigo_solicitado
            marca_text = "N/A"

        # Imagem
        link_img = await item.locator("img.product-image-photo").first.get_attribute("src")

        # Preço Unitário
        preco_raw = await item.locator(selector_preco_real).first.inner_text()
        preco_num = clean_price(preco_raw)

        # Estoque via data-stock
        stock_attr = await item.get_attribute("data-stock")
        qtd_disponivel = int(stock_attr) if stock_attr else 0
        tem_estoque = qtd_disponivel > 0

        valor_total = preco_num * quantidade_solicitada
        pode_comprar = tem_estoque and preco_num > 0

        regiao_rj = {
            "uf": "RJ",
            "preco": preco_raw.strip(),
            "preco_num": preco_num,
            "preco_formatado": format_brl(preco_num),
            "qtdSolicitada": quantidade_solicitada,
            "qtdDisponivel": qtd_disponivel,
            "valor_total": valor_total,
            "valor_total_formatado": format_brl(valor_total),
            "podeComprar": pode_comprar,
            "mensagem": None if pode_comprar else "Sem estoque",
            "disponivel": tem_estoque
        }

        return {
            "codigo": cod_fab_site,
            "nome": nome_text,
            "marca": marca_text,
            "imagem": link_img,
            "preco": preco_raw.strip(),
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

    except Exception as e:
        print(f"⚠ Erro na extração RMP: {e}")
        return None

# ===================== PREPARAÇÃO DE DADOS PARA O BANCO ===================== #
def preparar_dados_finais(lista_itens):
    """
    Monta o dicionário mestre com o nome do fornecedor fixo: 'RMP'
    """
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"), 
        "data_obj": agora, # Objeto datetime para o Banco (Postgres)
        "fornecedror": "RMP", # <--- NOME DO FORNECEDOR
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== EXECUTOR SEQUENCIAL ===================== #
async def processar_lista_produtos_sequencial(page, lista_produtos):
    itens_extraidos = []
    selector_input = "#search-cod-fab-input"

    for idx, item in enumerate(lista_produtos):
        codigo = str(item['codigo']).strip()
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] RMP -> Buscando: {codigo}")
        
        try:
            # 1. Limpa e Digita
            await page.wait_for_selector(selector_input, timeout=10000)
            campo = page.locator(selector_input)
            await campo.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await campo.type(codigo, delay=100)
            await page.keyboard.press("Enter")
            
            # 2. Aguarda o carregamento
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2) 

            # 3. Extração
            resultado = await extrair_dados_produto(page, codigo, item["quantidade"])
            
            if resultado:
                itens_extraidos.append(resultado)
                print(f"✅ Extraído: {resultado['nome']} | Preço: {resultado['preco_formatado']}")

        except Exception as e:
            print(f"❌ Falha no loop RMP: {e}")
            await page.reload()

    # ==========================================================
    # 👇👇 SALVAMENTO APENAS NO BANCO DE DADOS 👇👇
    # ==========================================================
    if itens_extraidos:
        # 1. Filtra itens vazios ou com erro
        validos = [r for r in itens_extraidos if r and r.get("codigo")]
        
        if validos:
            # 2. Prepara os dados
            dados_completos = preparar_dados_finais(validos)

            # 3. Salva no PostgreSQL
            if salvar_lote_postgres:
                print("⏳ Enviando dados para o PostgreSQL...")
                sucesso = salvar_lote_postgres(dados_completos)
                if sucesso:
                    print("✅ Dados salvos no banco com sucesso!")
                else:
                    print("❌ Falha ao salvar no banco.")
            else:
                print("ℹ️ Salvamento de banco pulado (módulo não importado).")
    
    return itens_extraidos