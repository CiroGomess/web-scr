import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_SKY = "https://cliente.skypecas.com.br/usuario/login"
HOME_URL_SKY = "https://cliente.skypecas.com.br/"

# Dados de acesso atualizados
CNPJ_SKY = "43053953000120"
USUARIO_SKY = "auto"
SENHA_SKY = "1186Km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADLESS = False

# ===================== LOGIN SKY PEÇAS ===================== #

async def login_skypecas(p):
    print("\n🔐 Iniciando LOGIN no fornecedor SKY PEÇAS...")

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
        await page.goto(LOGIN_URL_SKY, wait_until="networkidle", timeout=60000)

        # 2. Preencher CNPJ/CPF (id="txtCNPJCPF")
        await page.wait_for_selector("#txtCNPJCPF", state="visible")
        await page.fill("#txtCNPJCPF", CNPJ_SKY)
        print("👤 CNPJ preenchido.")

        # 3. Preencher Usuário (name="login")
        await page.fill("input[name='login']", USUARIO_SKY)
        print(f"👤 Usuário '{USUARIO_SKY}' preenchido.")

        # 4. Preencher Senha (name="senha")
        await page.fill("input[name='senha']", SENHA_SKY)
        print("🔑 Senha preenchida.")

        # 5. Clicar no botão Entrar (id="btnEntrar")
        print("🚀 Clicando no botão Entrar...")
        
        # O formulário dispara um POST. Aguardamos a navegação para a Home.
        async with page.expect_navigation(timeout=60000):
            await page.click("#btnEntrar")

        # 6. Aguardar estabilização da home
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Verificação: Se a URL ainda contiver /login ou o campo CNPJ persistir, falhou.
        if "/login" in page.url or await page.locator("#txtCNPJCPF").count() > 0:
            print("❌ ERRO: Login Sky Peças falhou! Verifique as credenciais.")
            return None, None, None

        print(f"✅ Login Sky Peças realizado com sucesso! URL: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro inesperado no login da Sky Peças: {e}")
        return None, None, None