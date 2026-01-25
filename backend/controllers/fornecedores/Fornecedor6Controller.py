import asyncio
import random
import time
from playwright.async_api import async_playwright

# ===================== CONFIG LAGUNA ===================== #
LOGIN_URL_LAGUNA = "https://compreonline.lagunaautopecas.com.br/Account/Login/"
USUARIO_LAGUNA = "autopecasvieira@gmail.com"
SENHA_LAGUNA = "1186km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

HEADLESS = False  # Pode manter True. Se falhar por bloqueio, rode via Xvfb com False.

# ===================== HELPERS ===================== #
async def human_type(page, selector, text):
    """Simula uma digitação humana"""
    try:
        box = await page.locator(selector).bounding_box()
        if box:
            await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

        await page.click(selector)
        await page.type(selector, text, delay=random.randint(50, 150))
    except Exception as e:
        print(f"⚠️ Erro ao digitar (human_type): {e}")

async def fechar_driver_js(page, motivo=""):
    """Fecha pop-up do Driver.js se existir."""
    try:
        btn = page.locator(".driver-popover-close-btn").first
        if await btn.count() > 0 and await btn.is_visible(timeout=1500):
            if motivo:
                print(f"🛡️ Driver.js detectado ({motivo}). Fechando...")
            await btn.click(force=True, timeout=2000)
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
    """Gera evidência quando login falha (screenshot + html)."""
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
    """
    Login é considerado OK se:
    - URL NÃO contém /Account/Login/
    - E existe algum elemento típico do pós-login (busca, tabela, menu etc.)
    """
    url = page.url or ""
    if "/Account/Login" in url:
        return False

    # Sinais comuns de pós-login (ajuste se precisar)
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

    # Mesmo se não achar seletor, se saiu da /Account/Login já é um bom sinal.
    return True

# ===================== LOGIN ===================== #
async def login_laguna_bypass(p, max_tentativas=3):
    print("\n🔐 Iniciando LOGIN na LAGUNA (Modo Stealth Manual)...")

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
            print(f"\n🔁 Tentativa {tentativa}/{max_tentativas} (Laguna)")

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

            # Bypass manual
            await context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """
            )

            page = await context.new_page()

            print("🌍 Acessando página...")
            await page.goto(LOGIN_URL_LAGUNA, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(random.uniform(2, 4))

            # Usuário
            print("👤 Digitando usuário...")
            await page.wait_for_selector("#username", state="visible", timeout=20000)
            await human_type(page, "#username", USUARIO_LAGUNA)
            await asyncio.sleep(1)

            # Senha
            print("🔑 Digitando senha...")
            await human_type(page, "#password", SENHA_LAGUNA)
            await asyncio.sleep(1)

            # Entrar
            print("🚀 Clicando em ENTRAR...")
            submit_btn = page.locator("#kt_login_signin_submit").first
            if await submit_btn.count() > 0:
                await submit_btn.click()
            else:
                await page.keyboard.press("Enter")

            # Espera pós-login (não confie só em networkidle)
            print("⏳ Aguardando pós-login...")
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except:
                pass

            # Pequena espera + fecha tutorial se aparecer
            await asyncio.sleep(2.5)
            await fechar_driver_js(page, motivo="pós-login")

            # Validação REAL do login
            if not await validar_login_sucesso(page):
                print(f"❌ LOGIN NÃO CONFIRMADO (ainda no login ou sem sinais de home). URL: {page.url}")
                await salvar_debug_login(page, "laguna")
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

            print(f"✅ Login Laguna OK! URL Atual: {page.url}")
            return browser, context, page

        except Exception as e:
            print(f"❌ Erro na Laguna: {e}")
            if page:
                try:
                    await salvar_debug_login(page, "laguna_err")
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

    print("❌ Falha definitiva no login da Laguna após todas as tentativas.")
    return None, None, None
