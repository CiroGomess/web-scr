import asyncio
import random
from playwright.async_api import async_playwright

# ===================== CONFIG FURACÃO (Fornecedor 16) ===================== #
LOGIN_URL_FURACAO = "https://vendas.furacao.com.br/vendas/sav/login?redirect="
# URL de destino solicitada
URL_PRODUTOS_FURACAO = "https://vendas.furacao.com.br/vendas/sav/produtos"

USUARIO_FURACAO = "136224"
SENHA_FURACAO = "34160"

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
        await page.type(selector, text, delay=random.randint(60, 150))
    except Exception as e:
        print(f"⚠️ Erro ao digitar em {selector}: {e}")

async def login_furacao_bypass(p):
    print("\n🔐 Iniciando LOGIN na FURACÃO (Modo Stealth)...")

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
        viewport={'width': 1920, 'height': 768},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        java_script_enabled=True
    )

    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page = await context.new_page()

    try:
        print("🌍 Acessando página de Login...")
        await page.goto(LOGIN_URL_FURACAO, wait_until="networkidle", timeout=60000)
        
        await asyncio.sleep(random.uniform(3, 5))

        # --- PASSO 1: SELECIONAR PERFIL "CLIENTE" ---
        print("🔽 Selecionando perfil 'Cliente'...")
        await page.wait_for_selector("#f", state="visible")
        await page.select_option("#f", "c")
        await asyncio.sleep(1)

        # --- PASSO 2: PREENCHER USUÁRIO ---
        print("👤 Digitando usuário...")
        await human_type(page, "#username", USUARIO_FURACAO)
        await asyncio.sleep(1)

        # --- PASSO 3: PREENCHER SENHA ---
        print("🔑 Digitando senha...")
        await human_type(page, "#password", SENHA_FURACAO)
        await asyncio.sleep(1)

        # --- PASSO 4: CLICAR ENTRAR ---
        print("🚀 Clicando em Entrar...")
        submit_btn = page.locator("button[type='submit']:has-text('Entrar')")
        
        if await submit_btn.is_visible():
            box = await submit_btn.bounding_box()
            if box:
                await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                await asyncio.sleep(0.5)
            await submit_btn.click()
        else:
            await page.keyboard.press("Enter")

        print("⏳ Aguardando processamento do login...")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(4) 

        # =======================================================
        # PASSO EXTRA: IR PARA PÁGINA DE PRODUTOS
        # =======================================================
        print(f"➡ Redirecionando para: {URL_PRODUTOS_FURACAO}")
        
        # Força a navegação para a URL de produtos
        await page.goto(URL_PRODUTOS_FURACAO, wait_until="networkidle")
        
        # Espera carregar a lista de produtos (opcional, segurança extra)
        await asyncio.sleep(3)
        # =======================================================

        print(f"✅ Login finalizado e redirecionado! URL Atual: {page.url}")
        
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro na Furacão: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None