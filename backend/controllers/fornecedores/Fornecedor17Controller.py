import asyncio
import random
from playwright.async_api import async_playwright

# ===================== CONFIG PLS WEB ===================== #
LOGIN_URL_PLS = "http://novo.plsweb.com.br/?id=75EAD22A-2086-49C8-A9E0-A28DAE9AEBC5"

USUARIO_PLS = "vieira2s"
SENHA_PLS = "45rt9w1"

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
        await page.type(selector, text, delay=random.randint(60, 150))
    except Exception as e:
        print(f"⚠️ Erro ao digitar em {selector}: {e}")

async def login_pls_bypass(p):
    print("\n🔐 Iniciando LOGIN no PLS WEB (Modo Stealth)...")

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
        print("🌍 Acessando página PLS...")
        await page.goto(LOGIN_URL_PLS, wait_until="networkidle", timeout=60000)
        
        await asyncio.sleep(random.uniform(2, 4))

        # --- PRE-LOGIN: CLICAR EM "OK, ENTENDI" ---
        print("🖱 (Pré-Login) Procurando botão 'Ok, entendi'...")
        btn_entendi = page.locator("span.ui-button-text:has-text('Ok, entendi')")
        
        if await btn_entendi.count() > 0 and await btn_entendi.is_visible():
            await btn_entendi.click()
            print("✔ Botão 'Ok, entendi' clicado.")
            await asyncio.sleep(1)
        else:
            print("ℹ️ Botão 'Ok, entendi' não apareceu.")

        # --- PREENCHER USUÁRIO ---
        print("👤 Digitando usuário...")
        await page.wait_for_selector("#usuario", state="visible", timeout=15000)
        await human_type(page, "#usuario", USUARIO_PLS)
        await asyncio.sleep(0.5)

        # --- PREENCHER SENHA ---
        print("🔑 Digitando senha...")
        await human_type(page, "#senha", SENHA_PLS)
        await asyncio.sleep(0.5)

        # --- CLICAR ENTRAR ---
        print("🚀 Clicando em Entrar...")
        submit_btn = page.locator("input[value='Entrar']")
        
        if await submit_btn.is_visible():
            box = await submit_btn.bounding_box()
            if box:
                await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                await asyncio.sleep(0.5)
            await submit_btn.click()
        else:
            await page.keyboard.press("Enter")

        # --- PÓS-LOGIN ---
        print("⏳ Aguardando processamento do login...")
        await page.wait_for_load_state("networkidle")
        
        # =======================================================
        # PASSO EXTRA: CLICAR EM "OK" PÓS-LOGIN
        # =======================================================
        print("⏱️ Esperando 3 segundos fixos (Pós-Login)...")
        await asyncio.sleep(3)
        
        print("🖱 Clicando no botão 'Ok'...")
        try:
            # Busca especificamente o texto "Ok" para não confundir com o anterior
            # O timeout é curto para não travar se ele não aparecer
            btn_ok = page.locator("span.ui-button-text:has-text('Ok')")
            
            # Se houver mais de um (ex: o "Ok entendi" ainda estiver oculto no DOM),
            # pegamos o último visível ou filtramos
            if await btn_ok.count() > 0:
                # Clica no primeiro que estiver visível
                await btn_ok.first.click()
                print("✔ Botão 'Ok' clicado com sucesso!")
            else:
                print("ℹ️ Botão 'Ok' não foi encontrado.")
                
        except Exception as e:
            print(f"ℹ️ Erro ao tentar clicar no Ok (pode não ter aparecido): {e}")
        # =======================================================

        print(f"✅ Login finalizado! URL Atual: {page.url}")
        
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro no PLS Web: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None