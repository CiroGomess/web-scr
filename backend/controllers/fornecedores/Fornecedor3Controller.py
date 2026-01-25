import asyncio
import random

# ===================== CONFIG ===================== #
LOGIN_URL_ACARAUJO = "https://portal.acaraujo.com.br/entrar"
USUARIO_AC = "autopecasvieira@gmail.com"
SENHA_AC = "Vieira1975@"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADLESS = False 

async def login_acaraujo(p):
    print("\n🔐 Iniciando LOGIN no fornecedor AC ARAÚJO...")

    browser = await p.chromium.launch(headless=HEADLESS, slow_mo=300)
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1366, 'height': 768}
    )

    page = await context.new_page()

    try:
        await page.goto(LOGIN_URL_ACARAUJO, wait_until="networkidle", timeout=60000)

        # 1. Preencher E-mail
        await page.wait_for_selector("#email", state="visible")
        await page.fill("#email", USUARIO_AC)
        print("👤 E-mail preenchido.")

        # 2. Preencher Senha
        await page.fill("input[name='senha']", SENHA_AC)
        print("🔑 Senha preenchida.")

        # 3. Clicar no botão Entrar
        btn_entrar = page.locator("button.g-recaptcha")
        print("🚀 Clicando no botão Entrar...")
        await btn_entrar.click()

        # --- ETAPA 4: MODAL DE PREFERÊNCIAS ---
        print("⏳ Aguardando Modal de Preferências...")
        
        try:
            # Espera o seletor do dropdown aparecer na tela (timeout de 15s)
            # Usamos o name específico que você mandou
            select_selector = "select[name='id_condicao_pagamento_preferencia']"
            await page.wait_for_selector(select_selector, state="visible", timeout=15000)

            # Seleciona a opção pelo INDEX 1 (Pula o "Selecione" e pega o primeiro item real)
            # O primeiro item da sua lista é "A VISTA-14D - 2%..." (value="10")
            await page.select_option(select_selector, index=1)
            print("📝 Primeira opção de pagamento selecionada.")

            # Pausa rápida para garantir que o site registrou a seleção
            await asyncio.sleep(1)

            # Clica no botão Confirmar
            # Procuramos um botão do tipo submit que tenha a classe btn-success
            print("🚀 Clicando no botão Confirmar...")
            await page.click("button[type='submit'].btn-success")

            # Aguarda o modal sumir e a página carregar o dashboard
            await page.wait_for_load_state("networkidle")
            
        except Exception as e:
            # Caso o modal não apareça (as vezes já está salvo), apenas avisamos e seguimos
            print(f"⚠️ O modal de preferências não apareceu ou já foi preenchido. Detalhe: {e}")

        # Verificação final
        if "/entrar" in page.url:
             print("❌ ERRO: Ainda estamos na página de login.")
             return None, None, None

        print(f"✅ Login AC Araújo e Seleção de Preferências realizados! URL: {page.url}")
        return browser, context, page

    except Exception as e:
        print(f"❌ Erro inesperado na AC Araújo: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None