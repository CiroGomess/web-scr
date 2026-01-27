import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_SOLROOM = "https://solroom.com.br/login/entrar"
HOME_URL_SOLROOM = "https://solroom.com.br/"

USUARIO_SOLROOM = "autopecasvieira@gmail.com"
SENHA_SOLROOM = "Vieira001"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADLESS = False


# ===================== HELPERS ===================== #
async def _goto_login(page, tentativa):
    print(f"🌐 Tentativa {tentativa}: abrindo login...")
    # networkidle pode travar em sites com polling; prefiro domcontentloaded
    await page.goto(LOGIN_URL_SOLROOM, wait_until="domcontentloaded", timeout=60000)

    # dá um tempinho pro JS montar a tela
    await asyncio.sleep(1)

    # confirma que os inputs existem/ficaram visíveis
    await page.wait_for_selector("#Login", state="visible", timeout=15000)
    await page.wait_for_selector("#Senha", state="visible", timeout=15000)


async def _do_login(page, tentativa):
    print(f"🔐 Tentativa {tentativa}: preenchendo credenciais...")

    await page.fill("#Login", USUARIO_SOLROOM)
    await page.fill("#Senha", SENHA_SOLROOM)

    print("🚀 Clicando no botão Login...")

    # Alguns sites não navegam (AJAX). Então tentamos:
    # 1) esperar navegação OU
    # 2) se não navegar, esperar a URL mudar/elemento de home aparecer
    try:
        async with page.expect_navigation(timeout=20000):
            await page.click("button[type='submit']")
    except Exception:
        # Se não navegou, ao menos clicou. Seguimos e aguardamos estabilização.
        await page.click("button[type='submit']")

    # estabiliza (sem travar)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(2)


def _login_ainda_esta_na_tela(page):
    return "login" in (page.url or "").lower()


# ===================== LOGIN SOLROOM ===================== #
async def login_solroom(p, max_tentativas=4):
    print("\n🔐 Iniciando LOGIN no fornecedor SOLROOM...")

    browser = await p.chromium.launch(
        headless=HEADLESS,
        slow_mo=300
    )

    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        locale="pt-BR",
        viewport={'width': 1366, 'height': 768}
    )

    page = await context.new_page()

    try:
        for tentativa in range(1, max_tentativas + 1):
            try:
                # 1) garantir que estamos na tela de login com inputs visíveis
                await _goto_login(page, tentativa)
                print("✅ Campos de login carregados.")

                # 2) tentar login
                await _do_login(page, tentativa)

                # 3) validar sucesso
                if not _login_ainda_esta_na_tela(page):
                    print(f"✅ Login Solroom realizado com sucesso! URL: {page.url}")
                    return browser, context, page

                print("⚠️ Ainda em tela de login após submit. Repetindo tentativa...")

            except Exception as e:
                print(f"⚠️ Tentativa {tentativa} falhou: {e}")

            # Backoff simples entre tentativas (evita bater igual robô)
            if tentativa < max_tentativas:
                espera = 2 + tentativa  # 3s, 4s, 5s...
                print(f"⏳ Aguardando {espera}s e tentando novamente...")
                await asyncio.sleep(espera)

                # Tenta limpar estado antes de reabrir
                try:
                    await page.goto("about:blank", wait_until="domcontentloaded", timeout=15000)
                except Exception:
                    pass

        print("❌ ERRO: Login Solroom falhou após todas as tentativas.")
        await context.close()
        await browser.close()
        return None, None, None

    except Exception as e:
        print(f"❌ Erro inesperado no login da Solroom: {e}")
        try:
            await context.close()
        except Exception:
            pass
        try:
            await browser.close()
        except Exception:
            pass
        return None, None, None
