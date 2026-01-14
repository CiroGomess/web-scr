import asyncio
import random
from playwright.async_api import async_playwright

# ===================== CONFIG LAGUNA ===================== #
LOGIN_URL_LAGUNA = "https://compreonline.lagunaautopecas.com.br/Account/Login/"
USUARIO_LAGUNA = "autopecasvieira@gmail.com"
SENHA_LAGUNA = "1186km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

async def human_type(page, selector, text):
    """Simula uma digitação humana"""
    try:
        box = await page.locator(selector).bounding_box()
        if box:
            await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        
        await page.click(selector)
        await page.type(selector, text, delay=random.randint(50, 150))
    except Exception as e:
        print(f"⚠️ Erro ao digitar (human_type): {e}")

async def login_laguna_bypass(p):
    print("\n🔐 Iniciando LOGIN na LAGUNA (Modo Stealth Manual)...")

    args = [
        "--disable-blink-features=AutomationControlled",
        "--start-maximized",
        "--no-sandbox",
        "--disable-infobars"
    ]

    browser = await p.chromium.launch(
        headless=False, 
        args=args,
        ignore_default_args=["--enable-automation"] 
    )

    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1920, 'height': 1080},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        java_script_enabled=True
    )

    # Bypass manual
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page = await context.new_page()

    try:
        print("🌍 Acessando página...")
        await page.goto(LOGIN_URL_LAGUNA, wait_until="domcontentloaded", timeout=60000)
        
        await asyncio.sleep(random.uniform(2, 4))

        # --- PREENCHER USUÁRIO ---
        print("👤 Digitando usuário...")
        await page.wait_for_selector("#username", state="visible")
        await human_type(page, "#username", USUARIO_LAGUNA)
        await asyncio.sleep(1)

        # --- PREENCHER SENHA ---
        print("🔑 Digitando senha...")
        await human_type(page, "#password", SENHA_LAGUNA)
        await asyncio.sleep(1)

        # --- CLICAR ENTRAR ---
        print("🚀 Clicando em ENTRAR...")
        submit_btn = page.locator("#kt_login_signin_submit")
        
        if await submit_btn.count() > 0:
            await submit_btn.click()
        else:
            await page.keyboard.press("Enter")

        # Aguardar navegação pós-login
        print("⏳ Aguardando carregamento da home...")
        await page.wait_for_load_state("networkidle")
        
        # =======================================================
        # AÇÃO SOLICITADA: ESPERAR 3s E CLICAR NO X
        # =======================================================
        print("⏱️ Esperando 3 segundos fixos...")
        await asyncio.sleep(3) 
        
        print("❎ Tentando clicar no botão X (.driver-popover-close-btn)...")
        try:
            # Tenta clicar no botão. Se ele não existir, o except captura e o código segue.
            # Timeout curto para não travar o robô se o botão não estiver lá.
            await page.click(".driver-popover-close-btn", timeout=2000)
            print("✔ Clicado com sucesso!")
        except:
            print("ℹ️ O botão não estava na tela ou já sumiu (seguindo fluxo).")
        # =======================================================

        print(f"✅ Login finalizado! URL Atual: {page.url}")
        
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro na Laguna: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None