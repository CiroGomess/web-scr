# runner_carrinho.py
from typing import Dict, Any, List, Optional, Tuple
import asyncio
from playwright.async_api import async_playwright

# LOGINs
from controllers.fornecedores.Fornecedor1Controller import login as login_portalcomdip
from controllers.fornecedores.Fornecedor2Controller import login_roles
from controllers.fornecedores.Fornecedor3Controller import login_acaraujo
from controllers.fornecedores.Fornecedor4Controller import login_fornecedor4  # GB
from controllers.fornecedores.Fornecedor5Controller import login_jahu
from controllers.fornecedores.Fornecedor6Controller import login_laguna_bypass  # LAGUNA
from controllers.fornecedores.Fornecedor7Controller import login_rmp
from controllers.fornecedores.Fornecedor8Controller import login_sama_bypass  # SAMA
from controllers.fornecedores.Fornecedor9Controller import login_solroom  # SOLROOM
from controllers.fornecedores.Fornecedor10Controller import login_matriz_bypass  # SUPORTE MATRIZ
from controllers.fornecedores.Fornecedor11Controller import login_dpk_bypass  # DPK
from controllers.fornecedores.Fornecedor12Controller import login_takao_bypass  # TAKAO
from controllers.fornecedores.Fornecedor13Controller import login_skypecas
from controllers.fornecedores.Fornecedor14Controller import login_sky_bypass  # PELLEGRINO / SKY
from controllers.fornecedores.Fornecedor16Controller import login_furacao_bypass  # FURAÇÃO
from controllers.fornecedores.Fornecedor17Controller import login_pls_bypass  # ODAPEL / PLS <- NOVO

# Ações carrinho/pedido
from controllers.addCarrinho.portalcomdip import adicionar_itens_ao_carrinho_portalcomdip
from controllers.addCarrinho.rmp import adicionar_itens_ao_carrinho_rmp
from controllers.addCarrinho.roles import processar_lista_produtos_roles
from controllers.addCarrinho.acaraujo import processar_lista_produtos_acaraujo
from controllers.addCarrinho.gb import processar_lista_produtos_gb
from controllers.addCarrinho.lagunaautopecas import processar_lista_produtos_laguna
from controllers.addCarrinho.samaautopecas import processar_lista_produtos_sama
from controllers.addCarrinho.solroom import processar_lista_produtos_solroom
from controllers.addCarrinho.suportematriz import processar_lista_produtos_suportematriz
from controllers.addCarrinho.dpk import processar_lista_produtos_dpk
from controllers.addCarrinho.takao import processar_lista_produtos_takao
from controllers.addCarrinho.jahu import processar_lista_produtos_jahu
from controllers.addCarrinho.skypecas import processar_lista_produtos_skypecas
from controllers.addCarrinho.pellegrino import processar_lista_produtos_pellegrino
from controllers.addCarrinho.furacao import processar_lista_produtos_furacao
from controllers.addCarrinho.odapel import processar_lista_produtos_odapel


FORNECEDORES_CARRINHO = {
    "portalcomdip": {"login": login_portalcomdip, "add_to_cart": adicionar_itens_ao_carrinho_portalcomdip},
    "rmp": {"login": login_rmp, "add_to_cart": adicionar_itens_ao_carrinho_rmp},
    "roles": {"login": login_roles, "add_to_cart": processar_lista_produtos_roles},
    "acaraujo": {"login": login_acaraujo, "add_to_cart": processar_lista_produtos_acaraujo},
    "gb": {"login": login_fornecedor4, "add_to_cart": processar_lista_produtos_gb},
    "laguna": {"login": login_laguna_bypass, "add_to_cart": processar_lista_produtos_laguna},
    "sama": {"login": login_sama_bypass, "add_to_cart": processar_lista_produtos_sama},
    "solroom": {"login": login_solroom, "add_to_cart": processar_lista_produtos_solroom},
    "suportematriz": {"login": login_matriz_bypass, "add_to_cart": processar_lista_produtos_suportematriz},
    "dpk": {"login": login_dpk_bypass, "add_to_cart": processar_lista_produtos_dpk},
    "takao": {"login": login_takao_bypass, "add_to_cart": processar_lista_produtos_takao},

    "pellegrino": {"login": login_sky_bypass, "add_to_cart": processar_lista_produtos_pellegrino},
    "furacao": {"login": login_furacao_bypass, "add_to_cart": processar_lista_produtos_furacao},
    "odapel": {"login": login_pls_bypass, "add_to_cart": processar_lista_produtos_odapel},

    "jahu": {"login": login_jahu, "add_to_cart": processar_lista_produtos_jahu},
    "skypecas": {"login": login_skypecas, "add_to_cart": processar_lista_produtos_skypecas},
}

