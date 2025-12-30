import asyncio
import re
import os
import json
from datetime import datetime

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

def limpar_codigo(texto):
    """Remove espaços e caracteres especiais para comparação"""
    if not texto: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(texto)).upper()

# ===================== EXTRAÇÃO DE DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    
    # 1. Verifica se existem cards de produto na tela
    cards = page.locator(".bx_produto")
    count_cards = await cards.count()

    if count_cards == 0:
        print(f"❌ {codigo_solicitado} não encontrado (Nenhum card .bx_produto).")
        return None

    print(f"🔎 Encontrados {count_cards} itens. Verificando correspondência exata...")

    # 2. Itera sobre os cards para achar o código exato
    item_alvo = None
    
    for i in range(count_cards):
        card = cards.nth(i)
        
        # --- VERIFICAÇÃO DE SEGURANÇA (CÓDIGO) ---
        try:
            # Pega o texto dentro de <strong> na div .codfab
            # HTML: <div class="fleft codfab">Cód. Fáb: <strong>S440</strong></div>
            cod_fab_site = await card.locator(".codfab strong").inner_text()
            
            # Limpa para comparar (ex: "S440" == "S440")
            cod_buscado_limpo = limpar_codigo(codigo_solicitado)
            cod_site_limpo = limpar_codigo(cod_fab_site)

            # Se não bater o código de fábrica, tenta ver o N/N (Número Original/Interno)
            # HTML: <div class="fleft codnn">N/N: 168919K</div>
            match_found = False
            if cod_buscado_limpo == cod_site_limpo:
                match_found = True
            else:
                # Tentativa secundária pelo N/N caso a busca seja pelo código interno
                try:
                    cod_nn_text = await card.locator(".codnn").inner_text() # "N/N: 168919K"
                    if cod_buscado_limpo in limpar_codigo(cod_nn_text):
                        match_found = True
                        cod_fab_site = codigo_solicitado # Assume o código buscado para o JSON
                except:
                    pass

            if match_found:
                item_alvo = card
                print(f"✅ Correspondência confirmada: Site '{cod_fab_site}' == Buscado '{codigo_solicitado}'")
                break # Encontrou, para de procurar
            else:
                print(f"item {i+1}: Código '{cod_site_limpo}' não bate com '{cod_buscado_limpo}'. Pulando...")
        
        except Exception as e:
            continue

    # Se rodou tudo e não achou o item exato
    if not item_alvo:
        print(f"⚠️ Item encontrado na busca, mas códigos não conferem.")
        return None

    try:
        # --- EXTRAÇÃO DOS DADOS DO ITEM ALVO ---
        
        # Nome
        # HTML: <div class="nome">PALHETA DIANTEIRA 16"</div>
        nome_text = await item_alvo.locator(".nome").inner_text()

        # Marca
        # HTML: <div class="fornecedor">DYNA</div>
        try:
            marca_text = await item_alvo.locator(".fornecedor").inner_text()
        except:
            marca_text = "N/A"

        # Imagem
        # HTML: <img ... src="/imagens/produtos/thumbs/168919K.jpg">
        # Vamos pegar o src e adicionar o domínio se for relativo
        try:
            link_img_rel = await item_alvo.locator(".foto img").first.get_attribute("src")
            if link_img_rel and not link_img_rel.startswith("http"):
                link_img = "https://cliente.skypecas.com.br" + link_img_rel
            else:
                link_img = link_img_rel
        except:
            link_img = ""

        # Preço
        # HTML: <span class="preco_final">34,84</span>
        try:
            preco_raw = await item_alvo.locator(".preco_final").inner_text()
        except:
            preco_raw = "0,00"
        
        preco_num = clean_price(preco_raw)

        # Estoque
        # HTML: <a ... class="lkEstoqueProduto">76 <span class="lkEstoqueFilial">...</span></a>
        # O inner_text pode vir "76 E.F.". Vamos pegar só o número.
        qtd_disponivel = 0
        try:
            estoque_text = await item_alvo.locator(".lkEstoqueProduto").inner_text()
            # Pega o primeiro grupo de números encontrado
            match_estoque = re.search(r'(\d+)', estoque_text)
            if match_estoque:
                qtd_disponivel = int(match_estoque.group(1))
        except:
            qtd_disponivel = 0

        # Disponibilidade lógica
        tem_estoque = qtd_disponivel > 0 and preco_num > 0
        
        # Cálculos Finais
        valor_total = preco_num * quantidade_solicitada
        pode_comprar = tem_estoque

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
            "codigo": codigo_solicitado,
            "nome": nome_text.strip(),
            "marca": marca_text.strip(),
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
        print(f"⚠ Erro ao ler dados do card Sky Peças: {e}")
        return None

# ===================== SALVAMENTO E EXECUTOR ===================== #


async def processar_lista_produtos_sequencial_sky(page, lista_produtos):
    itens_extraidos = []
    
    # Seletor do input de busca (do topo do site)
    selector_input = "#inpCodigo"

    for idx, item in enumerate(lista_produtos):
        codigo = str(item['codigo']).strip()
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] SKY -> Buscando: {codigo}")
        
        try:
            # 1. Garante que o campo de busca está visível
            await page.wait_for_selector(selector_input, timeout=10000)
            campo = page.locator(selector_input)
            
            # 2. Limpa e Digita o código
            await campo.click()
            await page.fill(selector_input, "") 
            await campo.type(codigo, delay=100)
            
            # 3. Dispara a busca (Enter)
            await page.keyboard.press("Enter")
            
            # 4. Aguarda carregamento
            # O seletor .bx_produto garante que os resultados carregaram
            try:
                # Espera ou o produto aparecer OU a mensagem de nenhum registro
                await asyncio.wait([
                    page.wait_for_selector(".bx_produto", timeout=5000),
                    page.wait_for_selector("text='Nenhum registro'", timeout=5000)
                ], return_when=asyncio.FIRST_COMPLETED)
            except:
                pass # Segue para tentar extrair, se falhar retorna None
            
            await asyncio.sleep(1) # Estabilização final

            # 5. Extração com Validação
            resultado = await extrair_dados_produto(page, codigo, item["quantidade"])
            
            if resultado:
                itens_extraidos.append(resultado)
                print(f"✅ Extraído: {resultado['nome']} | {resultado['preco_formatado']}")
            else:
                print(f"⚠️ Produto não identificado ou código divergente.")

        except Exception as e:
            print(f"❌ Falha no loop Sky: {e}")
            await page.goto("https://cliente.skypecas.com.br/", wait_until="networkidle")

 
    
    return itens_extraidos