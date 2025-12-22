import asyncio
import re
import os
import json
from datetime import datetime

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
    # Magento costuma carregar essa div quando não há match exato
    if await page.locator(".message.notice").count() > 0:
        print(f"❌ {codigo_solicitado} não encontrado (Aviso de correspondência próxima).")
        return None

    # 2. Localiza o card do produto principal
    # Usamos seletor rigoroso para evitar os itens dentro dos modais de similares
    item = page.locator("ol.product-items > li.product-item").first
    
    if await item.count() == 0:
        return None

    try:
        # --- AGUARDAR CARREGAMENTO ---
        # Em vez de esperar o preço geral, esperamos o container de preço da ação de compra
        # que é o que realmente importa e está visível.
        selector_preco_real = ".price-action-wrapper .price"
        await item.locator(selector_preco_real).first.wait_for(state="visible", timeout=15000)
        
        # Extração do Nome (Link principal do produto)
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

        # Preço Unitário (Garantindo que pegamos o da área de checkout do card)
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

# ===================== SALVAMENTO E EXECUTOR ===================== #
def salvar_json_final(lista_itens):
    agora = datetime.now()
    dados_finais = {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }
    pasta = "data/hist_dados"
    if not os.path.exists(pasta): os.makedirs(pasta)
    caminho = os.path.join(pasta, f"resultado_rmp_{agora.strftime('%Y%m%d_%H%M%S')}.json")
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados_finais, f, indent=4, ensure_ascii=False)
    return caminho

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
            
            # 2. Aguarda o carregamento da página de resultados
            # Em sites Magento, esperar por 'networkidle' ou um tempo fixo ajuda
            # pois o preço é injetado via JS após o HTML carregar.
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

    if itens_extraidos:
        salvar_json_final(itens_extraidos)
    
    return itens_extraidos