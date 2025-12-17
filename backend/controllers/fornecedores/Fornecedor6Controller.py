import asyncio
import random
# Importação corrigida para evitar conflito de módulo
from playwright_stealth import stealth


# ===================== CONFIG ===================== #
LOGIN_URL_LAGUNA = "https://compreonline.lagunaautopecas.com.br/Account/Login/"
HOME_URL_LAGUNA = "https://compreonline.lagunaautopecas.com.br/"

USUARIO_LAGUNA = "autopecasvieira@gmail.com"
SENHA_LAGUNA = "1186km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADLESS = False  # Para Cloudflare, deve ser False

# ===================== LOGIN LAGUNA ===================== #

async def login_laguna(p):
    print("\n🔐 Iniciando LOGIN no fornecedor LAGUNA (Proteção Cloudflare)...")

    # Lançamos o Google Chrome real (channel="chrome")
    browser = await p.chromium.launch(
        headless=HEADLESS, 
        channel="chrome", 
        slow_mo=200,
        args=["--disable-blink-features=AutomationControlled"]
    )

    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1366, 'height': 768},
        locale="pt-BR"
    )

    page = await context.new_page()

    # APLICAÇÃO DO STEALTH CORRIGIDA
    # Esta função camufla o navegador contra detecção de bot
    await stealth(page)

    try:
        print("🌍 Acessando o site...")
        await page.goto(LOGIN_URL_LAGUNA, wait_until="load", timeout=60000)

        # 1. Verificação de Cloudflare
        # Caso o site trave na tela de verificação, o log avisará
        desafio = page.locator("text='Verify you are human'")
        if await desafio.count() > 0:
            print("🛡 Desafio Cloudflare detectado! Resolva o captcha no navegador...")
            # Aguarda o campo de usuário aparecer após você resolver o captcha manualmente
            await page.wait_for_selector("#username", timeout=120000)

        # 2. Preencher Usuário
        await page.wait_for_selector("#username", state="visible")
        await page.fill("#username", USUARIO_LAGUNA)
        print("👤 Usuário preenchido.")

        # 3. Preencher Senha
        await page.fill("#password", SENHA_LAGUNA)
        print("🔑 Senha preenchida.")

        # 4. Clicar no botão Entrar
        print("🚀 Enviando formulário...")
        
        # Usamos expect_navigation para lidar com o redirecionamento pós-login
        try:
            async with page.expect_navigation(timeout=30000):
                await page.click("#kt_login_signin_submit")
        except:
            # Se a navegação demorar, mas o clique for aceito, seguimos
            pass

        # 5. Estabilização da página inicial
        await asyncio.sleep(4)
        await page.wait_for_load_state("load")

        # Verificação final de sucesso
        if "Account/Login" in page.url:
            print("❌ ERRO: O login não avançou. Verifique as credenciais.")
            return None, None, None

        print(f"✅ Login Laguna realizado com sucesso! URL atual: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro crítico no login da Laguna: {e}")
        return None, None, None