import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_TAKAO = "https://portal.takao.com.br/"

USUARIO_TAKAO = "compras2.autopecasvieira@gmail.com"
SENHA_TAKAO = "@1186Km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADLESS = True 

# ===================== LOGIN TAKAO ===================== #

async def login_takao(p):
    print("\n🔐 Iniciando LOGIN no fornecedor TAKAO...")

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
        # 1. Acessar a Home
        await page.goto(LOGIN_URL_TAKAO, wait_until="networkidle", timeout=60000)

        # 2. CLICAR NO ÍCONE DE LOGIN (ABRIR MODAL)
        # Usamos o ID do container ou o data-testid do botão interno
        print("🖱 Clicando no ícone para abrir o modal de login...")
        botao_abrir_modal = page.locator("#icon-login button[data-testid='btnLogin']")
        
        await botao_abrir_modal.wait_for(state="visible", timeout=15000)
        await botao_abrir_modal.click()

        # 3. AGUARDAR O MODAL E PREENCHER OS DADOS
        # Após o clique, o formulário deve aparecer na tela
        print("⌛ Aguardando formulário carregar...")
        campo_email = page.locator("input[data-testid='emailLogin']")
        
        # Espera o campo de e-mail ficar visível no modal
        await campo_email.wait_for(state="visible", timeout=10000)
        
        await campo_email.fill(USUARIO_TAKAO)
        print("👤 Email preenchido.")

        # Preencher Senha
        await page.locator("input[data-testid='senhaLogin']").fill(SENHA_TAKAO)
        print("🔑 Senha preenchida.")

        # 4. CLICAR NO BOTÃO ENTRAR (DENTRO DO MODAL)
        # Selecionamos o botão que está dentro da tag <form> para não confundir com o do header
        btn_enviar = page.locator("form button[data-testid='btnLogin']")
        
        print("🚀 Enviando formulário de login...")
        await btn_enviar.click()

        # 5. VERIFICAÇÃO DE SUCESSO
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(4)

        # Se o campo de login sumiu ou a URL mudou, o login deu certo
        if await campo_email.is_hidden():
            print(f"✅ Login Takao realizado com sucesso! URL: {page.url}")
            return browser, context, page
        else:
            print("❌ ERRO: O modal de login ainda está visível. Verifique as credenciais.")
            return None, None, None

    except Exception as e:
        print(f"❌ Erro inesperado no login da Takao: {e}")
        return None, None, None