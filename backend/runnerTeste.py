import asyncio
from playwright.async_api import async_playwright

# --- IMPORTS ---
# Login do Fornecedor 14 (Sky/Pellegrino)
from controllers.fornecedores.Fornecedor14Controller import login_sky_bypass

# Controller de Produtos 14 (Sky/Pellegrino) - NOVO
from controllers.produtos.produtoController14 import processar_lista_produtos_sequencial14

async def main():
    print("🚀 Iniciando Runner de Teste para Fornecedor 14 (Sky/Pellegrino)...")

    async with async_playwright() as p:
        
        # 1. Login (Com Bypass Cloudflare/Stealth se configurado)
        browser, context, page = await login_sky_bypass(p)

        if page:
            print("\n--- ✅ Login OK. Iniciando Pesquisa de Produto ---")
            
            # 2. Lista de Teste (Código solicitado: HG 33013)
            lista_teste = [
                {"codigo": "HG 33013", "quantidade": 2}
            ]
            
            # 3. Chama a função de processamento CORRETA (Controller 14)
            resultados = await processar_lista_produtos_sequencial14(page, lista_teste)
            
            # 4. Exibe Resultados no Console
            print("\n--- 📊 Resultado do Teste ---")
            for item in resultados:
                print(f"Produto: {item['nome']}")
                print(f"Código: {item['codigo']}")
                print(f"Marca: {item['marca']}")
                print(f"Preço Unitário: {item['preco_formatado']}")
                print(f"Total (x{item['qtdSolicitada']}): {item['valor_total_formatado']}")
                print(f"Status: {item['status']}")
                print(f"Estoque: {item['qtdDisponivel']}")
                print("-" * 30)
            
            print("\n🏁 Teste finalizado. Fechando em 5 segundos...")
            await asyncio.sleep(5)
            await browser.close()
        else:
            print("\n❌ Falha crítica: O login não retornou uma página válida.")

if __name__ == "__main__":
    asyncio.run(main())