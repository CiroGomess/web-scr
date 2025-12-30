import asyncio
from playwright.async_api import async_playwright

# 1. Importa o Login do Fornecedor (Supondo que seja o Fornecedor2 ou similar)
# Ajuste o nome do arquivo se necessário (ex: FornecedorRolesController)
from controllers.fornecedores.Fornecedor7Controller import login_rmp 

# 2. Importa o Controller de Produtos da Roles (produtoController2.py)
from controllers.produtos.produtoController7 import processar_lista_produtos_sequencial

async def main():
    async with async_playwright() as p:
        
        # --- LISTA DE PRODUTOS ---
        lista_produtos = [
            {"codigo": "13479", "quantidade": 3},
            {"codigo": "03634", "quantidade": 5},
            {"codigo": "10535", "quantidade": 6},
            {"codigo": "12178", "quantidade": 3},
            {"codigo": "08939", "quantidade": 2},
            {"codigo": "93306364", "quantidade": 1}
        ]

        print("🤖 Iniciando Robô Roles...")

        # 1. Faz o Login 
        # IMPORTANTE: login_roles retorna (browser, context, page)
        browser, context, page = await login_rmp(p)

        if not page:
            print("❌ Falha no login. Encerrando.")
            return

        print(f"🚀 Iniciando processamento de {len(lista_produtos)} produtos...")

        # 2. Chama a função de extração SEQUENCIAL
        # ⚠️ CORREÇÃO AQUI: Passamos 'page' e não 'context'
        # Porque o código sequencial navega na mesma aba
        await processar_lista_produtos_sequencial(page, lista_produtos)

        # 3. Fecha o navegador
        await browser.close()
        print("\n✨ Processamento finalizado.")

if __name__ == "__main__":
    asyncio.run(main())