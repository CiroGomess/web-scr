import asyncio
import random
from playwright.async_api import async_playwright

# ===================== CONFIG MATRIZ (Fornecedor 10) ===================== #
LOGIN_URL_MATRIZ = "http://suportematriz.ddns.net:5006"
HOME_URL_MATRIZ = "http://suportematriz.ddns.net:5006/home" 

USUARIO_MATRIZ = "fiscal.autopecasvieira@gmail.com"
SENHA_MATRIZ = "123456"

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

async def login_matriz_bypass(p):
    print("\n🔐 Iniciando LOGIN na MATRIZ (Modo Stealth Manual)...")

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

    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page = await context.new_page()

    try:
        print("🌍 Acessando página da Matriz...")
        await page.goto(LOGIN_URL_MATRIZ, wait_until="domcontentloaded", timeout=60000)
        
        await asyncio.sleep(random.uniform(2, 4))

        # --- PREENCHER USUÁRIO ---
        print("👤 Digitando usuário...")
        await page.wait_for_selector("#email", state="visible")
        await human_type(page, "#email", USUARIO_MATRIZ)
        await asyncio.sleep(1)

        # --- PREENCHER SENHA ---
        print("🔑 Digitando senha...")
        await human_type(page, "#password", SENHA_MATRIZ)
        await asyncio.sleep(1)

        # --- CLICAR ENTRAR ---
        print("🚀 Clicando em ENTRAR...")
        submit_btn = page.locator("#loginBtn")
        
        if await submit_btn.count() > 0:
            await submit_btn.click()
        else:
            await page.keyboard.press("Enter")

        # Aguarda carregamento inicial
        print("⏳ Aguardando processamento do login...")
        await page.wait_for_load_state("networkidle")

        # =======================================================
        # PASSO 1: CONFIRMAR SÃO GONÇALO
        # =======================================================
        print("⏱️ Esperando 3 segundos para clicar em 'SUPORTE SÃO GONÇALO'...")
        await asyncio.sleep(3)
        
        try:
            # Botão do SweetAlert
            btn_suporte = page.locator(".swal2-confirm")
            if await btn_suporte.is_visible(timeout=3000):
                await btn_suporte.click()
                print("✔ Botão 'SUPORTE SÃO GONÇALO' clicado!")
            else:
                print("ℹ️ Botão de suporte não apareceu.")
        except Exception as e:
            print(f"⚠️ Erro ao clicar no suporte: {e}")

        # =======================================================
        # PASSO 2: CONFIRMAR "ENTENDI TUDO"
        # =======================================================
        print("⏱️ Esperando mais 4 segundos para clicar em 'Entendi Tudo'...")
        await asyncio.sleep(4)

        try:
            # Botão de atualização
            btn_entendi = page.locator(".btn-atualizacao-entendi")
            if await btn_entendi.is_visible(timeout=3000):
                await btn_entendi.click()
                print("✔ Botão 'Entendi Tudo' clicado!")
            else:
                print("ℹ️ Botão 'Entendi Tudo' não apareceu.")
        except Exception as e:
            print(f"⚠️ Erro ao clicar em entendi: {e}")
        # =======================================================

        # Verificação final
        if await page.locator("#email").count() > 0:
             print("❌ O login parece ter falhado (campo de email ainda visível).")
        else:
             print(f"✅ Login MATRIZ finalizado! URL Atual: {page.url}")
        
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro na Matriz: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None