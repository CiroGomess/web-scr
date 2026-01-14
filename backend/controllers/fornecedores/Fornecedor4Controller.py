import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_F4 = "https://ecommerce.gb.com.br/#/homeE" 

USUARIO_F4 = "43053953000120"
SENHA_F4 = "@#Compras21975"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADLESS = False 

async def login_fornecedor4(p):
    print("\n🔐 Iniciando LOGIN no FORNECEDOR 4...")

    browser = await p.chromium.launch(headless=HEADLESS, slow_mo=200)
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1366, 'height': 768}
    )

    page = await context.new_page()

    try:
        # Acessa a página
        await page.goto(LOGIN_URL_F4, wait_until="networkidle", timeout=60000)

        # 1. Preencher Usuário
        await page.wait_for_selector("#username", state="visible")
        await page.fill("#username", USUARIO_F4)
        print("👤 Usuário preenchido.")

        # 2. Preencher Senha
        await page.fill("#password", SENHA_F4)
        print("🔑 Senha preenchida.")

        # 3. Clicar no botão ENTRAR
        # AQUI ESTÁ O TRUQUE: Usamos :has-text("ENTRAR") para ignorar o botão de cadastro
        print("🚀 Clicando no botão ENTRAR...")
        
        # O seletor abaixo diz: Procure um link (a) com id btn-logar QUE TENHA o texto 'ENTRAR'
        await page.click("a#btn-logar:has-text('ENTRAR')")

        # 4. Aguardar o login processar
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(20) # Aumentei um pouco para garantir

        print(f"✅ Ação de login realizada! URL Atual: {page.url}")
        
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro no Fornecedor 4: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None