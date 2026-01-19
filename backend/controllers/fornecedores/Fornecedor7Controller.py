import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_RMP = "https://loja.rmp.com.br/customer/account/login"
HOME_URL_RMP = "https://loja.rmp.com.br/"

USUARIO_RMP = "fiscal.autopecasvieira@gmail.com"
SENHA_RMP = "autopecasvieira"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

HEADLESS = True   # Mantenha False para visualizar o processo

# ===================== LOGIN RMP ===================== #

async def login_rmp(p):
    print("\n🔐 Iniciando LOGIN no fornecedor RMP...")

    # Lança o navegador seguindo seu padrão original
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
        await page.goto(LOGIN_URL_RMP, wait_until="networkidle", timeout=60000)

        # 2. Preencher E-mail/CNPJ (id="email")
        await page.wait_for_selector("#email", state="visible")
        await page.fill("#email", USUARIO_RMP)
        print("👤 Usuário preenchido.")

        # 3. Preencher Senha (id="pass")
        await page.fill("#pass", SENHA_RMP)
        print("🔑 Senha preenchida.")

        # 4. Clicar no botão Entrar (id="send-login")
        print("🚀 Clicando no botão Entrar...")
        
        # Como é um botão de submit, aguardamos a navegação
        await page.click("#send-login")

        # 5. Aguardar carregamento pós-login
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Verificação simples de sucesso baseada na URL
        if "login" in page.url.lower():
            print("❌ ERRO: Login RMP falhou! Verifique as credenciais.")
            return None, None, None

        print(f"✅ Login RMP realizado com sucesso! URL: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro inesperado no login da RMP: {e}")
        return None, None, None