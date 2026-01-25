import asyncio
import random
from playwright.async_api import async_playwright

# ===================== CONFIG SKY (PELLEGRINO) ===================== #
LOGIN_URL_SKY = "https://compreonline.pellegrino.com.br/Account/Login/?ReturnUrl=%2F"
HOME_URL_SKY = "https://compreonline.pellegrino.com.br/"

USUARIO_SKY = "autopecasvieira@gmail.com"
SENHA_SKY = "1186km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

HEADLESS = False 

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

async def login_sky_bypass(p):
    print("\n🔐 Iniciando LOGIN na SKY/PELLEGRINO (Modo Stealth)...")

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

    # Bypass manual
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page = await context.new_page()

    try:
        print("🌍 Acessando página da Pellegrino...")
        await page.goto(LOGIN_URL_SKY, wait_until="domcontentloaded", timeout=60000)
        
        await asyncio.sleep(random.uniform(2, 4))

        # --- PREENCHER USUÁRIO ---
        print("👤 Digitando usuário...")
        await page.wait_for_selector("#username", state="visible")
        await human_type(page, "#username", USUARIO_SKY)
        
        await asyncio.sleep(1)

        # --- PREENCHER SENHA ---
        print("🔑 Digitando senha...")
        await human_type(page, "#password", SENHA_SKY)
        
        await asyncio.sleep(1)

        # --- CLICAR ENTRAR ---
        print("🚀 Clicando em Entrar...")
        submit_btn = page.locator("#kt_login_signin_submit")
        
        if await submit_btn.is_visible():
            box = await submit_btn.bounding_box()
            if box:
                await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                await asyncio.sleep(0.5)
            await submit_btn.click()
        else:
            await page.keyboard.press("Enter")

        # --- AGUARDAR CARREGAMENTO ---
        print("⏳ Aguardando processamento do login...")
        await page.wait_for_load_state("networkidle")
        
        # =======================================================
        # PASSO EXTRA: FECHAR O MODAL (TUTORIAL)
        # =======================================================
        print("⏱️ Esperando 3 segundos fixos...")
        await asyncio.sleep(3) 
        
        print("❎ Clicando no botão X (.driver-popover-close-btn)...")
        try:
            # Tenta clicar no botão. Timeout de 3s para garantir.
            await page.click(".driver-popover-close-btn", timeout=3000)
            print("✔ Modal fechado com sucesso!")
        except:
            print("ℹ️ O botão não apareceu ou já sumiu.")
        # =======================================================

        print(f"✅ Login SKY finalizado! URL Atual: {page.url}")
        
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro na Sky/Pellegrino: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None