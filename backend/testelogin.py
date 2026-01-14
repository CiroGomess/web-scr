import asyncio
from playwright.async_api import async_playwright

# CORREÇÃO: Importando a função correta (login_laguna_bypass)
from controllers.fornecedores.Fornecedor18Controller import login_pennacorp_via_vivario

async def testar_acesso():
    print("🚀 Iniciando teste de login FORNECEDOR 6 (Laguna - Bypass)...")
    
    async with async_playwright() as p:
        # CORREÇÃO: Chamando a função correta
        browser, context, page = await login_pennacorp_via_vivario(p)
        
        if page:
            print(f"✅ Sucesso! Logado em: {page.url}")
            # Deixei um tempo maior para você conferir visualmente se o login funcionou
            await asyncio.sleep(10)
            await browser.close()
        else:
            print("❌ O login retornou vazio (falha).")

if __name__ == "__main__":
    asyncio.run(testar_acesso())