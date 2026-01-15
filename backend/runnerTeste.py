import asyncio
from playwright.async_api import async_playwright

# Importa o Login do Fornecedor 3 (AC Araújo)
from controllers.fornecedores.Fornecedor3Controller import login_acaraujo

# Importa o Controller de Produtos Atualizado
# Nota: Usamos a função 'sequencial' que aceita a lista e faz a extração completa
from controllers.produtos.produtoController3 import processar_lista_produtos_sequencial3

async def main():
    print("🚀 Iniciando Runner de Teste para AC Araújo...")

    async with async_playwright() as p:
        
        # 1. Executa o Login
        browser, context, page = await login_acaraujo(p)

        # Se o login retornou uma página válida, seguimos
        if page:
            print("\n--- ✅ Login OK. Iniciando Pesquisa de Produto ---")
            
            # 2. Cria uma lista de teste (Simulando o que viria do Excel)
            # Coloquei quantidade 2 para testar se ele calcula o valor total corretamente
            lista_teste = [
                {"codigo": "M8183", "quantidade": 2}
            ]
            
            # 3. Chama a função de processamento passando a LISTA
            resultados = await processar_lista_produtos_sequencial3(page, lista_teste)
            
            # 4. Exibe o resumo do que foi extraído
            print("\n--- 📊 Resultado do Teste ---")
            for item in resultados:
                print(f"Produto: {item['nome']}")
                print(f"Código: {item['codigo']}")
                print(f"Preço Unitário: {item['preco_formatado']}")
                print(f"Quantidade Solicitada: {item['qtdSolicitada']}")
                print(f"Valor Total: {item['valor_total_formatado']}")
                print(f"Disponível: {item['disponivel']}")
                print("-" * 30)
            
            # Mantém o navegador aberto um pouco mais para você ver o resultado visualmente
            print("\n🏁 Teste finalizado. Fechando em 5 segundos...")
            await asyncio.sleep(5)
            await browser.close()
        else:
            print("\n❌ Falha crítica: O login não retornou uma página válida.")

if __name__ == "__main__":
    asyncio.run(main())