import asyncio
import random

# ===================== CONFIG ===================== #

LOGIN_URL_ACARAUJO = "https://portal.acaraujo.com.br/entrar"
HOME_URL_ACARAUJO = "https://portal.acaraujo.com.br/"

USUARIO_AC = "autopecasvieira@gmail.com"
SENHA_AC = "Vieira1975@"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

HEADLESS = False 

# ===================== LOGIN AC ARAUJO ===================== #

async def login_acaraujo(p):
    print("\n🔐 Iniciando LOGIN no fornecedor AC ARAÚJO...")

    browser = await p.chromium.launch(
        headless=HEADLESS,
        slow_mo=200 
    )

    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1366, 'height': 768}
    )

    page = await context.new_page()

    try:
        # Acessa a página de login
        await page.goto(LOGIN_URL_ACARAUJO, wait_until="networkidle", timeout=60000)

        # Preencher Usuário
        # Geralmente esses portais usam inputs do tipo email ou texto
        await page.wait_for_selector("input[type='email'], input[name='email'], input[placeholder*='e-mail']", timeout=15000)
        await page.fill("input[type='email'], input[name='email'], input[placeholder*='e-mail']", USUARIO_AC)
        print("👤 Usuário preenchido.")

        # Preencher Senha
        await page.fill("input[type='password']", SENHA_AC)
        print("🔑 Senha preenchida.")

        # Clicar no botão Entrar
        # Buscando por texto 'Entrar' ou botão do tipo submit
        btn_entrar = page.locator("button:has-text('Entrar'), button[type='submit']")
        
        print("🚀 Enviando formulário...")
        await btn_entrar.click()

        # Aguarda a transição de página
        # Portais modernos às vezes não mudam a URL na hora, então esperamos a Home carregar
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3) # Tempo para processar tokens de sessão

        # Verificação
        if "/entrar" in page.url:
            print("❌ ERRO: Login AC Araújo falhou! Verifique as credenciais.")
            return None, None, None

        print(f"✅ Login AC Araújo realizado com sucesso! Estamos em: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Ocorreu um erro no login da AC Araújo: {e}")
        return None, None, None