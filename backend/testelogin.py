import asyncio
from playwright.async_api import async_playwright
# Troque aqui para testar o Fornecedor 3
from controllers.fornecedores.Fornecedor13Controller import login_skypecas

async def testar_acesso():
    print("🚀 Iniciando teste de login FORNECEDOR 6...")
    async with async_playwright() as p:
        browser, context, page = await login_skypecas(p)
        
        if page:
            print(f"✅ Sucesso! Logado em: {page.url}")
            await asyncio.sleep(5)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(testar_acesso())