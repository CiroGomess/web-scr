import asyncio
from playwright.async_api import async_playwright

# 1. Importa o Login do fornecedor 13 (Sky Peças)
# Certifique-se que o arquivo de login se chama Fornecedor13Controller.py e está na pasta certa
from controllers.fornecedores.Fornecedor1Controller import login

# 2. Importa o Processador de produtos do controller 13
from controllers.produtos.produtoController1 import processar_lista_produtos_parallel

async def main():
    async with async_playwright() as p:
        
        # --- LISTA DE TESTE ---
        # Coloque aqui códigos que você sabe que existem na Sky Peças
        lista_produtos = [
            {"codigo": "13479", "quantidade": 3},
            {"codigo": "S440", "quantidade": 2},
            {"codigo": "93306364", "quantidade": 1} # Exemplo do seu teste anterior
        ]

        # 1. Realiza o login na Sky Peças
        print("🤖 Iniciando Robô Sky Peças...")
        browser, context, page = await login(p)
        
        if not page:
            print("❌ Falha no login inicial. Encerrando.")
            return

        # 2. Processamento
        print(f"🚀 Iniciando processamento de {len(lista_produtos)} produtos...")

        await processar_lista_produtos_parallel(page, lista_produtos)

        # 3. Finalização
        # Descomente a linha abaixo se quiser fechar o navegador ao terminar
        # await browser.close()
        print("\n✨ Processamento Sky Peças concluído.")

if __name__ == "__main__":
    asyncio.run(main())