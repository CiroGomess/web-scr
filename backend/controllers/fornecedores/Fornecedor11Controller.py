import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_DPK = "https://www.dpk.com.br/#/login"
HOME_URL_DPK = "https://www.dpk.com.br/#/home"

USUARIO_DPK = "compras2.autopecasvieira@gmail.com"
SENHA_DPK = "1186Km71*"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADLESS = False

# ===================== LOGIN DPK ===================== #

async def login_dpk(p):
    print("\n🔐 Iniciando LOGIN no fornecedor DPK...")

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
        await page.goto(LOGIN_URL_DPK, wait_until="networkidle", timeout=60000)

        # 2. Preencher Email
        # Usamos o formcontrolname pois o ID 'mat-input-2' pode mudar a cada carregamento
        campo_email = page.locator("input[formcontrolname='userPrincipalName']")
        await campo_email.wait_for(state="visible", timeout=15000)
        await campo_email.fill(USUARIO_DPK)
        print("👤 Email preenchido.")

        # 3. Preencher Senha
        campo_senha = page.locator("input[formcontrolname='password']")
        await campo_senha.fill(SENHA_DPK)
        print("🔑 Senha preenchida.")

        # 4. Clicar no botão Entrar
        # Buscamos o botão do tipo submit que contém o texto "Entrar"
        btn_entrar = page.locator("button[type='submit']:has-text('Entrar')")
        
        print("🚀 Clicando no botão Entrar...")
        await btn_entrar.click()

        # 5. Aguardar carregamento pós-login
        # Aplicações Angular costumam processar a rota após o clique
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(40) # Tempo para processar o token e carregar o catálogo

        # Verificação: Se a URL ainda for /login, algo falhou
        if "/login" in page.url:
            print("❌ ERRO: Login DPK falhou! Verifique as credenciais ou mensagens de erro na tela.")
            return None, None, None

        print(f"✅ Login DPK realizado com sucesso! URL: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro inesperado no login da DPK: {e}")
        return None, None, None