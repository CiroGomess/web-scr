# runner_carrinho.py
from typing import Dict, Any, List
from playwright.async_api import async_playwright

# LOGINs
from controllers.fornecedores.Fornecedor1Controller import login as login_portalcomdip
from controllers.fornecedores.Fornecedor7Controller import login_rmp  # <- AQUI

# Ações carrinho
from controllers.addCarrinho.portalcomdip import adicionar_itens_ao_carrinho_portalcomdip
from controllers.addCarrinho.rmp import adicionar_itens_ao_carrinho_rmp  # <- AQUI


FORNECEDORES_CARRINHO = {
    "portalcomdip": {
        "login": login_portalcomdip,
        "add_to_cart": adicionar_itens_ao_carrinho_portalcomdip
    },
    "rmp": {
        "login": login_rmp,
        "add_to_cart": adicionar_itens_ao_carrinho_rmp
    }
}

# (Opcional) aceitar aliases que o front possa mandar
ALIASES = {
    "fornecedor 7 (rmp)": "rmp",
    "fornecedor7": "rmp",
    "loja.rmp.com.br": "rmp",
}


async def executar_automacao_carrinho(fornecedor: str, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    fornecedor_key = (fornecedor or "").strip().lower()
    fornecedor_key = ALIASES.get(fornecedor_key, fornecedor_key)

    if fornecedor_key not in FORNECEDORES_CARRINHO:
        return {
            "success": False,
            "error": f"Fornecedor '{fornecedor}' não mapeado para automação de carrinho.",
            "fornecedor_recebido": fornecedor,
            "fornecedor_key": fornecedor_key
        }

    async with async_playwright() as p:
        browser = None
        context = None
        page = None

        try:
            login_func = FORNECEDORES_CARRINHO[fornecedor_key]["login"]
            browser, context, page = await login_func(p)

            if not page:
                return {
                    "success": False,
                    "error": f"Falha no login do fornecedor '{fornecedor_key}'."
                }

            add_func = FORNECEDORES_CARRINHO[fornecedor_key]["add_to_cart"]
            resultado = await add_func(page, itens)

            return {
                "success": bool(resultado.get("success")),
                "fornecedor": fornecedor_key,
                "detalhes": resultado
            }

        except Exception as e:
            return {"success": False, "error": str(e), "fornecedor": fornecedor_key}

        finally:
            try:
                if browser:
                    await browser.close()
            except Exception:
                pass
