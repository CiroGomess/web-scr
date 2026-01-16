import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

# 1. Importa o Login específico (Fornecedor 4 - GB)
from controllers.fornecedores.Fornecedor4Controller import login_fornecedor4

# 2. Importa a automação de pedido (GB)
from controllers.addCarrinho.gb import processar_lista_produtos_gb


def log(mensagem):
    hora = datetime.now().strftime("%H:%M:%S")
    print(f"[{hora}] {mensagem}")


async def main():
    # Dados do teste (exemplo)
    lista_itens = [
        {
            "codigo": "34372",
            "quantidade": 3
        }
    ]

    log("=== INICIANDO TESTE MANUAL (GB / FORNECEDOR 4) ===")

    async with async_playwright() as p:
        # ---------------------------------------------------------
        # PASSO 1: LOGIN
        # ---------------------------------------------------------
        log("1. Executando Login (Fornecedor4Controller)...")

        # O controller de login retorna (browser, context, page)
        try:
            browser, context, page = await login_fornecedor4(p)
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
        # PASSO 2: FAZER PEDIDO (SETA QUANTIDADE)
        # ---------------------------------------------------------
        log("2. Iniciando processamento do pedido (GB)...")
        log(f"   Produto alvo: {lista_itens[0]['codigo']}")

        # Chama a função do GB passando a página já logada
        try:
            resultado = await processar_lista_produtos_gb(page, lista_itens)
        except Exception as e:
            log(f"❌ Erro durante processamento do pedido: {e}")
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
