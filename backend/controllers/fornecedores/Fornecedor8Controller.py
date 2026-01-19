import asyncio
import random
from playwright.async_api import async_playwright

# ===================== CONFIG SAMA (Fornecedor 8) ===================== #
LOGIN_URL_SAMA = "https://compreonline.samaautopecas.com.br/Account/Login/"
HOME_URL_SAMA = "https://compreonline.samaautopecas.com.br/"

USUARIO_SAMA = "autopecasvieira@gmail.com"
SENHA_SAMA = "1186km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

HEADLESS = True 

async def human_type(page, selector, text):
    """Simula uma digitação humana com variações de velocidade"""
    try:
        box = await page.locator(selector).bounding_box()
        if box:
            await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        
        await page.click(selector)
        await page.type(selector, text, delay=random.randint(50, 150))
    except Exception as e:
        print(f"⚠️ Erro ao digitar em {selector}: {e}")

async def login_sama_bypass(p):
    print("\n🔐 Iniciando LOGIN na SAMA (Modo Stealth Manual)...")

    # 1. Argumentos para camuflagem
    args = [
        "--disable-blink-features=AutomationControlled",
        "--start-maximized",
        "--no-sandbox",
        "--disable-infobars"
    ]

    browser = await p.chromium.launch(
        headless=HEADLESS, # Headless False ajuda a passar por proteções
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

    # 2. Bypass manual do navigator.webdriver
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page = await context.new_page()

    try:
        print("🌍 Acessando página da SAMA...")
        await page.goto(LOGIN_URL_SAMA, wait_until="domcontentloaded", timeout=60000)
        
        await asyncio.sleep(random.uniform(2, 4))

        # --- PREENCHER USUÁRIO ---
        print("👤 Digitando usuário...")
        await page.wait_for_selector("#username", state="visible")
        await human_type(page, "#username", USUARIO_SAMA)
        await asyncio.sleep(random.uniform(1, 2))

        # --- PREENCHER SENHA ---
        print("🔑 Digitando senha...")
        await human_type(page, "#password", SENHA_SAMA)
        await asyncio.sleep(random.uniform(1, 2))

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
        # TRATAMENTO DO POP-UP (Igual ao Laguna)
        # =======================================================
        print("⏱️ Esperando 3 segundos fixos para o modal aparecer...")
        await asyncio.sleep(3) 
        
        print("❎ Tentando clicar no botão X (.driver-popover-close-btn)...")
        try:
            # Tenta clicar no botão. Timeout curto para não travar se ele não vier.
            await page.click(".driver-popover-close-btn", timeout=3000)
            print("✔ Modal fechado com sucesso!")
        except:
            print("ℹ️ O botão X não apareceu ou já foi fechado.")
        # =======================================================

        print(f"✅ Login SAMA finalizado! URL Atual: {page.url}")
        
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro na SAMA: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None