# (Opcional) aliases que o front pode mandar
ALIASES = {
    "fornecedor 7 (rmp)": "rmp",
    "fornecedor7": "rmp",
    "loja.rmp.com.br": "rmp",
    "rmp": "rmp",

    "fornecedor2": "roles",
    "fornecedor 2 (roles)": "roles",
    "compreonline roles": "roles",
    "compreonline roles.com.br": "roles",
    "compreonline.roles.com.br": "roles",
    "roles": "roles",

    "fornecedor3": "acaraujo",
    "fornecedor 3 (acaraujo)": "acaraujo",
    "acaraujo": "acaraujo",
    "a caraujo": "acaraujo",
    "portal.acaraujo.com.br": "acaraujo",
    "https://portal.acaraujo.com.br": "acaraujo",
    "https://portal.acaraujo.com.br/": "acaraujo",

    "fornecedor4": "gb",
    "fornecedor 4 (gb)": "gb",
    "gb": "gb",
    "g&b": "gb",
    "g e b": "gb",
    "ecommerce.gb.com.br": "gb",
    "https://ecommerce.gb.com.br": "gb",
    "https://ecommerce.gb.com.br/": "gb",

    "fornecedor6": "laguna",
    "fornecedor 6 (laguna)": "laguna",
    "laguna": "laguna",
    "laguna autopecas": "laguna",
    "laguna autopeças": "laguna",
    "compreonline.lagunaautopecas.com.br": "laguna",
    "https://compreonline.lagunaautopecas.com.br": "laguna",
    "https://compreonline.lagunaautopecas.com.br/": "laguna",

    "fornecedor8": "sama",
    "fornecedor 8 (sama)": "sama",
    "sama": "sama",
    "sama autopecas": "sama",
    "sama autopeças": "sama",
    "compreonline.samaautopecas.com.br": "sama",
    "https://compreonline.samaautopecas.com.br": "sama",
    "https://compreonline.samaautopecas.com.br/": "sama",

    "fornecedor9": "solroom",
    "fornecedor 9 (solroom)": "solroom",
    "solroom": "solroom",
    "sol room": "solroom",
    "sol room rj": "solroom",
    "solroom.com.br": "solroom",
    "https://solroom.com.br": "solroom",
    "https://solroom.com.br/": "solroom",

    "fornecedor10": "suportematriz",
    "fornecedor 10 (suporte matriz)": "suportematriz",
    "suporte matriz": "suportematriz",
    "matriz": "suportematriz",
    "suportematriz": "suportematriz",
    "suportematriz.ddns.net:5006": "suportematriz",
    "http://suportematriz.ddns.net:5006": "suportematriz",
    "http://suportematriz.ddns.net:5006/": "suportematriz",

    "fornecedor11": "dpk",
    "fornecedor 11 (dpk)": "dpk",
    "dpk": "dpk",

    "fornecedor12": "takao",
    "fornecedor 12 (takao)": "takao",
    "takao": "takao",

    "fornecedor14": "pellegrino",
    "fornecedor 14 (pellegrino)": "pellegrino",
    "pellegrino": "pellegrino",
    "sky": "pellegrino",
    "compreonline.pellegrino.com.br": "pellegrino",
    "https://compreonline.pellegrino.com.br": "pellegrino",
    "https://compreonline.pellegrino.com.br/": "pellegrino",

    "fornecedor16": "furacao",
    "fornecedor 16 (furacao)": "furacao",
    "furacao": "furacao",
    "furacão": "furacao",
    "furacao": "furacao",
    "furação": "furacao",
    "vendas.furacao.com.br": "furacao",
    "https://vendas.furacao.com.br": "furacao",
    "https://vendas.furacao.com.br/": "furacao",

    "fornecedor17": "odapel",
    "fornecedor 17 (odapel)": "odapel",
    "fornecedor 17 (pls)": "odapel",
    "odapel": "odapel",
    "pls": "odapel",
    "plsweb": "odapel",
    "pls web": "odapel",
    "/movimentacao": "odapel",

    "fornecedor5": "jahu",
    "fornecedor 5 (jahu)": "jahu",
    "jahu": "jahu",
    "b2b jahu": "jahu",
    "b2b.jahu.com.br": "jahu",

    "fornecedor13": "skypecas",
    "fornecedor 13 (skypecas)": "skypecas",
    "skypecas": "skypecas",
    "sky peças": "skypecas",
    "sky pecas": "skypecas",
    "cliente.skypecas.com.br": "skypecas",
    "https://cliente.skypecas.com.br": "skypecas",
    "https://cliente.skypecas.com.br/": "skypecas",
}


