import asyncio
import random
from playwright.async_api import async_playwright

# ===================== CONFIG TAKAO ===================== #
LOGIN_URL_TAKAO = "https://portal.takao.com.br/"

USUARIO_TAKAO = "compras2.autopecasvieira@gmail.com"
SENHA_TAKAO = "@1186Km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

HEADLESS = True 

async def human_type(page, selector, text):
    """Simula uma digitação humana"""
    try:
        # Tenta mover o mouse para o elemento antes de interagir
        box = await page.locator(selector).bounding_box()
        if box:
            await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        
        await page.click(selector)
        # Digita devagar
        await page.type(selector, text, delay=random.randint(60, 180))
    except Exception as e:
        print(f"⚠️ Erro ao digitar em {selector}: {e}")

async def login_takao_bypass(p):
    print("\n🔐 Iniciando LOGIN na TAKAO (Modo Stealth Lento)...")

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
        print("🌍 Acessando página da Takao (aguardando carregamento)...")
        # Aumentei timeout para 90s pois o site é lento
        await page.goto(LOGIN_URL_TAKAO, wait_until="domcontentloaded", timeout=90000)
        
        # Pausa longa inicial para garantir que scripts carregaram
        print("⏳ Aguardando 8 segundos para estabilização do site...")
        await asyncio.sleep(8)

        # --- PASSO 1: ABRIR MODAL ---
        print("🖱 Procurando botão de abrir modal...")
        botao_abrir_modal = page.locator("#icon-login button[data-testid='btnLogin']")
        
        # Espera o botão ficar visível
        await botao_abrir_modal.wait_for(state="visible", timeout=20000)
        
        # Move o mouse e clica
        box = await botao_abrir_modal.bounding_box()
        if box:
            await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
            await asyncio.sleep(0.5)
        
        await botao_abrir_modal.click()
        
        print("⌛ Aguardando 4 segundos para o modal aparecer...")
        await asyncio.sleep(4) # Espera a animação do modal

        # --- PASSO 2: PREENCHER USUÁRIO ---
        print("👤 Digitando usuário...")
        input_email = "input[data-testid='emailLogin']"
        await page.wait_for_selector(input_email, state="visible", timeout=15000)
        await human_type(page, input_email, USUARIO_TAKAO)
        
        await asyncio.sleep(random.uniform(1, 2))

        # --- PASSO 3: PREENCHER SENHA ---
        print("🔑 Digitando senha...")
        input_senha = "input[data-testid='senhaLogin']"
        await human_type(page, input_senha, SENHA_TAKAO)
        
        await asyncio.sleep(random.uniform(1, 2))

        # --- PASSO 4: CLICAR ENTRAR ---
        print("🚀 Clicando no botão de entrar do formulário...")
        # Seletor específico do botão dentro do form
        btn_enviar = page.locator("form button[data-testid='btnLogin']")
        
        # Move mouse e clica
        if await btn_enviar.is_visible():
            box = await btn_enviar.bounding_box()
            if box:
                await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                await asyncio.sleep(0.5)
            await btn_enviar.click()
        else:
            print("⚠️ Botão de enviar não visível, tentando Enter...")
            await page.keyboard.press("Enter")

        # --- VERIFICAÇÃO ---
        print("⏳ Aguardando processamento do login (Site lento)...")
        # Espera longa para processar
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(6) 

        # Se o campo de email sumiu (modal fechou), consideramos sucesso
        if await page.locator(input_email).is_hidden():
             print(f"✅ Login TAKAO finalizado! URL Atual: {page.url}")
        else:
             print("⚠️ Aviso: O modal de login parece ainda estar aberto. Verifique se entrou.")
        
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro na Takao: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None