import asyncio
import random
from playwright.async_api import async_playwright

# ===================== CONFIG ===================== #
URL_PORTAL_VIVARIO = "https://www.vivariopecas.com.br/"

USUARIO_PENNA = "43.053.953/0001-20"
SENHA_PENNA = "@1186Km71"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

# Dados para ajudar a parecer um humano que já acessou antes
LOCAL_STORAGE_DATA = {
    "atualiza": "true",
    "_grecaptcha": "09AKhCRwg6uUdTEOQ1L6hBW-WqmuPCOoMPug3fLT8oBcWTnAc37hFU8vj-ZGdiI1FdEioWWxduo202Pa6zj_Rc29hl3TCv5c77FM7VPYY8Ddj13v4ntiLGrW_rzuQTqCja"
}

HEADLESS = True 

async def human_type(page, selector, text):
    """Digita como um humano para evitar detecção"""
    try:
        element = page.locator(selector)
        box = await element.bounding_box()
        if box:
            await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        await element.click()
        await page.type(selector, text, delay=random.randint(50, 120))
    except Exception as e:
        print(f"⚠️ Erro digitação: {e}")

async def injetar_local_storage(page):
    """Injeta dados para tentar manter sessão ativa"""
    try:
        await page.evaluate(f"""(data) => {{
            for (const [key, value] of Object.entries(data)) {{
                localStorage.setItem(key, value);
            }}
        }}""", LOCAL_STORAGE_DATA)
    except:
        pass

async def resolver_captcha_profissional(page):
    """
    Lógica avançada para lidar com o ReCaptcha v2 do HTML fornecido
    """
    print("🤖 Iniciando resolução do reCAPTCHA...")
    
    # O HTML mostra que o captcha está dentro de uma div com id="container"
    # E dentro de um iframe.
    
    try:
        # Localiza o iframe. O src contém 'api2/anchor'
        frame = page.frame_locator("#container iframe[src*='recaptcha/api2/anchor']")
        
        # 1. VERIFICAR SE JÁ ESTÁ EXPIRADO (O erro que você mostrou no HTML)
        # O HTML tem a classe: recaptcha-checkbox-expired
        esta_expirado = await frame.locator(".recaptcha-checkbox-expired").is_visible()
        
        if esta_expirado:
            print("❌ O Captcha está EXPIRADO (Demorou muito). Recarregando página...")
            await page.reload()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            # Re-localiza o frame após reload
            frame = page.frame_locator("#container iframe[src*='recaptcha/api2/anchor']")

        # 2. VERIFICAR SE JÁ ESTÁ MARCADO (Verde)
        esta_marcado = await frame.locator(".recaptcha-checkbox-checked").is_visible()
        if esta_marcado:
            print("✅ Captcha já está resolvido! Seguindo...")
            return True

        # 3. CLICAR NO CHECKBOX
        checkbox = frame.locator("#recaptcha-anchor")
        if await checkbox.is_visible(timeout=5000):
            print("🖱️ Clicando no Captcha...")
            
            # Movimento suave
            box = await checkbox.bounding_box()
            if box:
                await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2, steps=10)
                await asyncio.sleep(0.2)
                await page.mouse.down()
                await asyncio.sleep(0.1)
                await page.mouse.up()
            else:
                await checkbox.click()
            
            # 4. ESPERAR A VALIDAÇÃO DO GOOGLE
            print("⏳ Aguardando o 'Check' verde do Google...")
            # Espera até 10 segundos para a classe 'recaptcha-checkbox-checked' aparecer
            try:
                await frame.locator(".recaptcha-checkbox-checked").wait_for(state="visible", timeout=10000)
                print("✅ Captcha resolvido com sucesso!")
                await asyncio.sleep(1) # Segurança
                return True
            except:
                print("⚠️ O Captcha pediu desafio de imagens ou demorou. Tentando logar mesmo assim...")
                return False
        else:
            print("ℹ️ Checkbox do Captcha não encontrado (Pode não ter carregado).")
            return False

    except Exception as e:
        print(f"⚠️ Erro no processo do Captcha: {e}")
        return False

async def login_pennacorp_via_vivario(p):
    print("\n🔐 Iniciando Fluxo: Viva Rio -> Pennacorp...")

    # Argumentos para evitar detecção
    args = [
        "--disable-blink-features=AutomationControlled",
        "--start-maximized",
        "--no-sandbox",
        "--disable-infobars",
        "--disable-features=IsolateOrigins,site-per-process" # Ajuda com iframes
    ]

    browser = await p.chromium.launch(
        headless=False, 
        args=args,
        ignore_default_args=["--enable-automation"] 
    )

    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={'width': 1366, 'height': 768},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        java_script_enabled=True
    )

    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    # --- FASE 1: VIVA RIO ---
    page = await context.new_page()
    
    try:
        print("🌍 Acessando Viva Rio...")
        await page.goto(URL_PORTAL_VIVARIO, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        print("🖱 Abrindo menu 'Entrar'...")
        # Clica no menu
        await page.click(".login-btn .button.login")
        await asyncio.sleep(1)

        print("🖱 Clicando em 'Icarus'...")
        async with context.expect_page() as new_page_info:
            await page.click("a:has-text('Icarus')")

        new_page = await new_page_info.value
        await new_page.wait_for_load_state("domcontentloaded")
        print(f"✅ Nova aba Pennacorp aberta: {new_page.url}")

        # --- FASE 2: PENNACORP ---
        
        await injetar_local_storage(new_page)

        # Preenche dados RAPIDAMENTE antes do captcha expirar
        print("👤 Preenchendo Login...")
        await new_page.wait_for_selector("#login", state="visible", timeout=20000)
        await human_type(new_page, "#login", USUARIO_PENNA)
        
        print("🔑 Preenchendo Senha...")
        await human_type(new_page, "#pass", SENHA_PENNA)
        
        # =======================================================
        # RESOLUÇÃO DO CAPTCHA
        # =======================================================
        await resolver_captcha_profissional(new_page)
        # =======================================================

        print("🚀 Clicando Entrar...")
        # Garantir que o clique ocorra mesmo se o captcha demorou um pouco
        btn_entrar = new_page.locator("#entrar")
        
        # Tenta clicar usando JS se o clique normal falhar (burlar sobreposições)
        try:
            await btn_entrar.click(timeout=3000)
        except:
            print("⚠️ Clique normal falhou, forçando via JS...")
            await new_page.evaluate("document.getElementById('entrar').click()")

        # --- PÓS-LOGIN ---
        print("⏳ Aguardando acesso...")
        await new_page.wait_for_load_state("networkidle")
        await asyncio.sleep(5)

        # Tentar clicar em consulta produtos
        try:
            btn_consulta = new_page.locator("a:has-text('Consulta Produtos')")
            if await btn_consulta.is_visible(timeout=5000):
                await btn_consulta.click()
                print("✔ Entrando em Consulta Produtos!")
                await asyncio.sleep(3)
        except:
            pass

        print(f"✅ Finalizado! URL: {new_page.url}")
        return browser, context, new_page

    except Exception as e:
        print(f"❌ Erro Crítico: {e}")
        if 'browser' in locals():
            await browser.close()
        return None, None, None