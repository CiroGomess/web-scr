import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_SAMA = "https://compreonline.samaautopecas.com.br/Account/Login/"
HOME_URL_SAMA = "https://compreonline.samaautopecas.com.br/"

USUARIO_SAMA = "autopecasvieira@gmail.com"
SENHA_SAMA = "1186km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

HEADLESS = True 

# ===================== LOGIN SAMA ===================== #

async def login_sama(p):
    print("\n🔐 Iniciando LOGIN no fornecedor SAMA...")

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
        await page.goto(LOGIN_URL_SAMA, wait_until="networkidle", timeout=60000)

        # 2. Preencher E-mail (id="username")
        await page.wait_for_selector("#username", state="visible")
        await page.fill("#username", USUARIO_SAMA)
        print("👤 Usuário preenchido.")

        # 3. Preencher Senha (id="password")
        await page.fill("#password", SENHA_SAMA)
        print("🔑 Senha preenchida.")

        # 4. Clicar no botão Entrar (id="kt_login_signin_submit")
        print("🚀 Clicando no botão Entrar...")
        
        # Como o formulário dispara um Submit Javascript, aguardamos a resposta
        await page.click("#kt_login_signin_submit")

        # 5. Aguardar carregamento e redirecionamento
        # Esses sistemas Metronic costumam ser pesados no carregamento inicial
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(4)

        # Verificação de sucesso
        if "Login" in page.url:
            print("❌ ERRO: Login Sama falhou! Verifique as credenciais.")
            return None, None, None

        print(f"✅ Login Sama realizado com sucesso! URL: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro inesperado no login da Sama: {e}")
        return None, None, None