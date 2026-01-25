import asyncio
import random
import json

# ===================== CONFIG ===================== #
LOGIN_URL_ROLES = "https://compreonline.roles.com.br/Account/Login/"
HOME_URL_ROLES = "https://compreonline.roles.com.br/"

USUARIO_ROLES = "autopecasvieira@gmail.com"
SENHA_ROLES = "1186km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/15 Safari/605.1.15"
]

HEADLESS = False 

# ===================== AUXILIARES ===================== #

async def desativar_tutoriais_js(page):
    """Injeta chaves no LocalStorage para evitar que os popovers apareçam via JS"""
    try:
        dados_tutoriais = {
            "tutorial/catalogo/index": ["ok-v1", "ok-v0", "ok-v0"],
            "tutorial/home/index": ["ok-v1", "ok-v2", "ok-v1"]
        }
        # Injeção via evaluate
        await page.evaluate(f"localStorage.setItem('tutoriais', '{json.dumps(dados_tutoriais)}');")
        print("💉 LocalStorage injetado: Tutoriais desativados via Script.")
    except Exception as e:
        print(f"⚠ Erro ao injetar LocalStorage: {e}")

async def fechar_tutorial_roles(page):
    """Fallback: Fecha o popover manualmente se a injeção falhar ou ele persistir"""
    try:
        btn_fechar = page.locator("button.driver-popover-close-btn")
        if await btn_fechar.count() > 0:
            print("💡 Tutorial detectado visualmente. Fechando no botão...")
            await btn_fechar.click()
            await asyncio.sleep(1)
    except:
        pass

# ===================== LOGIN ROLES ===================== #

async def login_roles(p):
    print("\n🔐 Iniciando LOGIN no fornecedor ROLES...")

    browser = await p.chromium.launch(headless=HEADLESS, slow_mo=200)
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1366, 'height': 768}
    )

    page = await context.new_page()

    try:
        # 1. Acessar página de login
        await page.goto(LOGIN_URL_ROLES, wait_until="load", timeout=60000)
        
        # Injeção preventiva no login
        await desativar_tutoriais_js(page)

        # 2. Preencher campos
        await page.fill("#username", USUARIO_ROLES)
        await page.fill("#password", SENHA_ROLES)
        
        print("🚀 Enviando formulário...")
        
        # 3. Clicar e aguardar navegação
        async with page.expect_navigation(url="**/", timeout=60000):
            await page.click("#kt_login_signin_submit")

        # 4. Pós-Login: Reforçar bloqueio e limpar tela
        await page.wait_for_load_state("networkidle")
        
        # Re-injetar para garantir que a home aceite as chaves
        await desativar_tutoriais_js(page)
        
        # Tentar fechar manualmente caso o script do site tenha sido mais rápido que a injeção
        await fechar_tutorial_roles(page)

        current_url = page.url
        if "Account/Login" in current_url:
            print(f"❌ ERRO: Login falhou! Ainda na página: {current_url}")
            return None, None, None

        print(f"✅ Login Roles realizado com sucesso! URL: {current_url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Ocorreu um erro no login: {e}")
        return None, None, None