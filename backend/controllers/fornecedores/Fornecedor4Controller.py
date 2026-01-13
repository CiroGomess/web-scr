import asyncio
import random

# ===================== CONFIG ===================== #
# Substitua pela URL real de login desse fornecedor
LOGIN_URL_F4 = "https://ecommerce.gb.com.br/#/homeE" 

USUARIO_F4 = "43053953000120"
SENHA_F4 = "@#Compras21975"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]


HEADLESS = True 

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

        # 1. Preencher Login/CNPJ
        await page.wait_for_selector("#username", state="visible")
        await page.fill("#username", USUARIO_F4)
        print("👤 Usuário preenchido.")

        # 2. Preencher Senha
        await page.fill("#password", SENHA_F4)
        print("🔑 Senha preenchida.")

        # 3. Clicar no botão ENTRAR (é uma tag <a> com id btn-logar)
        print("🚀 Clicando no botão logar...")
        await page.click("#btn-logar")

        # 4. Aguardar processamento
        # Como é uma aplicação Vue/Single Page, às vezes a URL não muda instantaneamente
        # Vamos esperar o sumiço do botão de login ou uma navegação
        await asyncio.sleep(4) 
        await page.wait_for_load_state("networkidle")

        # Verificação
        if "login" in page.url.lower():
             # Caso ainda esteja na página de login, tentamos verificar se existe erro na tela
             print("❌ ERRO: Login Fornecedor 4 falhou! Verifique as credenciais.")
             return None, None, None

        print(f"✅ Login Fornecedor 4 realizado com sucesso! URL: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro inesperado no Fornecedor 4: {e}")
        return None, None, None