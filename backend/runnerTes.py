import asyncio
from playwright.async_api import async_playwright

from controllers.fornecedores.Fornecedor15Controller import login_riojc_bypass
from controllers.produtos.produtoController15 import processar_lista_produtos_sequencial15


async def main():
    print("🚀 Iniciando Runner de Teste (Fornecedor 15 - RioJC)...")

    lista_produtos = [
        {"codigo": "R38826", "quantidade": 1},
        {"codigo": "R02907", "quantidade": 1},
    ]

    print(f"📋 Total de produtos para busca: {len(lista_produtos)}")

    async with async_playwright() as p:
        browser = None
        context = None
        page = None

        try:
            browser, context, page = await login_riojc_bypass(p)
        except Exception as e:
            print(f"\n❌ Falha crítica no login: {e}")
            return

        if not context or not page:
            print("\n❌ Falha crítica: Login não retornou contexto/page válidos.")
            if browser:
                await browser.close()
            return

        print("\n--- ✅ Login OK. Iniciando Pesquisa de Produtos ---")

        try:
            # ✅ CHAMADA CORRETA (sem keyword)
            resultados = await processar_lista_produtos_sequencial15(page, lista_produtos)
        except Exception as e:
            print(f"\n❌ Erro durante o processamento da lista: {e}")
            resultados = []

        print("\n--- 📊 Resultado do Teste ---")
        if not resultados:
            print("Nenhum resultado retornado.")
        else:
            print(f"Total processado com sucesso: {len(resultados)}")
            for item in resultados:
                print(
                    f"[{item.get('codigo')}] "
                    f"{item.get('nome')} | "
                    f"{item.get('preco_formatado')} | "
                    f"Estoque: {item.get('estoque_raw')}"
                )

        print("\n🏁 Teste finalizado. Fechando em 5 segundos...")
        await asyncio.sleep(5)

        try:
            if context:
                await context.close()
            if browser:
                await browser.close()
        except Exception as e:
            print(f"⚠️ Erro ao fechar recursos: {e}")


if __name__ == "__main__":
    asyncio.run(main())
