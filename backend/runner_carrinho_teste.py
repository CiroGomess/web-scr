import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

# 1) Login (Fornecedor 10 - Suporte Matriz)
from controllers.fornecedores.Fornecedor10Controller import login_matriz_bypass

# 2) Automação carrinho (Suporte Matriz)
from controllers.addCarrinho.suportematriz import processar_lista_produtos_suportematriz


def log(mensagem):
    hora = datetime.now().strftime("%H:%M:%S")
    print(f"[{hora}] {mensagem}")


async def main():
    # Dados do teste
    lista_itens = [
        {
            "codigo": "FLUDS282DU1",
            "quantidade": 10
        }
    ]

    log("=== INICIANDO TESTE MANUAL (SUPORTE MATRIZ / FORNECEDOR 10) ===")

    async with async_playwright() as p:
        # ---------------------------------------------------------
        # PASSO 1: LOGIN
        # ---------------------------------------------------------
        log("1. Executando Login (Fornecedor10Controller)...")

        try:
            browser, context, page = await login_matriz_bypass(p)
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
        # PASSO 2: ADICIONAR AO CARRINHO (Card -> Add -> Modal quantidade -> Confirmar)
        # ---------------------------------------------------------
        log("2. Iniciando processamento do carrinho (Suporte Matriz)...")
        log(f"   Produto alvo: {lista_itens[0]['codigo']}")

        try:
            resultado = await processar_lista_produtos_suportematriz(page, lista_itens)
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
