import asyncio
from playwright.async_api import async_playwright
from utils.xlsx_loader import get_latest_xlsx, load_produtos_from_xlsx

# --- IMPORTAÇÃO DOS CONTROLLERS DE LOGIN (FORNECEDORES) ---
from controllers.fornecedores.Fornecedor1Controller import login as login_f1
from controllers.fornecedores.Fornecedor7Controller import login_rmp
from controllers.fornecedores.Fornecedor2Controller import login_roles
from controllers.fornecedores.Fornecedor5Controller import login_jahu
from controllers.fornecedores.Fornecedor13Controller import login_skypecas

# --- IMPORTAÇÃO DOS CONTROLLERS DE PRODUTOS (EXTRAÇÃO) ---
from controllers.produtos.produtoController1 import processar_lista_produtos_parallel
from controllers.produtos.produtoController7 import processar_lista_produtos_sequencial1
from controllers.produtos.produtoController2 import processar_lista_produtos_sequencial2
from controllers.produtos.produtoController5 import processar_lista_produtos_acaraujo
from controllers.produtos.produtoController13 import processar_lista_produtos_sequencial_sky

async def main():
    async with async_playwright() as p:

        # 1. Buscar XLSX mais recente
        pasta_temp = "data/temp"
        ultimo_arquivo = get_latest_xlsx(pasta_temp)

        if not ultimo_arquivo:
            return {"erro": "Nenhum arquivo XLSX encontrado na pasta /data/temp"}

        print(f"📂 Carregando arquivo: {ultimo_arquivo}")

        # 2. Carregar produtos do arquivo
        lista_produtos = load_produtos_from_xlsx(ultimo_arquivo)

        if not lista_produtos:
            return {"erro": "Nenhum produto válido encontrado no XLSX"}

        print(f"📦 {len(lista_produtos)} produtos carregados para processamento.")

        # --- CONFIGURAÇÃO DOS FORNECEDORES ---
        # Aqui definimos quem vai rodar e qual função usar.
        # 'tipo': 'parallel' envia (context, lista)
        # 'tipo': 'sequencial' envia (page, lista)
        fornecedores_config = [
            {
                "nome": "Fornecedor 1 (Padrão)",
                "login_func": login_f1,
                "process_func": processar_lista_produtos_parallel,
                "tipo": "parallel" # Usa context
            },
            {
                "nome": "Fornecedor 7 (RMP)",
                "login_func": login_rmp,
                "process_func": processar_lista_produtos_sequencial1,
                "tipo": "sequencial" # Usa page
            },
            {
                "nome": "Fornecedor 2 (Roles)",
                "login_func": login_roles,
                "process_func": processar_lista_produtos_sequencial2,
                "tipo": "sequencial"
            },
            {
                "nome": "Fornecedor 5 (Jahu)",
                "login_func": login_jahu,
                "process_func": processar_lista_produtos_acaraujo,
                "tipo": "sequencial"
            },
            {
                "nome": "Fornecedor 13 (Skypecas)",
                "login_func": login_skypecas,
                "process_func": processar_lista_produtos_sequencial_sky,
                "tipo": "sequencial"
            }
        ]

        todos_resultados = []

        # 3. Loop de Execução
        for config in fornecedores_config:
            nome = config["nome"]
            print(f"\n--- 🚀 Iniciando: {nome} ---")
            
            browser = None
            try:
                # Executa o Login
                # Nota: Supondo que suas funções de login já lancem o browser internamente ou retornem os objetos
                # Se suas funções de login esperam o objeto 'p' do playwright, passamos ele.
                browser, context, page = await config["login_func"](p)

                if not page:
                    print(f"❌ Falha no login de {nome}. Pulando...")
                    continue

                print(f"✅ Login {nome} realizado. Extraindo dados...")

                dados_fornecedor = []

                # Executa o Processamento (Diferencia Contexto vs Página)
                if config["tipo"] == "parallel":
                    # O paralelo geralmente usa o contexto para abrir múltiplas abas
                    dados_fornecedor = await config["process_func"](
                        context, 
                        lista_produtos, 
                        batch_size=5
                    )
                else:
                    # O sequencial geralmente navega na mesma página (page)
                    dados_fornecedor = await config["process_func"](
                        page, 
                        lista_produtos
                    )

                # Adiciona os resultados deste fornecedor à lista geral
                if dados_fornecedor:
                    todos_resultados.extend(dados_fornecedor)
                    print(f"📥 {len(dados_fornecedor)} itens processados em {nome}.")
                else:
                    print(f"⚠️ Nenhum dado retornado de {nome}.")

            except Exception as e:
                print(f"🔥 Erro crítico ao processar {nome}: {str(e)}")
            
            finally:
                # Garante o fechamento do navegador deste fornecedor antes de ir para o próximo
                if browser:
                    await browser.close()
                    print(f"🔒 Navegador de {nome} fechado.")

        # 4. Retorno Final Consolidado
        return {
            "status": "ok",
            "total_processado": len(todos_resultados),
            "dados": todos_resultados # Lista única com dados de todos os fornecedores
        }

if __name__ == "__main__":
    # Apenas para teste local do arquivo runner.py
    resultado = asyncio.run(main())
    print(f"\nRESUMO FINAL: {resultado['total_processado']} itens extraídos no total.")