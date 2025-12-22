import asyncio
from playwright.async_api import async_playwright

# 1. Importa o Login do fornecedor 7 (RMP)
from controllers.fornecedores.Fornecedor7Controller import login_rmp

# 2. Importa o Processador de produtos do controller 4
# Nota: Ajustei o nome da função para o padrão que definimos no código anterior
from controllers.produtos.produtoController4 import processar_lista_produtos_sequencial

async def main():
    async with async_playwright() as p:
        # 1. Lista de produtos (incluindo o código 93306364 que você enviou no HTML)
        lista_produtos = [
            {"codigo": "13479", "quantidade": 3},
            {"codigo": "03634", "quantidade": 5},
            {"codigo": "10535", "quantidade": 6},
            {"codigo": "12178", "quantidade": 3},
            {"codigo": "08939", "quantidade": 2},
            {"codigo": "93306364", "quantidade": 1}
        ]

        # 2. Realiza o login na RMP
        # Retorna browser e context para podermos fechar tudo no final
        browser, context, page = await login_rmp(p)
        
        if not page:
            print("❌ Falha no login inicial na RMP. Verifique as credenciais.")
            return

        print(f"🚀 Iniciando processamento de {len(lista_produtos)} produtos na RMP...")

        # 3. Chama a função de extração do Controller 4
        # Ela vai pesquisar um por um, validar se existe, extrair e salvar o JSON
        await processar_lista_produtos_sequencial(page, lista_produtos)

        # 4. Finalização de segurança
        await browser.close()
        print("\n✨ Processamento RMP concluído e navegador fechado.")

if __name__ == "__main__":
    asyncio.run(main())