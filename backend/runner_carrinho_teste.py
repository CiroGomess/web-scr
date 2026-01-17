import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

# 1) Login (Fornecedor 14 - Pellegrino / Sky)
from controllers.fornecedores.Fornecedor16Controller import login_furacao_bypass

# 2) Automação carrinho (Pellegrino)
from controllers.addCarrinho.furacao import processar_lista_produtos_furacao


def log(mensagem):
    hora = datetime.now().strftime("%H:%M:%S")
    print(f"[{hora}] {mensagem}")


async def main():
    lista_itens = [
        {
            "codigo": "3G0919866D",
            "quantidade": 2
        }
    ]

    log("=== INICIANDO TESTE MANUAL (PELLEGRINO / FORNECEDOR 14) ===")

    async with async_playwright() as p:
        # ---------------------------------------------------------
        # PASSO 1: LOGIN
        # ---------------------------------------------------------
        log("1. Executando Login (Fornecedor14Controller)...")

        try:
            browser, context, page = await login_furacao_bypass(p)
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
        # PASSO 2: ADICIONAR AO CARRINHO (Buscar -> Setar qtd -> Botão)
        # ---------------------------------------------------------
        log("2. Iniciando processamento do carrinho (Pellegrino)...")
        log(f"   Produto alvo: {lista_itens[0]['codigo']}")

        try:
            resultado = await processar_lista_produtos_furacao(page, lista_itens)
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
