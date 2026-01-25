import asyncio
import random
import time
from playwright.async_api import async_playwright

# ===================== CONFIG SAMA (Fornecedor 8) ===================== #
LOGIN_URL_SAMA = "https://compreonline.samaautopecas.com.br/Account/Login/"
USUARIO_SAMA = "autopecasvieira@gmail.com"
SENHA_SAMA = "1186km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

HEADLESS = False

# ===================== HELPERS ===================== #
async def human_type(page, selector, text):
    """Simula uma digitação humana com variações de velocidade"""
    try:
        box = await page.locator(selector).bounding_box()
        if box:
            await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

        await page.click(selector)
        await page.type(selector, text, delay=random.randint(50, 150))
    except Exception as e:
        print(f"⚠️ Erro ao digitar em {selector}: {e}")

async def fechar_driver_js(page, motivo=""):
    """Fecha pop-up do Driver.js se existir."""
    try:
        btn = page.locator(".driver-popover-close-btn").first
        if await btn.count() > 0 and await btn.is_visible(timeout=1500):
            if motivo:
                print(f"🛡️ Driver.js detectado ({motivo}). Fechando...")
            await btn.click(force=True, timeout=2500)
            try:
                await btn.wait_for(state="hidden", timeout=2000)
            except:
                pass
            print("✅ Driver.js fechado.")
            return True
    except:
        pass
    return False

async def salvar_debug_login(page, prefix):
    ts = int(time.time())
    shot = f"{prefix}_login_fail_{ts}.png"
    html = f"{prefix}_login_fail_{ts}.html"

    try:
        await page.screenshot(path=shot, full_page=True)
        print(f"🧾 Screenshot salvo: {shot}")
    except:
        pass

    try:
        content = await page.content()
        with open(html, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"🧾 HTML salvo: {html}")
    except:
        pass

async def validar_login_sucesso(page) -> bool:
    url = page.url or ""
    if "/Account/Login" in url:
        return False

    candidates = [
        "#search-prod",
        "table",
        "nav",
        ".kt-header",
        ".kt-menu",
    ]

    for sel in candidates:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                return True
        except:
            pass

    return True

# ===================== LOGIN ===================== #
async def login_sama_bypass(p, max_tentativas=3):
    print("\n🔐 Iniciando LOGIN na SAMA (Modo Stealth Manual)...")

    args = [
        "--disable-blink-features=AutomationControlled",
        "--start-maximized",
        "--no-sandbox",
        "--disable-infobars",
        "--disable-dev-shm-usage",
    ]

    for tentativa in range(1, max_tentativas + 1):
        browser = None
        context = None
        page = None

        try:
            print(f"\n🔁 Tentativa {tentativa}/{max_tentativas} (SAMA)")

            browser = await p.chromium.launch(
                headless=HEADLESS,
                args=args,
                ignore_default_args=["--enable-automation"],
            )

            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
                java_script_enabled=True,
            )

            await context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """
            )

            page = await context.new_page()

            print("🌍 Acessando página da SAMA...")
            await page.goto(LOGIN_URL_SAMA, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(random.uniform(2, 4))

            # Usuário
            print("👤 Digitando usuário...")
            await page.wait_for_selector("#username", state="visible", timeout=20000)
            await human_type(page, "#username", USUARIO_SAMA)
            await asyncio.sleep(random.uniform(1, 2))

            # Senha
            print("🔑 Digitando senha...")
            await human_type(page, "#password", SENHA_SAMA)
            await asyncio.sleep(random.uniform(1, 2))

            # Entrar
            print("🚀 Clicando em ENTRAR...")
            submit_btn = page.locator("#kt_login_signin_submit").first
            if await submit_btn.count() > 0:
                await submit_btn.click()
            else:
                await page.keyboard.press("Enter")

            print("⏳ Aguardando pós-login...")
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except:
                pass

            await asyncio.sleep(2.5)
            await fechar_driver_js(page, motivo="pós-login")

            if not await validar_login_sucesso(page):
                print(f"❌ LOGIN NÃO CONFIRMADO (ainda no login ou sem sinais de home). URL: {page.url}")
                await salvar_debug_login(page, "sama")
                try:
                    await context.close()
                except:
                    pass
                try:
                    await browser.close()
                except:
                    pass
                await asyncio.sleep(2)
                continue

            print(f"✅ Login SAMA OK! URL Atual: {page.url}")
            return browser, context, page

        except Exception as e:
            print(f"❌ Erro na SAMA: {e}")
            if page:
                try:
                    await salvar_debug_login(page, "sama_err")
                except:
                    pass
            if context:
                try:
                    await context.close()
                except:
                    pass
            if browser:
                try:
                    await browser.close()
                except:
                    pass
            await asyncio.sleep(2)

    print("❌ Falha definitiva no login da SAMA após todas as tentativas.")
    return None, None, None
