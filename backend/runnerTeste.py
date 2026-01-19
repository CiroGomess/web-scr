import asyncio
from playwright.async_api import async_playwright

# --- IMPORTS ---
# Login do Fornecedor 4
from controllers.fornecedores.Fornecedor4Controller import login_fornecedor4

# Controller de Produtos 4
from controllers.produtos.produtoController4 import processar_lista_produtos_sequencial4


async def main():
    print("🚀 Iniciando Runner de Teste (Fornecedor 4)...")

    async with async_playwright() as p:

        # 1) Login
        # O login_fornecedor4 deve retornar (browser, context, page)
        try:
            login_data = await login_fornecedor4(p)
            browser, context, page = login_data
        except Exception as e:
            print(f"\n❌ Falha crítica no login: {e}")
            return

        if not page:
            print("\n❌ Falha crítica: O login não retornou uma página válida.")
            if browser:
                await browser.close()
            return

        print("\n--- ✅ Login OK. Iniciando Pesquisa de Produtos ---")

        # 2) Lista de Teste (todos com quantidade 3)
        lista_teste = [
            {"codigo": "34565", "quantidade": 3},
            {"codigo": "74963", "quantidade": 3},
            {"codigo": "11970", "quantidade": 3},
            {"codigo": "03212", "quantidade": 3},  # mantém zero à esquerda
        ]

        print("   Produtos alvo: " + ", ".join([f"{i['codigo']} (qtd {i['quantidade']})" for i in lista_teste]))

        # 3) Chama a função de processamento
        # IMPORTANTE: Passamos 'login_data' completo para ter acesso ao context
        try:
            resultados = await processar_lista_produtos_sequencial4(login_data, lista_teste)
        except Exception as e:
            print(f"\n❌ Erro durante o processamento da lista: {e}")
            resultados = []

        # 4) Exibe Resultados no Console
        print("\n--- 📊 Resultado do Teste ---")
        if not resultados:
            print("Nenhum resultado retornado.")
        else:
            for item in resultados:
                print(f"Produto: {item.get('nome')}")
                print(f"Código: {item.get('codigo')}")
                print(f"Marca: {item.get('marca')}")
                print(f"Preço Unitário: {item.get('preco_formatado')}")
                print(f"Total: {item.get('valor_total_formatado')}")
                print(f"Estoque: {item.get('qtdDisponivel')}")
                print("-" * 30)

        print("\n🏁 Teste finalizado. Fechando em 5 segundos...")
        await asyncio.sleep(5)

        if browser:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
