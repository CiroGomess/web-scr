import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_SOLROOM = "https://solroom.com.br/login/entrar"
HOME_URL_SOLROOM = "https://solroom.com.br/"

USUARIO_SOLROOM = "autopecasvieira@gmail.com"
SENHA_SOLROOM = "Vieira001"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADLESS = True 

# ===================== LOGIN SOLROOM ===================== #

async def login_solroom(p):
    print("\n🔐 Iniciando LOGIN no fornecedor SOLROOM...")

    browser = await p.chromium.launch(
        headless=HEADLESS,
        slow_mo=300
    )

    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        locale="pt-BR",
        viewport={'width': 1366, 'height': 768}
    )

    page = await context.new_page()

    try:
        # 1. Acessar a página de Login
        await page.goto(LOGIN_URL_SOLROOM, wait_until="networkidle", timeout=60000)

        # 2. Preencher Login (id="Login")
        await page.wait_for_selector("#Login", state="visible")
        await page.fill("#Login", USUARIO_SOLROOM)
        print("👤 Usuário preenchido.")

        # 3. Preencher Senha (id="Senha")
        await page.fill("#Senha", SENHA_SOLROOM)
        print("🔑 Senha preenchida.")

        # 4. Clicar no botão Login
        # Usamos o seletor de tipo submit para garantir que clicamos no botão correto
        print("🚀 Clicando no botão Login...")
        
        async with page.expect_navigation(timeout=60000):
            await page.click("button[type='submit']")

        # 5. Aguardar estabilização da home
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Verificação: Se a URL ainda contiver 'login', o acesso falhou
        if "login" in page.url.lower():
            print("❌ ERRO: Login Solroom falhou! Verifique as credenciais.")
            return None, None, None

        print(f"✅ Login Solroom realizado com sucesso! URL: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro inesperado no login da Solroom: {e}")
        return None, None, None