import asyncio
import re
from datetime import datetime

# ===================== IMPORTAÇÃO DO SERVIÇO DE BANCO ===================== #
try:
    from services.db_saver import salvar_lote_postgres
except ImportError:
    print("⚠️ Aviso: 'services.db_saver' não encontrado. O salvamento no banco será pulado.")
    salvar_lote_postgres = None

# ===================== AUXILIARES DE FORMATAÇÃO ===================== #
def clean_price(preco_str):
    if not preco_str: return 0.0
    # Remove R$, espaços e caracteres não numéricos exceto vírgula e ponto
    preco = re.sub(r'[^\d,]', '', preco_str)
    # Substitui vírgula por ponto para converter para float
    preco = preco.replace(",", ".")
    try: return float(preco)
    except: return 0.0

def format_brl(valor):
    if valor is None or valor == 0: return "R$ 0,00"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def clean_stock(stock_str):
    """Limpa a string de estoque (ex: '424.000' -> 424.0)"""
    if not stock_str: return 0.0
    try:
        # Remove ponto de milhar se houver, mantendo a lógica de float padrão
        # Se o site usa 424.000 para 424, precisamos tratar.
        # Geralmente em HTML input number, . é decimal.
        return float(stock_str)
    except: return 0.0

# ===================== LÓGICA DE BUSCA ===================== #
async def buscar_produto(page, codigo):
    # Seletor específico do AC Araújo
    selector_busca = "input.search__input[name='s']"
    
    try:
        await page.wait_for_selector(selector_busca, state="visible", timeout=20000)
        
        campo = page.locator(selector_busca)
        await campo.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        
        await campo.fill(str(codigo))
        await asyncio.sleep(0.5)
        await page.keyboard.press("Enter")
        
        print(f"⌛ Pesquisando {codigo}... aguardando 4s.")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(4) 
        
    except Exception as e:
        print(f"❌ Erro ao buscar produto: {e}")

# ===================== EXTRAÇÃO DOS DADOS DO CARD ===================== #
async def extrair_dados_produto(page, codigo_solicitado, quantidade_solicitada=1):
    
    # 1. Verifica se encontrou resultados
    selector_card = ".products-list__item .product-card"
    
    # Se não tiver nenhum card, retorna estrutura vazia padronizada
    if await page.locator(selector_card).count() == 0:
        print(f"❌ {codigo_solicitado} não encontrado.")
        
        # Estrutura vazia igual ao Controller 2
        res_vazio = {
            "codigo": codigo_solicitado, "nome": None, "marca": None, "imagem": None,
            "preco": "R$ 0,00", "preco_num": 0.0, "preco_formatado": "R$ 0,00",
            "valor_total": 0.0, "valor_total_formatado": "R$ 0,00",
            "uf": "RJ", "qtdSolicitada": quantidade_solicitada, "qtdDisponivel": 0,
            "podeComprar": False, "disponivel": False, "status": "Não encontrado",
            "regioes": []
        }
        return res_vazio

    # 2. Pega o primeiro card da lista
    card = page.locator(selector_card).first
    
    try:
        # --- EXTRAÇÃO VIA SELETORES DO CARD ---
        
        # Nome
        elemento_nome = card.locator(".product-card__name a")
        nome_text = (await elemento_nome.inner_text()).strip()
        
        # Marca e Código (Dos atributos data)
        marca_text = await elemento_nome.get_attribute("data-marca")
        codigo_fab = await elemento_nome.get_attribute("data-codigo-produto")
        if not codigo_fab: codigo_fab = codigo_solicitado

        # Imagem
        img_element = card.locator(".product-card__image img")
        link_img = await img_element.get_attribute("src")
        
        # Preço
        preco_element = card.locator(".product-card__new-price")
        preco_raw = (await preco_element.inner_text()).strip()
        preco_num = clean_price(preco_raw)
        
        # Disponibilidade e Estoque
        # O estoque está no atributo 'max' do input
        input_qtd = card.locator("input.input-number__input")
        max_stock_attr = await input_qtd.get_attribute("max") # ex: "424.000"
        
        qtd_disponivel = clean_stock(max_stock_attr)
        
        # Se tem botão de adicionar e preço > 0, está disponível
        btn_adicionar = card.locator("button.product-card__addtocart")
        tem_estoque = await btn_adicionar.is_visible() and qtd_disponivel > 0

    except Exception as e:
        print(f"⚠ Erro na extração do card: {e}")
        return None

    # 3. Consolidação dos dados (Padrão RJ solicitado)
    valor_total = preco_num * quantidade_solicitada
    pode_comprar = tem_estoque and (qtd_disponivel >= quantidade_solicitada)

    # Estrutura interna de regiões
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
        "mensagem": None if pode_comprar else "Quantidade solicitada indisponível",
        "disponivel": tem_estoque
    }

    # Estrutura Principal do JSON/DB
    return {
        "codigo": codigo_fab,
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

# ===================== PREPARAÇÃO DE DADOS PARA O BANCO ===================== #
def preparar_dados_finais(lista_itens):
    """
    Monta o dicionário mestre com o nome do fornecedor fixo: 'AC Araújo'
    """
    agora = datetime.now()
    return {
        "data_processamento_lote": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "data_obj": agora,
        "fornecedror": "AC Araújo", # <--- NOME DO FORNECEDOR
        "total_itens": len(lista_itens),
        "itens": lista_itens
    }

# ===================== EXECUTOR SEQUENCIAL (AC ARAÚJO) ===================== #
async def processar_lista_produtos_sequencial3(page, lista_produtos):
    itens_extraidos = []
    
    # Validação da página correta
    if "portal.acaraujo.com.br" not in page.url:
        print("⚠️ Página incorreta detectada. Redirecionando para home...")
        await page.goto("https://portal.acaraujo.com.br/home", wait_until="networkidle")

    # Loop pelos produtos
    for idx, item in enumerate(lista_produtos):
        codigo = item["codigo"]
        # Pega a quantidade do Excel, ou usa 1 se não tiver
        qtd = item.get("quantidade", 1)
        
        print(f"\n📦 [{idx+1}/{len(lista_produtos)}] AC Araújo -> Buscando: {codigo} (Qtd: {qtd})")
        
        try:
            # 1. Pesquisa
            await buscar_produto(page, codigo)
            
            # 2. Extrai (Passando a quantidade desejada)
            resultado = await extrair_dados_produto(page, codigo, qtd)
            
            if resultado:
                itens_extraidos.append(resultado)
                # Print de validação visual
                print(f"   ↳ {resultado['nome']} | {resultado['preco_formatado']} | Total: {resultado['valor_total_formatado']}")
            
            await asyncio.sleep(2) 

        except Exception as e:
            print(f"❌ Erro crítico no loop: {e}")
            await page.reload(wait_until="networkidle")

    # ==========================================================
    # 👇👇 SALVAMENTO NO BANCO DE DADOS 👇👇
    # ==========================================================
    if itens_extraidos:
        # 1. Filtra itens válidos
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
    
    print(f"✅ Processamento finalizado com {len(itens_extraidos)} itens.")
    return itens_extraidos