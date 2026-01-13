import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_ACARAUJO = "https://portal.acaraujo.com.br/entrar"
USUARIO_AC = "autopecasvieira@gmail.com"
SENHA_AC = "Vieira1975@"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADLESS = True 

async def login_acaraujo(p):
    print("\n🔐 Iniciando LOGIN no fornecedor AC ARAÚJO...")

    browser = await p.chromium.launch(headless=HEADLESS, slow_mo=300)
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1366, 'height': 768}
    )

    page = await context.new_page()

    try:
        await page.goto(LOGIN_URL_ACARAUJO, wait_until="networkidle", timeout=60000)

        # 1. Preencher E-mail (usando o ID 'email' que você enviou)
        await page.wait_for_selector("#email", state="visible")
        await page.fill("#email", USUARIO_AC)
        print("👤 E-mail preenchido.")

        # 2. Preencher Senha (usando o name 'senha' que você enviou)
        # Como não tem ID fixo na senha, usamos o seletor de name
        await page.fill("input[name='senha']", SENHA_AC)
        print("🔑 Senha preenchida.")

        # 3. Clicar no botão Entrar
        # Usando a classe 'g-recaptcha' que você identificou
        btn_entrar = page.locator("button.g-recaptcha")
        
        print("🚀 Clicando no botão Entrar (processando captcha invisible)...")
        await btn_entrar.click()

        # 4. Aguardar a navegação pós-login
        # Sites com reCAPTCHA podem demorar alguns segundos extras para validar
        try:
            await page.wait_for_url("**/", timeout=20000) # Espera sair da página de login
            await page.wait_for_load_state("networkidle")
        except:
            print("⚠ Tempo de espera da URL excedido, verificando posição atual...")

        # Verificação final
        if "/entrar" in page.url:
            print("❌ ERRO: Login AC Araújo falhou! Verifique se apareceu desafio de Captcha visual.")
            return None, None, None

        print(f"✅ Login AC Araújo realizado com sucesso! URL: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro inesperado na AC Araújo: {e}")
        return None, None, None