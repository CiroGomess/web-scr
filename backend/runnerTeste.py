import asyncio
from playwright.async_api import async_playwright

# --- IMPORTS ---
from controllers.fornecedores.Fornecedor4Controller import login_fornecedor4
# CORREÇÃO: Importar o controller 4, não o 3
from controllers.produtos.produtoController4 import processar_lista_produtos_sequencial4

async def main():
    print("🚀 Iniciando Runner de Teste para Fornecedor 4 (GB)...")

    async with async_playwright() as p:
        
        # 1. Login
        browser, context, page = await login_fornecedor4(p)

        if page:
            print("\n--- ✅ Login OK. Iniciando Pesquisa de Produto ---")
            
            # 2. Lista de Teste (Código que você pediu: 73512)
            lista_teste = [
                {"codigo": "73512", "quantidade": 2}
            ]
            
            # 3. Chama a função de processamento CORRETA (Controller 4)
            resultados = await processar_lista_produtos_sequencial4(page, lista_teste)
            
            # 4. Exibe Resultados
            print("\n--- 📊 Resultado do Teste ---")
            for item in resultados:
                print(f"Produto: {item['nome']}")
                print(f"Código: {item['codigo']}")
                print(f"Marca: {item['marca']}")
                print(f"Preço Unitário: {item['preco_formatado']}")
                print(f"Total: {item['valor_total_formatado']}")
                print("-" * 30)
            
            print("\n🏁 Teste finalizado. Fechando em 5 segundos...")
            await asyncio.sleep(5)
            await browser.close()
        else:
            print("\n❌ Falha crítica: O login não retornou uma página válida.")

if __name__ == "__main__":
    asyncio.run(main())