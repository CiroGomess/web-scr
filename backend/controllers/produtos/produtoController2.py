import asyncio
import re
import os
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

# ===================== BLOQUEIOS E TUTORIAIS ===================== #
async def desativar_tutoriais_js(page):
    try:
        # Importante: Como tiramos o 'import json' do topo (se não for usar), 
        # aqui precisamos escrever a string JSON manualmente ou importar json só aqui.
        # Vou manter a string manual para evitar import desnecessário.
        dados_tutoriais = '{"tutorial/catalogo/index": ["ok-v1", "ok-v0", "ok-v0"], "tutorial/home/index": ["ok-v1", "ok-v2", "ok-v1"]}'
        await page.evaluate(f"localStorage.setItem('tutoriais', '{dados_tutoriais}');")
    except: pass

async def fechar_bloqueios_obrigatorio(page):
    try:
        await page.evaluate("""
            document.querySelectorAll('.driver-popover, .driver-fix-stacking, .ins-layout-wrapper, .modal-backdrop')
                    .forEach(el => el.remove());
            document.body.classList.remove('driver-pinnable-post-fixed');
            document.body.style.overflow = 'auto';
        """)
    except: pass

# ===================== LÓGICA DE BUSCA ===================== #
async def buscar_produto(page, codigo):
    selector_busca = "input#search-prod"
    await page.wait_for_selector(selector_busca, timeout=20000)
    await desativar_tutoriais_js(page)
    await fechar_bloqueios_obrigatorio(page)
    
    campo_busca = page.locator(selector_busca)
    await campo_busca.click()
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    await campo_busca.fill(str(codigo))
    await page.keyboard.press("Enter")
    
    print(f"⌛ Pesquisando {codigo}... aguardando 3s.")
    await asyncio.sleep(3) 
    
    try:
        # Espera a tabela atualizar
        await page.wait_for_selector("table tbody tr.odd, table tbody tr.even, .dataTables_empty", timeout=10000)
    except: pass

# ===================== EXTRAÇÃO DIRETA DA TABELA (TR) ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    await fechar_bloqueios_obrigatorio(page)

    # 1. Verifica se o produto foi encontrado
    nao_encontrado = await page.locator(".dataTables_empty, h3:has-text('encontramos')").count() > 0
    
    if nao_encontrado:
        print(f"❌ {codigo_solicitado} não encontrado.")
        # Retorna estrutura vazia no padrão, mas preserva o código
        res_vazio = {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "RJ", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }
        return res_vazio

    # 2. Localiza a primeira linha real da tabela
    tr = page.locator("table tbody tr.odd, table tbody tr.even").first
    if await tr.count() == 0: return None

    try:
        # Extração de dados via seletores da linha (TR)
        marca_text = (await tr.locator("td.dtr-control span.text-truncate").inner_text()).strip()
        nome_text = (await tr.locator("td.dtr-control span.font-weight-bold").inner_text()).strip()
        codigo_fab = (await tr.locator("td.max-w-175px span").inner_text()).strip()
        
        # Imagem
        link_img = await tr.locator("img.h-100").first.get_attribute("src")
        if link_img and not link_img.startswith("http"):
            link_img = "https://compreonline.roles.com.br" + link_img
        
        # Preço (Pegamos o preço da coluna dt-right)
        preco_raw = await tr.locator("td.dt-right span.font-size-h5").last.inner_text()
        preco_num = clean_price(preco_raw)
        
        # Disponibilidade: Se houver botão de "Avise-me" (flaticon-bell), está indisponível
        # Se houver input de quantidade (vit-qtde-table), está disponível
        tem_estoque = await tr.locator("input.vit-qtde-table").count() > 0
        
        qtd_disponivel = 0
        if tem_estoque:
            # Assumimos 1 se disponível, pois a tabela não mostra quantidade exata sem clicar
            qtd_disponivel = 1 
        
    except Exception as e:
        print(f"⚠ Erro na extração da linha: {e}")
        return None

    # 3. Consolidação dos dados (Padrão RJ solicitado)
    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque and preco_num > 0

    # Estrutura interna de regiões
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
        "mensagem": None if pode_comprar else "Produto sem estoque imediato",
        "disponivel": tem_estoque
    }

    # Estrutura Principal do JSON/DB
    return {
        "codigo": codigo_fab,
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

# ===================== PREPARAÇÃO DE DADOS PARA O BANCO ===================== #
def preparar_dados_finais(lista_itens):
    """
    Monta o dicionário mestre com o nome do fornecedor fixo: 'compreonline Roles'
    """
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"), # Texto (não usado no JSON local mais, mas mantido pra log)
        "data_obj": agora, # Objeto datetime para o Banco (Postgres)
        "fornecedror": "compreonline Roles", # <--- NOME DO FORNECEDOR
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== EXECUTOR SEQUENCIAL ===================== #
async def processar_lista_produtos_sequencial2(page, lista_produtos):
    itens_extraidos = []
    
    # Início: garante que está na página de busca
    if page.url == "about:blank" or "compreonline" not in page.url:
        await page.goto("https://compreonline.roles.com.br/", wait_until="networkidle")
    
    for idx, item in enumerate(lista_produtos):
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] Roles -> Buscando: {item['codigo']}")
        try:
            await buscar_produto(page, item["codigo"])
            resultado = await extrair_dados_produto(page, item["codigo"], item["quantidade"])
            
            if resultado:
                itens_extraidos.append(resultado)
            
            await asyncio.sleep(2) 

        except Exception as e:
            print(f"❌ Erro crítico no loop: {e}")
            await page.reload(wait_until="networkidle")

    # ==========================================================
    # 👇👇 SALVAMENTO APENAS NO BANCO DE DADOS 👇👇
    # ==========================================================
    if itens_extraidos:
        # 1. Filtra itens vazios ou com erro se necessário
        validos = [r for r in itens_extraidos if r and r.get("codigo")]
        
        if validos:
            # 2. Prepara os dados
            dados_completos = preparar_dados_finais(validos)

            # 3. Salva no PostgreSQL (Sem salvar JSON local)
            if salvar_lote_postgres:
                print("⏳ Enviando dados para o PostgreSQL...")
                sucesso = salvar_lote_postgres(dados_completos)
                if sucesso:
                    print("✅ Dados salvos no banco com sucesso!")
                else:
                    print("❌ Falha ao salvar no banco.")
            else:
                print("ℹ️ Salvamento de banco pulado (módulo não importado).")
    
    print(f"✅ Processamento finalizado com {len(itens_extraidos)} itens.")
    return itens_extraidos