# ============================================================
# ✅ TESTE DE LOGIN (mesmo padrão do runner.py)
# ============================================================
async def testar_login(login_func, playwright_instance, timeout_segundos=60):
    try:
        browser, context, page = await asyncio.wait_for(
            login_func(playwright_instance),
            timeout=timeout_segundos,
        )

        if not browser or not context or not page:
            return (False, browser, context, page, "Login não retornou browser/context/page válidos")

        if page.is_closed():
            return (False, browser, context, page, "Page veio fechada após login")

        return (True, browser, context, page, "")

    except asyncio.TimeoutError:
        return (False, None, None, None, f"Timeout no login ({timeout_segundos}s)")
    except Exception as e:
        return (False, None, None, None, str(e))


# ============================================================
# ✅ EXECUTA 1 FORNECEDOR (carrinho) com SEMAPHORE
# ============================================================
async def executar_fornecedor_carrinho(fornecedor_key: str, itens: List[Dict[str, Any]], playwright_instance, sem: asyncio.Semaphore):
    async with sem:
        browser = None
        nome_log = fornecedor_key

        try:
            if fornecedor_key not in FORNECEDORES_CARRINHO:
                return {
                    "success": False,
                    "fornecedor": fornecedor_key,
                    "error": f"Fornecedor '{fornecedor_key}' não mapeado.",
                }

            login_func = FORNECEDORES_CARRINHO[fornecedor_key]["login"]
            add_func = FORNECEDORES_CARRINHO[fornecedor_key]["add_to_cart"]

            print(f"\n--- 🛒 Iniciando carrinho: {nome_log} ---")

            ok, browser, context, page, erro_login = await testar_login(login_func, playwright_instance, timeout_segundos=60)

            if not ok:
                print(f"❌ Falha no login de {nome_log}: {erro_login}")
                return {
                    "success": False,
                    "fornecedor": fornecedor_key,
                    "error": erro_login,
                }

            print(f"✅ Login OK: {nome_log}. Adicionando itens...")

            resultado = await add_func(page, itens)

            return {
                "success": bool((resultado or {}).get("success")),
                "fornecedor": fornecedor_key,
                "detalhes": resultado,
            }

        except Exception as e:
            print(f"🔥 Erro no carrinho {nome_log}: {e}")
            return {"success": False, "fornecedor": fornecedor_key, "error": str(e)}

        finally:
            try:
                if browser:
                    await browser.close()
                    print(f"🔒 Navegador fechado (carrinho): {nome_log}")
            except Exception:
                pass


def _normalizar_fornecedor_key(fornecedor: str) -> str:
    fk = (fornecedor or "").strip().lower()
    return ALIASES.get(fk, fk)


# ============================================================
# ✅ MODO ANTIGO (1 fornecedor) - mantém compatibilidade
# ============================================================
async def executar_automacao_carrinho(
    fornecedor: str,
    itens: List[Dict[str, Any]],
) -> Dict[str, Any]:
    fornecedor_key = _normalizar_fornecedor_key(fornecedor)

    if fornecedor_key not in FORNECEDORES_CARRINHO:
        return {
            "success": False,
            "error": f"Fornecedor '{fornecedor}' não mapeado para automação de carrinho.",
            "fornecedor_recebido": fornecedor,
            "fornecedor_key": fornecedor_key,
        }

    async with async_playwright() as p:
        sem = asyncio.Semaphore(1)
        return await executar_fornecedor_carrinho(fornecedor_key, itens, p, sem)


# ============================================================
# ✅ NOVO: EXECUTA VÁRIOS FORNECEDORES com concorrência=5
# ============================================================
async def executar_automacao_carrinho_em_lotes(
    fornecedores: List[str],
    itens: List[Dict[str, Any]],
    concorrencia_fornecedores: int = 5,
) -> Dict[str, Any]:
    # normaliza + remove duplicados mantendo ordem
    fornecedores_keys = []
    seen = set()
    invalidos = []

    for f in (fornecedores or []):
        fk = _normalizar_fornecedor_key(f)
        if fk not in FORNECEDORES_CARRINHO:
            invalidos.append({"fornecedor_recebido": f, "fornecedor_key": fk})
            continue
        if fk in seen:
            continue
        seen.add(fk)
        fornecedores_keys.append(fk)

    if not fornecedores_keys:
        return {
            "success": False,
            "error": "Nenhum fornecedor válido para processar.",
            "invalidos": invalidos,
            "resultados": [],
        }

    sem = asyncio.Semaphore(concorrencia_fornecedores)

    async with async_playwright() as p:
        tarefas = [
            executar_fornecedor_carrinho(fk, itens, p, sem)
            for fk in fornecedores_keys
        ]
        resultados = await asyncio.gather(*tarefas)

    ok = sum(1 for r in resultados if r.get("success"))
    falha = len(resultados) - ok

    return {
        "success": True,
        "concorrencia": concorrencia_fornecedores,
        "fornecedores_total": len(resultados),
        "ok": ok,
        "falha": falha,
        "invalidos": invalidos,
        "resultados": resultados,
    }
