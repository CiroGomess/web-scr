import asyncio
import random
from playwright.async_api import async_playwright

# ===================== CONFIG ===================== #

LOGIN_URL = "https://www.portalcomdip.com.br/comdip/catalogo/login"
HOME_URL = "https://www.portalcomdip.com.br/"

CPF = "43.053.953/0001-20"
SENHA = "1186Km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/15 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 Chrome/115 Mobile Safari/537.36"
]

HEADLESS = False  # mude para False quando quiser ver o navegador


# ===================== ACEITAR COOKIES ===================== #

async def aceitar_cookies(page):
    try:
        btn = page.locator("div.alerta-cookies a.btn:has-text('Aceitar')")
        await btn.wait_for(state="visible", timeout=3000)
        await btn.click()
        print("✔ Cookies aceitos.")
    except:
        print("ℹ Nenhum popup de cookies encontrado.")


# ===================== LOGIN ===================== #

async def login(p):

    print("\n🔐 Iniciando LOGIN obrigatório...")

    browser = await p.chromium.launch(
        headless=HEADLESS,
        slow_mo=0 if HEADLESS else 350
    )


    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        locale="pt-BR",
        timezone_id="America/Sao_Paulo"
    )

    page = await context.new_page()
    await page.goto(LOGIN_URL, wait_until="networkidle")

    await aceitar_cookies(page)
    await asyncio.sleep(1)

    # Preencher CPF
    await page.fill("input[formcontrolname='login']", CPF)
    await asyncio.sleep(1)

    # Preencher senha
    await page.fill("input[formcontrolname='senha']", SENHA)
    await asyncio.sleep(1)

    # Salvar acesso
    try:
        await page.locator("label:has-text('Salvar Acesso')").click()
    except:
        pass

    # Aceitar termos
    try:
        await page.check("input[name='cbAceitarTermos']")
    except:
        pass

    # Clicar Entrar
    botao = page.locator("button:has-text('Entrar')")
    await botao.wait_for(state="visible")
    await botao.click()

    await page.wait_for_load_state("networkidle")
    await aceitar_cookies(page)

    if "/login" in page.url:
        print("❌ ERRO: Login falhou!")
        return None, None, None

    print("✅ Login realizado com sucesso!")

    # Ir para home
    await page.goto(HOME_URL, wait_until="networkidle")
    await aceitar_cookies(page)

    print("🏠 Estamos na home!")

    return browser, context, page


