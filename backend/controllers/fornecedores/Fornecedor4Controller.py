import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_F4 = "https://ecommerce.gb.com.br/#/homeE"
# URL de destino pós-login (Tela de Produtos)
URL_PRODUTOS_F4 = "https://ecommerce.gb.com.br/#/unit004"

USUARIO_F4 = "43053953000120"
SENHA_F4 = "@#Compras21975"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]
HEADLESS = True 

async def login_fornecedor4(p):
    print("\n🔐 Iniciando LOGIN no FORNECEDOR 4 (GB)...")

    # Adicionei argumentos para evitar detecção simples
    args = [
        "--disable-blink-features=AutomationControlled", 
        "--start-maximized", 
        "--no-sandbox"
    ]

    browser = await p.chromium.launch(
        headless=HEADLESS, 
        args=args,
        slow_mo=200,
        ignore_default_args=["--enable-automation"]
    )
    
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1366, 'height': 768},
        locale="pt-BR"
    )

    # Bypass básico
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    page = await context.new_page()

    try:
        # Acessa a página de login
        await page.goto(LOGIN_URL_F4, wait_until="networkidle", timeout=60000)

        # 1. Preencher Usuário
        await page.wait_for_selector("#username", state="visible")
        await page.fill("#username", USUARIO_F4)
        print("👤 Usuário preenchido.")

        # 2. Preencher Senha
        await page.fill("#password", SENHA_F4)
        print("🔑 Senha preenchida.")

        # 3. Clicar no botão ENTRAR
        print("🚀 Clicando no botão ENTRAR...")
        await page.click("a#btn-logar:has-text('ENTRAR')")

        # 4. Aguardar o login processar
        print("⏳ Aguardando autenticação...")
        await page.wait_for_load_state("networkidle")
        # Diminuí um pouco o tempo pois vamos fazer outra navegação em seguida
        await asyncio.sleep(10) 

        # =======================================================
        # PASSO EXTRA: REDIRECIONAR PARA A TELA DE PRODUTOS
        # =======================================================
        print(f"📂 Redirecionando para Produtos ({URL_PRODUTOS_F4})...")
        await page.goto(URL_PRODUTOS_F4, wait_until="networkidle")
        
        # Espera o Vue.js renderizar a tela de produtos
        await asyncio.sleep(5)
        # =======================================================

        print(f"✅ Login e Redirecionamento realizados! URL Atual: {page.url}")
        
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro no Fornecedor 4: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None