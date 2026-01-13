import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_MATRIZ = "http://suportematriz.ddns.net:5006"
HOME_URL_MATRIZ = "http://suportematriz.ddns.net:5006/home" # Ajuste se a home for diferente

# O campo pede e-mail, mas você forneceu o CNPJ. 
# O Playwright preencherá o campo 'email' com este número.
USUARIO_MATRIZ = "43053953000120" 
SENHA_MATRIZ = "VIEIRA"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]


HEADLESS = True 

# ===================== LOGIN MATRIZ ===================== #

async def login_matriz(p):
    print("\n🔐 Iniciando LOGIN no fornecedor MATRIZ...")

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
        await page.goto(LOGIN_URL_MATRIZ, wait_until="networkidle", timeout=60000)

        # 2. Preencher E-mail (id="email")
        await page.wait_for_selector("#email", state="visible")
        await page.fill("#email", USUARIO_MATRIZ)
        print("👤 Usuário/CNPJ preenchido.")

        # 3. Preencher Senha (id="password")
        await page.fill("#password", SENHA_MATRIZ)
        print("🔑 Senha preenchida.")

        # 4. Clicar no botão Entrar (id="loginBtn")
        print("🚀 Clicando no botão Entrar...")
        
        # Como o botão pode ter animações de 'loading', clicamos e aguardamos a navegação
        await page.click("#loginBtn")

        # 5. Aguardar carregamento do painel principal
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Verificação: Se ainda houver o campo de e-mail, o login falhou
        if await page.locator("#email").count() > 0:
            print("❌ ERRO: Login Matriz falhou! Verifique as credenciais.")
            return None, None, None

        print(f"✅ Login Matriz realizado com sucesso! URL: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro inesperado no login da Matriz: {e}")
        return None, None, None