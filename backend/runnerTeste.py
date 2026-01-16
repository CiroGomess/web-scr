import asyncio
from playwright.async_api import async_playwright

# --- IMPORTS ---
# Login do Fornecedor 9 (Solroom)
from controllers.fornecedores.Fornecedor15Controller import login_riojc_bypass

# Controller de Produtos 9 (Solroom)
from controllers.produtos.produtoController15 import processar_lista_produtos_sequencial15

async def main():
    print("🚀 Iniciando Runner de Teste para Fornecedor 9 (Solroom)...")

    async with async_playwright() as p:
        
        # 1. Login
        # O login_solroom retorna (browser, context, page)
        login_data = await login_riojc_bypass(p)
        browser, context, page = login_data

        if page:
            print("\n--- ✅ Login OK. Iniciando Pesquisa de Produto ---")
            
            # 2. Lista de Teste (Código do exemplo que você enviou: 3250237)
            lista_teste = [
                {"codigo": "R32746", "quantidade": 2}
            ]
            
            # 3. Chama a função de processamento
            # IMPORTANTE: Passamos 'login_data' completo para ter acesso ao context
            resultados = await processar_lista_produtos_sequencial15(login_data, lista_teste)
            
            # 4. Exibe Resultados no Console
            print("\n--- 📊 Resultado do Teste ---")
            for item in resultados:
                print(f"Produto: {item['nome']}")
                print(f"Código: {item['codigo']}")
                print(f"Marca: {item['marca']}")
                print(f"Preço Unitário: {item['preco_formatado']}")
                print(f"Total: {item['valor_total_formatado']}")
                print(f"Estoque: {item['qtdDisponivel']}")
                print("-" * 30)
            
            print("\n🏁 Teste finalizado. Fechando em 5 segundos...")
            await asyncio.sleep(5)
            await browser.close()
        else:
            print("\n❌ Falha crítica: O login não retornou uma página válida.")

if __name__ == "__main__":
    asyncio.run(main())