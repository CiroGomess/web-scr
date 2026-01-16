import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

# 1) Login (Fornecedor 12 - Takao)
from controllers.fornecedores.Fornecedor12Controller import login_takao_bypass

# 2) Automação carrinho (Takao)
from controllers.addCarrinho.takao import processar_lista_produtos_takao


def log(mensagem):
    hora = datetime.now().strftime("%H:%M:%S")
    print(f"[{hora}] {mensagem}")


async def main():
    lista_itens = [
        {
            "codigo": "JSCBR LR 30D",  # exemplo do seu controller de pesquisa
            "quantidade": 2
        }
    ]

    log("=== INICIANDO TESTE MANUAL (TAKAO / FORNECEDOR 12) ===")

    async with async_playwright() as p:
        log("1. Executando Login (Fornecedor12Controller)...")

        try:
            browser, context, page = await login_takao_bypass(p)
        except Exception as e:
            log(f"❌ Erro fatal no login: {e}")
            return

        if not page:
            log("❌ Falha: O login não retornou uma página válida.")
            if browser:
                await browser.close()
            return

        log("✅ Login realizado com sucesso! Página ativa.")

        log("2. Iniciando processamento do carrinho (Takao)...")
        log(f"   Produto alvo: {lista_itens[0]['codigo']}")

        try:
            resultado = await processar_lista_produtos_takao(page, lista_itens)
        except Exception as e:
            log(f"❌ Erro durante processamento do carrinho: {e}")
            resultado = None

        print("\n--- JSON FINAL ---")
        print(json.dumps(resultado, indent=4, ensure_ascii=False))
        print("------------------")

        if browser:
            await browser.close()
            log("Navegador fechado.")


if __name__ == "__main__":
    asyncio.run(main())
