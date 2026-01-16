import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

# 1. Importa o Login específico (Fornecedor 8 - SAMA)
from controllers.fornecedores.Fornecedor8Controller import login_sama_bypass

# 2. Importa a automação de carrinho (SAMA)
from controllers.addCarrinho.samaautopecas import processar_lista_produtos_sama


def log(mensagem):
    hora = datetime.now().strftime("%H:%M:%S")
    print(f"[{hora}] {mensagem}")


async def main():
    # Dados do teste
    lista_itens = [
        {
            "codigo": "GP30120",
            "quantidade": 3
        }
    ]

    log("=== INICIANDO TESTE MANUAL (SAMA / FORNECEDOR 8) ===")

    async with async_playwright() as p:
        # ---------------------------------------------------------
        # PASSO 1: LOGIN
        # ---------------------------------------------------------
        log("1. Executando Login (Fornecedor8Controller)...")

        try:
            browser, context, page = await login_sama_bypass(p)
        except Exception as e:
            log(f"❌ Erro fatal no login: {e}")
            return

        if not page:
            log("❌ Falha: O login não retornou uma página válida.")
            if browser:
                await browser.close()
            return

        log("✅ Login realizado com sucesso! Página ativa.")

        # ---------------------------------------------------------
        # PASSO 2: ADICIONAR AO CARRINHO (SETA QTD + CLICA NO BOTÃO)
        # ---------------------------------------------------------
        log("2. Iniciando processamento do carrinho (SAMA)...")
        log(f"   Produto alvo: {lista_itens[0]['codigo']}")

        try:
            resultado = await processar_lista_produtos_sama(page, lista_itens)
        except Exception as e:
            log(f"❌ Erro durante processamento do carrinho: {e}")
            resultado = None

        # ---------------------------------------------------------
        # RESULTADO E FECHAMENTO
        # ---------------------------------------------------------
        print("\n--- JSON FINAL ---")
        print(json.dumps(resultado, indent=4, ensure_ascii=False))
        print("------------------")

        if browser:
            await browser.close()
            log("Navegador fechado.")


if __name__ == "__main__":
    asyncio.run(main())
