import asyncio
import re
import os
from datetime import datetime

# ===================== IMPORTAÇÃO DO SERVIÇO DE BANCO ===================== #
try:
    # Tenta importar a função de salvar no Postgres
    from services.db_saver import salvar_lote_sqlite
except ImportError:
    print("⚠️ Aviso: 'services.db_saver' não encontrado. O salvamento no banco será pulado.")
    salvar_lote_sqlite = None

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

# ===================== AUXILIAR: FECHAR POPUP ===================== #
async def fechar_popup_acaraujo(page):
    try:
        popup = page.locator("#popup")
        if await popup.is_visible():
            print("🍪 Popup de atualização detectado. Fechando...")
            await popup.locator("button:has-text('Fechar')").click()
            await asyncio.sleep(1)
    except Exception:
        pass

# ===================== EXTRAÇÃO DE DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    cards = page.locator(".up-produto")
    total_cards = await cards.count()
    
    if total_cards == 0:
        return {
            "codigo": codigo_solicitado, "nome": "Não encontrado", "preco": "R$ 0,00", 
            "uf": "RJ", "disponivel": False, "regioes": []
        }

    for i in range(total_cards):
        card = cards.nth(i)
        
        # Obtém o SKU para validação
        sku_no_card = await card.locator("#produto-sku-grid b").inner_text()
        sku_no_card = sku_no_card.strip()

        # Lógica de Match (Exato ou Início do SKU)
        if sku_no_card == codigo_solicitado or sku_no_card.startswith(codigo_solicitado):
            try:
                # --- CORREÇÃO DO NOME ---
                # Buscamos o span que contém a descrição, ignorando o que tem texto "SKU:"
                nome_selector = card.locator(".description span.ng-binding:not(:has-text('SKU:'))")
                nome_text = (await nome_selector.inner_text()).strip()
                
                link_img = await card.locator("img.originalImg").first.get_attribute("src")
                preco_raw = await card.locator(".product-price").inner_text()
                preco_num = clean_price(preco_raw)
                
                status_estoque = await card.locator(".produto-status").inner_text()
                status_estoque = status_estoque.strip()
                
                tem_estoque = "Indisponível" not in status_estoque
                qtd_disponivel = 1 if tem_estoque else 0

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
                    "mensagem": None if pode_comprar else "Sem estoque imediato",
                    "disponivel": tem_estoque
                }

                return {
                    "codigo": sku_no_card,
                    "nome": nome_text,
                    "marca": "JAHU",
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
                    "status": status_estoque,
                    "regioes": [regiao_rj]
                }
            except Exception as e:
                print(f"⚠ Erro nos detalhes do card: {e}")
                continue
    return None

# ===================== PREPARAÇÃO DE DADOS PARA O BANCO ===================== #
def preparar_dados_finais(lista_itens):
    """
    Monta o dicionário mestre com o nome do fornecedor fixo: 'Auto Pecas Vieira'
    """
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"), 
        "data_obj": agora, # Objeto datetime para o Banco (Postgres)
        "fornecedror": "Jahu", # <--- NOME DO FORNECEDOR
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== EXECUTOR PRINCIPAL ===================== #
async def processar_lista_produtos_acaraujo(page, lista_produtos):
    itens_extraidos = []
    
    for idx, item in enumerate(lista_produtos):
        codigo = str(item['codigo']).strip()
        print(f"📦 [{idx+1}/{len(lista_produtos)}] Buscando: {codigo}")
        
        try:
            await fechar_popup_acaraujo(page)

            campo_busca = page.locator("#search-input")
            await campo_busca.fill("")
            await campo_busca.type(codigo, delay=100)
            await page.keyboard.press("Enter")
            
            await asyncio.sleep(2) # Espera o Angular processar a busca

            resultado = await extrair_dados_produto(page, codigo, item["quantidade"])
            if resultado:
                itens_extraidos.append(resultado)
                print(f"✅ Extraído: {resultado['nome']} | SKU: {resultado['codigo']}")

        except Exception as e:
            print(f"❌ Erro no loop para o código {codigo}: {e}")

    # ==========================================================
    # 👇👇 SALVAMENTO APENAS NO BANCO DE DADOS 👇👇
    # ==========================================================
    if itens_extraidos:
        # 1. Filtra itens vazios ou com erro se necessário
        validos = [r for r in itens_extraidos if r and r.get("codigo")]
        
        if validos:
            # 2. Prepara os dados
            dados_completos = preparar_dados_finais(validos)

            # 3. Salva no PostgreSQL
            if salvar_lote_sqlite:
                print("⏳ Enviando dados para o PostgreSQL...")
                sucesso = salvar_lote_sqlite(dados_completos)
                if sucesso:
                    print("✅ Dados salvos no banco com sucesso!")
                else:
                    print("❌ Falha ao salvar no banco.")
            else:
                print("ℹ️ Salvamento de banco pulado (módulo não importado).")
    
    return itens_extraidos