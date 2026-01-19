import asyncio
import re
from datetime import datetime

# Variável de controle para remover o tutorial apenas uma vez
bloqueios_removidos = False

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

# ===================== FUNÇÃO DE LIMPEZA ÚNICA (TUTORIAL) ===================== #
async def verificar_bloqueios_unico(page):
    """
    Tenta fechar o tutorial Driver.js APENAS UMA VEZ por sessão.
    """
    global bloqueios_removidos
    
    if not bloqueios_removidos:
        print("🛡️ Verificando bloqueios (Primeira vez na SAMA)...")
        try:
            # Espera 3 segundos para o popup aparecer
            await asyncio.sleep(3)
            
            btn_fechar = page.locator(".driver-popover-close-btn")
            
            # Verifica se está visível
            if await btn_fechar.count() > 0 and await btn_fechar.is_visible():
                print("🛑 Pop-up detectado! Clicando no X...")
                await btn_fechar.click()
                await asyncio.sleep(1) 
                print("✅ Pop-up fechado.")
            else:
                print("👍 Nenhum pop-up apareceu.")
                
            bloqueios_removidos = True
            
        except Exception as e:
            print(f"ℹ️ Erro ao tentar fechar bloqueio: {e}")

# ===================== NAVEGAÇÃO E BUSCA ===================== #
async def buscar_produto(page, codigo):
    """Digita o código no campo #search-prod"""
    try:
        selector_busca = "#search-prod"
        
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
        
        # --- AÇÃO: FECHAR O POP-UP (SÓ NA PRIMEIRA VEZ) ---
        await verificar_bloqueios_unico(page)
        
        # Espera a tabela carregar
        try:
            await page.wait_for_selector("table tbody tr.odd, table tbody tr.even", timeout=8000)
        except:
            pass 
            
    except Exception as e:
        print(f"❌ Erro na busca: {e}")

# ===================== EXTRAÇÃO DOS DADOS ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    
    # Verifica se tem linha na tabela (odd ou even)
    linha_selector = "table tbody tr.odd, table tbody tr.even"
    
    if await page.locator(linha_selector).count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado (Tabela vazia).")
        return {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "RJ", # SAMA é MG
            "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }

    # Pega a PRIMEIRA linha visível
    tr = page.locator(linha_selector).first
    
    try:
        # --- EXTRAÇÃO ---
        # Nome
        # HTML: <span class="d-block font-weight-bold font-size-h6-sm mb-0">Correia Dentada</span>
        nome_element = tr.locator("span.font-weight-bold.font-size-h6-sm")
        nome_text = (await nome_element.inner_text()).strip()
        
        # Marca
        # HTML: <span class="d-block nowrap text-truncate font-weight-light w-125px">ELITE</span>
        marca_element = tr.locator("span.nowrap.text-truncate.font-weight-light")
        marca_text = (await marca_element.inner_text()).strip()

        # Código (Tenta pegar da coluna oculta 'procedencia' ou usa o solicitado)
        # HTML: <span ... class="... procedencia">CT488</span>
        cod_element = tr.locator("span.procedencia")
        if await cod_element.count() > 0:
            codigo_fab = (await cod_element.inner_text()).strip()
        else:
            codigo_fab = codigo_solicitado

        # Imagem
        img_element = tr.locator("div.symbol-label img")
        link_img = await img_element.get_attribute("src")
        if link_img and not link_img.startswith("http"):
            # SAMA usa files.pecas.com.br, mas o src relativo pode variar
            link_img = "https://compreonline.samaautopecas.com.br" + link_img

        # Preço
        # HTML: <span ... class="catalogo-preco ..."> R$ 55,60</span>
        preco_element = tr.locator("span.catalogo-preco")
        preco_raw = (await preco_element.inner_text()).strip()
        preco_num = clean_price(preco_raw)
        
        # Disponibilidade
        # HTML: <input ... class="vit-qtde-table ...">
        input_qtd = tr.locator("input.vit-qtde-table")
        tem_estoque = await input_qtd.count() > 0 and preco_num > 0
        qtd_disponivel = 1.0 if tem_estoque else 0.0

    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

    # --- CONSOLIDAÇÃO ---
    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque

    regiao_mg = {
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
        "nome": nome_text,
        "marca": marca_text,
        "imagem": link_img,
        "preco": preco_raw,
        "preco_num": preco_num,
        "preco_formatado": format_brl(preco_num),
        "valor_total": valor_total,
        "valor_total_formatado": format_brl(valor_total),
        "uf": "MG",
        "qtdSolicitada": quantidade_solicitada,
        "qtdDisponivel": qtd_disponivel,
        "podeComprar": pode_comprar,
        "mensagem": regiao_mg["mensagem"],
        "disponivel": tem_estoque,
        "status": "Disponível" if tem_estoque else "Indisponível",
        "regioes": [regiao_mg]
    }
    
    print(f"✅ SUCESSO SAMA: {codigo_fab} | {format_brl(preco_num)} | {marca_text}")
    return item_formatado

# ===================== DB PREPARER ===================== #
def preparar_dados_finais(lista_itens):
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "SAMA",
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== MAIN LOOP ===================== #
async def processar_lista_produtos_sequencial8(page, lista_produtos):
    # Reinicia controle de popup para cada execução do lote
    global bloqueios_removidos
    bloqueios_removidos = False
    
    itens_extraidos = []
    
    if not lista_produtos:
        print("⚠️ Lista vazia. Usando teste padrão.")
        lista_produtos = [{"codigo": "CT488", "quantidade": 1}]
    elif isinstance(lista_produtos, str):
        lista_produtos = [{"codigo": lista_produtos, "quantidade": 1}]

    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] SAMA -> Buscando: {codigo}")
        
        try:
            await buscar_produto(page, codigo)
            resultado = await extrair_dados_produto(page, codigo, qtd)
            
            if resultado:
                itens_extraidos.append(resultado)
            
            await asyncio.sleep(1) 

        except Exception as e:
            print(f"❌ Erro crítico no loop F8: {e}")
            await page.reload(wait_until="networkidle")

    # SALVAMENTO
    if itens_extraidos:
        validos = [r for r in itens_extraidos if r and r.get("status") != "Não encontrado"]
        
        if validos:
            if salvar_lote_sqlite:
                print(f"⏳ Salvando {len(validos)} itens SAMA no banco...")
                if salvar_lote_sqlite(preparar_dados_finais(validos)):
                    print("✅ Banco atualizado!")
                else:
                    print("❌ Erro ao salvar no banco.")
            else:
                print("ℹ️ Banco não configurado.")
        else:
            print("⚠️ Nada encontrado para salvar.")
    
    return itens_extraidos