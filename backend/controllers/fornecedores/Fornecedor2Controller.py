import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_ROLES = "https://compreonline.roles.com.br/Account/Login/"
HOME_URL_ROLES = "https://compreonline.roles.com.br/"

USUARIO_ROLES = "autopecasvieira@gmail.com"
SENHA_ROLES = "1186km71"

USER_AGENTS = [
       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/15 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 Chrome/115 Mobile Safari/537.36"
]

HEADLESS = False 

async def login_roles(p):
    print("\n🔐 Iniciando LOGIN no fornecedor ROLES...")

    browser = await p.chromium.launch(headless=HEADLESS, slow_mo=200)
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1366, 'height': 768}
    )

    page = await context.new_page()

    try:
        await page.goto(LOGIN_URL_ROLES, wait_until="load", timeout=60000)
        
        # Preencher campos
        await page.fill("#username", USUARIO_ROLES)
        await page.fill("#password", SENHA_ROLES)
        
        # Clicar e aguardar a navegação especificamente
        print("🚀 Enviando formulário...")
        
        # Usamos wait_for_navigation pois o clique causa um redirecionamento pesado
        async with page.expect_navigation(url="**/", timeout=60000):
            await page.click("#kt_login_signin_submit")

        # Pequena pausa para garantir que os scripts de sessão carreguem
        await asyncio.sleep(3) 

        # Verificação robusta: se o botão de submit ainda existe, o login falhou
        # Se estiver na home ou a URL não contiver 'Account/Login', deu certo.
        current_url = page.url
        
        if "Account/Login" in current_url:
            print(f"❌ ERRO: O site ainda está na página de login ({current_url})")
            return None, None, None

        print(f"✅ Login Roles realizado com sucesso! Estamos em: {current_url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Ocorreu um erro: {e}")
        return None, None, None