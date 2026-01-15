import asyncio
from playwright.async_api import async_playwright

# --- IMPORTS ---
# Login do Fornecedor 6 (Laguna)
from controllers.fornecedores.Fornecedor6Controller import login_laguna_bypass

# Controller de Produtos 6 (Laguna) - NOVO
from controllers.produtos.produtoController6 import processar_lista_produtos_sequencial6

async def main():
    print("🚀 Iniciando Runner de Teste para Fornecedor 6 (Laguna)...")

    async with async_playwright() as p:
        
        # 1. Login (Com Bypass Cloudflare)
        browser, context, page = await login_laguna_bypass(p)

        if page:
            print("\n--- ✅ Login OK. Iniciando Pesquisa de Produto ---")
            
            # 2. Lista de Teste (Código do exemplo fornecido)
            # Código: 9430084214 (Bico Injetor Bosch)
            lista_teste = [
                {"codigo": "9430084214", "quantidade": 2}
            ]
            
            # 3. Chama a função de processamento CORRETA (Controller 6)
            resultados = await processar_lista_produtos_sequencial6(page, lista_teste)
            
            # 4. Exibe Resultados no Console
            print("\n--- 📊 Resultado do Teste ---")
            for item in resultados:
                print(f"Produto: {item['nome']}")
                print(f"Código: {item['codigo']}")
                print(f"Marca: {item['marca']}")
                print(f"Preço Unitário: {item['preco_formatado']}")
                print(f"Total (x{item['qtdSolicitada']}): {item['valor_total_formatado']}")
                print(f"Status: {item['status']}")
                print("-" * 30)
            
            print("\n🏁 Teste finalizado. Fechando em 5 segundos...")
            await asyncio.sleep(5)
            await browser.close()
        else:
            print("\n❌ Falha crítica: O login não retornou uma página válida.")

if __name__ == "__main__":
    asyncio.run(main())