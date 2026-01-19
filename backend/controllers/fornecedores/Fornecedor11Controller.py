import asyncio
import random
from playwright.async_api import async_playwright

# ===================== CONFIG DPK ===================== #
LOGIN_URL_DPK = "https://www.dpk.com.br/#/login"
# URL de destino após o login
HOME_URL_DPK = "https://www.dpk.com.br/#/" 

USUARIO_DPK = "compras2.autopecasvieira@gmail.com"
SENHA_DPK = "1186Km71*"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

HEADLESS = True 

async def human_type(page, selector, text):
    """Simula uma digitação humana"""
    try:
        box = await page.locator(selector).bounding_box()
        if box:
            await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        
        await page.click(selector)
        await page.type(selector, text, delay=random.randint(50, 150))
    except Exception as e:
        print(f"⚠️ Erro ao digitar em {selector}: {e}")

async def login_dpk_bypass(p):
    print("\n🔐 Iniciando LOGIN na DPK (Modo Stealth)...")

    args = [
        "--disable-blink-features=AutomationControlled",
        "--start-maximized",
        "--no-sandbox",
        "--disable-infobars"
    ]

    browser = await p.chromium.launch(
        headless=HEADLESS, 
        args=args,
        ignore_default_args=["--enable-automation"] 
    )

    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1366, 'height': 768},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        java_script_enabled=True
    )

    # Bypass manual do navigator.webdriver
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page = await context.new_page()

    try:
        print("🌍 Acessando página da DPK...")
        await page.goto(LOGIN_URL_DPK, wait_until="networkidle", timeout=60000)
        
        # Pausa para o Angular carregar
        await asyncio.sleep(random.uniform(4, 6))

        # --- PREENCHER EMAIL ---
        print("👤 Digitando e-mail...")
        seletor_email = "input[formcontrolname='userPrincipalName']"
        await page.wait_for_selector(seletor_email, state="visible", timeout=20000)
        await human_type(page, seletor_email, USUARIO_DPK)
        
        await asyncio.sleep(random.uniform(1, 2))

        # --- PREENCHER SENHA ---
        print("🔑 Digitando senha...")
        seletor_senha = "input[formcontrolname='password']"
        await human_type(page, seletor_senha, SENHA_DPK)
        
        await asyncio.sleep(random.uniform(1, 2))

        # --- CLICAR ENTRAR ---
        print("🚀 Clicando em Entrar...")
        btn_entrar = page.locator("button[type='submit']:has-text('Entrar')")
        
        if await btn_entrar.is_visible():
            box = await btn_entrar.bounding_box()
            if box:
                await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                await asyncio.sleep(0.5)
            await btn_entrar.click()
        else:
            print("⚠️ Botão de entrar não encontrado, tentando Enter...")
            await page.keyboard.press("Enter")

        # --- AGUARDAR CARREGAMENTO PÓS-LOGIN ---
        print("⏳ Aguardando processamento e redirecionamento...")
        await page.wait_for_load_state("networkidle")
        
        # Espera para garantir que a URL mude
        await asyncio.sleep(10) 

        # --- VALIDAÇÃO DA URL ---
        url_atual = page.url
        print(f"🔎 URL Final: {url_atual}")

        # Verifica se estamos na raiz (/#/) ou se saiu da tela de login
        if "login" not in url_atual and ("/#/" in url_atual or url_atual == HOME_URL_DPK):
             print(f"✅ Login DPK finalizado com sucesso! (Home detectada)")
        else:
             print("⚠️ Aviso: A URL não parece ser a Home padrão. Verifique se o login foi concluído.")
        
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro na DPK: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None