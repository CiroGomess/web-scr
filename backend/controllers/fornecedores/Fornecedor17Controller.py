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

HEADLESS = False

# ===================== HELPERS ===================== #
async def wait_processing_gone(page, timeout=60000):
    """
    Espera o overlay de processamento (#processingRequest) SUMIR.
    - Se não existir na página, segue.
    - Se existir e estiver visível, espera ficar hidden/detached.
    """
    locator = page.locator("#processingRequest")

    try:
        # se existir no DOM
        if await locator.count() > 0:
            # se estiver visível, aguarda sumir
            if await locator.is_visible():
                print("⏳ Overlay #processingRequest visível... aguardando sumir.")
                await locator.wait_for(state="hidden", timeout=timeout)
                print("✅ Overlay #processingRequest sumiu.")
        return True
    except Exception as e:
        print(f"⚠️ Falha ao aguardar #processingRequest sumir: {e}")
        return False


async def safe_click(page, locator_or_selector, timeout=60000):
    await wait_processing_gone(page, timeout=timeout)
    if isinstance(locator_or_selector, str):
        await page.click(locator_or_selector)
    else:
        await locator_or_selector.click()


async def human_type(page, selector, text):
    """Simula uma digitação humana"""
    try:
        await wait_processing_gone(page, timeout=60000)

        box = await page.locator(selector).bounding_box()
        if box:
            await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)

        await page.click(selector)
        await page.type(selector, text, delay=random.randint(60, 150))
    except Exception as e:
        print(f"⚠️ Erro ao digitar em {selector}: {e}")


# ===================== LOGIN PLS ===================== #
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
        # networkidle às vezes prende; domcontentloaded é mais resiliente
        await page.goto(LOGIN_URL_PLS, wait_until="domcontentloaded", timeout=60000)

        # Se já entrar carregando, espera sumir
        await wait_processing_gone(page, timeout=60000)

        await asyncio.sleep(random.uniform(2, 4))

        # --- PRE-LOGIN: CLICAR EM "OK, ENTENDI" ---
        print("🖱 (Pré-Login) Procurando botão 'Ok, entendi'...")
        btn_entendi = page.locator("span.ui-button-text:has-text('Ok, entendi')")

        if await btn_entendi.count() > 0 and await btn_entendi.is_visible():
            await safe_click(page, btn_entendi, timeout=60000)
            print("✔ Botão 'Ok, entendi' clicado.")
            await asyncio.sleep(1)
        else:
            print("ℹ️ Botão 'Ok, entendi' não apareceu.")

        # --- ESPERAR OVERLAY SUMIR ANTES DE DIGITAR ---
        await wait_processing_gone(page, timeout=60000)

        # --- PREENCHER USUÁRIO ---
        print("👤 Digitando usuário...")
        await page.wait_for_selector("#usuario", state="visible", timeout=15000)
        await wait_processing_gone(page, timeout=60000)
        await human_type(page, "#usuario", USUARIO_PLS)
        await asyncio.sleep(0.5)

        # --- PREENCHER SENHA ---
        print("🔑 Digitando senha...")
        await wait_processing_gone(page, timeout=60000)
        await human_type(page, "#senha", SENHA_PLS)
        await asyncio.sleep(0.5)

        # --- CLICAR ENTRAR ---
        print("🚀 Clicando em Entrar...")
        submit_btn = page.locator("input[value='Entrar']")

        await wait_processing_gone(page, timeout=60000)

        if await submit_btn.is_visible():
            box = await submit_btn.bounding_box()
            if box:
                await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                await asyncio.sleep(0.5)

            await submit_btn.click()
        else:
            await page.keyboard.press("Enter")

        # ✅ AQUI É O PONTO PRINCIPAL:
        # "o login só deve ser feito depois que essa div sair"
        # => após submeter, aguarda o processamento terminar antes de qualquer passo pós-login
        print("⏳ Aguardando processamento do login (overlay sumir)...")
        ok_overlay = await wait_processing_gone(page, timeout=90000)
        if not ok_overlay:
            print("⚠️ Overlay não sumiu dentro do timeout. Tentando continuar mesmo assim...")

        # Depois do overlay sumir, aí sim aguarda estabilização leve
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        # =======================================================
        # PASSO EXTRA: CLICAR EM "OK" PÓS-LOGIN (SÓ DEPOIS DO OVERLAY SUMIR)
        # =======================================================
        print("🖱 Tentando clicar no botão 'Ok' pós-login...")
        try:
            await wait_processing_gone(page, timeout=60000)

            btn_ok = page.locator("span.ui-button-text:has-text('Ok')")
            if await btn_ok.count() > 0:
                # clica apenas se estiver visível
                if await btn_ok.first.is_visible():
                    await safe_click(page, btn_ok.first, timeout=60000)
                    print("✔ Botão 'Ok' clicado com sucesso!")
                else:
                    print("ℹ️ Botão 'Ok' existe, mas não está visível.")
            else:
                print("ℹ️ Botão 'Ok' não foi encontrado.")
        except Exception as e:
            print(f"ℹ️ Erro ao tentar clicar no Ok (pode não ter aparecido): {e}")
        # =======================================================

        print(f"✅ Login finalizado! URL Atual: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro no PLS Web: {e}")
        try:
            await browser.close()
        except Exception:
            pass
        return None, None, None
