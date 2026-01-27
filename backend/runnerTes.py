import asyncio
from playwright.async_api import async_playwright

# --- IMPORTS ---
from controllers.fornecedores.Fornecedor1Controller import login
from controllers.produtos.produtoController1 import processar_lista_produtos_sequencial


async def main():
    print("🚀 Iniciando Runner de Teste (Fornecedor 1 - PortalComDip)...")

    # ================= LISTA DE PRODUTOS ================= #
    lista_produtos = [
        {"codigo": "31968", "quantidade": 1},
        {"codigo": "16792", "quantidade": 1},
        {"codigo": "21115", "quantidade": 1},
        {"codigo": "21136", "quantidade": 1},
        {"codigo": "18471", "quantidade": 1},
        {"codigo": "14712", "quantidade": 1},
        {"codigo": "21620", "quantidade": 1},
        {"codigo": "12964", "quantidade": 3},
        {"codigo": "13578", "quantidade": 1},
        {"codigo": "29449", "quantidade": 1},
        {"codigo": "03634", "quantidade": 1},
        {"codigo": "10535", "quantidade": 1},
    ]

    print(f"📋 Total de produtos para busca: {len(lista_produtos)}")

    async with async_playwright() as p:
        browser = None
        context = None
        page = None

        # ================= LOGIN ================= #
        try:
            browser, context, page = await login(p)
        except Exception as e:
            print(f"\n❌ Falha crítica no login: {e}")
            return

        if not context:
            print("\n❌ Falha crítica: Login não retornou contexto válido.")
            if browser:
                await browser.close()
            return

        print("\n--- ✅ Login OK. Iniciando Pesquisa de Produtos ---")

        # ================= PROCESSAMENTO (SEQUENCIAL) ================= #
        try:
            resultados = await processar_lista_produtos_sequencial(
                context=context,
                lista_produtos=lista_produtos
            )
        except Exception as e:
            print(f"\n❌ Erro durante o processamento da lista: {e}")
            resultados = []

        # ================= RESULTADOS ================= #
        print("\n--- 📊 Resultado do Teste ---")

        if not resultados:
            print("Nenhum resultado retornado.")
        else:
            print(f"Total processado: {len(resultados)}")

            for item in resultados[-5:]:
                print(
                    f"[{item.get('codigo')}] "
                    f"{item.get('nome')} | "
                    f"{item.get('preco_formatado')}"
                )

        print("\n🏁 Teste finalizado. Fechando em 5 segundos...")
        await asyncio.sleep(5)

        # ================= FECHAR ================= #
        try:
            if context:
                await context.close()
            if browser:
                await browser.close()
        except Exception as e:
            print(f"⚠️ Erro ao fechar recursos: {e}")


if __name__ == "__main__":
    asyncio.run(main())
