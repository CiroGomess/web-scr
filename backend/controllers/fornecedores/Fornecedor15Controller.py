import asyncio
import random
from playwright.async_api import async_playwright

# ===================== CONFIG RIOJC ===================== #
LOGIN_URL_RIOJC = "http://riojc.dyndns-remote.com:8080/b2b/"

USUARIO_RIOJC = "43053953000120"
SENHA_RIOJC = "2835"



USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

HEADLESS = False 

async def human_type(page, selector, text):
    """Simula uma digitação humana"""
    try:
        # Tenta achar o elemento
        element = page.locator(selector)
        # Move o mouse para cima dele
        box = await element.bounding_box()
        if box:
            await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        
        await element.click()
        # Digita devagar
        await page.type(selector, text, delay=random.randint(60, 150))
    except Exception as e:
        print(f"⚠️ Erro ao digitar em {selector}: {e}")

async def login_riojc_bypass(p):
    print("\n🔐 Iniciando LOGIN no RIOJC (Modo Stealth)...")

    # 1. Argumentos Anti-Detecção
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

    # 2. Bypass manual do navigator.webdriver
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page = await context.new_page()

    try:
        print("🌍 Acessando página RIOJC...")
        await page.goto(LOGIN_URL_RIOJC, wait_until="domcontentloaded", timeout=60000)
        
        # ExtJS costuma ser pesado para carregar os inputs, vamos esperar bem
        await asyncio.sleep(random.uniform(3, 5))

        # --- PREENCHER CNPJ ---
        # ESTRATÉGIA: Usar o placeholder, pois o ID (ex: O55) muda sempre
        print("👤 Digitando CNPJ...")
        seletor_usuario = "input[placeholder='CNPJ do cliente']"
        
        await page.wait_for_selector(seletor_usuario, state="visible", timeout=20000)
        await human_type(page, seletor_usuario, USUARIO_RIOJC)
        
        await asyncio.sleep(1)

        # --- PREENCHER SENHA ---
        print("🔑 Digitando senha...")
        seletor_senha = "input[placeholder='Senha do cliente']"
        await human_type(page, seletor_senha, SENHA_RIOJC)
        
        await asyncio.sleep(1)

        # --- CLICAR ENTRAR ---
        print("🚀 Clicando em Login...")
        
        # O botão é um SPAN dentro de uma estrutura ExtJS.
        # Procuramos um SPAN que tenha o texto exato "Login" e classe x-btn-inner
        seletor_btn = "span.x-btn-inner:has-text('Login')"
        
        btn = page.locator(seletor_btn)
        
        if await btn.count() > 0:
            # Move e clica
            box = await btn.bounding_box()
            if box:
                await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                await asyncio.sleep(0.5)
            await btn.click()
        else:
            print("⚠️ Botão de login não encontrado pelo texto, tentando Enter...")
            await page.keyboard.press("Enter")

        # --- AGUARDAR CARREGAMENTO ---
        print("⏳ Aguardando carregamento do sistema...")
        # Sistemas em ExtJS usam muito AJAX, o networkidle é essencial
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(5) 

        print(f"✅ Ação de login finalizada! URL Atual: {page.url}")
        
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro no RIOJC: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None