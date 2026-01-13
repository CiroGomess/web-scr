import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_JAHU = "https://b2b.jahu.com.br/"
USUARIO_JAHU = "fiscal.autopecasvieira@gmail.com"
SENHA_JAHU = "Jahu@123"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]


HEADLESS = True 

# ===================== AUXILIAR: ACEITAR COOKIES ===================== #

async def aceitar_termos_jahu(page):
    try:
        # Busca o botão pelo ID e texto exato que você extraiu
        btn_aceitar = page.locator("#modalBtn:has-text('EU ACEITO')")
        
        if await btn_aceitar.count() > 0:
            print("🍪 Popup de cookies detectado. Aceitando...")
            await btn_aceitar.click()
            # Espera o modal sair da frente dos outros elementos
            await asyncio.sleep(1.5)
        else:
            print("ℹ Popup de cookies não visualizado.")
    except Exception as e:
        print(f"ℹ Sem popup de cookies para fechar.")

# ===================== LOGIN JAHU ===================== #

async def login_jahu(p):
    print("\n🔐 Iniciando LOGIN no fornecedor JAHU...")

    browser = await p.chromium.launch(headless=HEADLESS, slow_mo=350)
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1366, 'height': 768}
    )

    page = await context.new_page()

    try:
        # 1. Acessar a Home
        await page.goto(LOGIN_URL_JAHU, wait_until="networkidle", timeout=60000)

        # 2. Fechar o bloqueio de cookies (importante no Angular)
        await aceitar_termos_jahu(page)

        # 3. Clicar em "Entre" para abrir o painel de login
        print("🖱 Abrindo menu de login...")
        btn_entre = page.locator("span.user-link.acesso:has-text('Entre')")
        await btn_entre.wait_for(state="visible", timeout=15000)
        await btn_entre.click()

        # 4. Preencher E-mail (id="user")
        await page.wait_for_selector("#user", state="visible", timeout=10000)
        await page.fill("#user", USUARIO_JAHU)
        print("👤 E-mail preenchido.")

        # 5. Preencher Senha (id="ipt-password")
        await page.fill("#ipt-password", SENHA_JAHU)
        print("🔑 Senha preenchida.")

        # 6. Clicar no botão ENTRAR
        # CORREÇÃO: Usamos :visible para evitar erro de duplicidade (Desktop/Mobile)
        # E usamos .first para garantir que pegamos apenas uma instância
        btn_entrar = page.locator("button#entrar:visible").first
        
        print("⏳ Aguardando validação do formulário pelo Angular...")
        
        # O Angular precisa de um tempo para validar os dados e habilitar o botão
        try:
            # Espera o atributo 'disabled' ser removido pelo Angular
            await btn_entrar.wait_for(state="enabled", timeout=10000)
        except:
            print("⚠ Botão ainda desabilitado, tentando prosseguir mesmo assim...")

        print("🚀 Clicando no botão Entrar...")
        await btn_entrar.click()

        # 7. Aguardar redirecionamento pós-login
        # Sites B2B costumam carregar muitos dados após o login, então o sleep ajuda
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(5) 

        # Verificação final
        if "session" in page.url or await btn_entre.is_hidden():
            print(f"✅ Login Jahu realizado com sucesso! URL: {page.url}")
            return browser, context, page
        else:
            print("❌ ERRO: Login pode ter falhado (ainda na página inicial sem logar).")
            return None, None, None

    except Exception as e:
        print(f"❌ Erro crítico no login da Jahu: {e}")
        return None, None, None