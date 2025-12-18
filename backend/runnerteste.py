import asyncio
from playwright.async_api import async_playwright
from controllers.fornecedores.Fornecedor2Controller import login_roles
from controllers.produtos.produtoController2 import processar_lista_produtos_sequencial

async def main():
    async with async_playwright() as p:
        # 1. Lista de produtos para processamento sequencial
        lista_produtos = [
            {"codigo": "13479", "quantidade": 3},
            {"codigo": "03634", "quantidade": 5},
            {"codigo": "10535", "quantidade": 6},
            {"codigo": "12178", "quantidade": 3},
            {"codigo": "08939", "quantidade": 2},
            {"codigo": "03637", "quantidade": 1}
        ]

        # 2. Realiza o login e obtém a página já autenticada
        # browser e context são mantidos para fechar ao final
        browser, context, page = await login_roles(p)
        
        if not page:
            print("❌ Falha no login inicial. Verifique as credenciais ou a conexão.")
            return

        print(f"🚀 Iniciando processamento de {len(lista_produtos)} produtos sequencialmente...")

        # 3. Chama a função sequencial passando a 'page'
        # Esta função vai pesquisar, extrair e salvar o JSON automaticamente
        await processar_lista_produtos_sequencial(page, lista_produtos)

        # 4. Finalização
        await browser.close()
        print("\n✨ Processamento concluído e navegador fechado.")

if __name__ == "__main__":
    asyncio.run(main())