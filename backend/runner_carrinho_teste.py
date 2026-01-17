import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

# 1) Login (Fornecedor 17 - PLS Web / Odapel)
from controllers.fornecedores.Fornecedor17Controller import login_pls_bypass

# 2) Automação carrinho (PLS Web / Odapel)
from controllers.addCarrinho.odapel import processar_lista_produtos_odapel


def log(mensagem):
    hora = datetime.now().strftime("%H:%M:%S")
    print(f"[{hora}] {mensagem}")


async def main():
    # código do produto -> 5235.3
    lista_itens = [
        {
            "codigo": "8833.1",
            "quantidade": 3
        }
    ]

    log("=== INICIANDO TESTE MANUAL (PLS WEB / ODAPEL - FORNECEDOR 17) ===")

    async with async_playwright() as p:
        # ---------------------------------------------------------
        # PASSO 1: LOGIN
        # ---------------------------------------------------------
        log("1. Executando Login (Fornecedor17Controller)...")

        browser = None
        try:
            browser, context, page = await login_pls_bypass(p)
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
        # PASSO 2: ADICIONAR AO CARRINHO (Buscar -> ENTER -> Qtd -> Sim)
        # ---------------------------------------------------------
        log("2. Iniciando processamento do carrinho (PLS Web / Odapel)...")
        log(f"   Produto alvo: {lista_itens[0]['codigo']}")

        try:
            resultado = await processar_lista_produtos_odapel(page, lista_itens)
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
