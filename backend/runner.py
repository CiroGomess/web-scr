import asyncio
from playwright.async_api import async_playwright

from utils.xlsx_loader import get_latest_xlsx, load_produtos_from_xlsx

# -------------------------
# LOGINS (FORNECEDORES)
# -------------------------
from controllers.fornecedores.Fornecedor1Controller import login as login_portalcomdip
from controllers.fornecedores.Fornecedor2Controller import login_roles
from controllers.fornecedores.Fornecedor3Controller import login_acaraujo
from controllers.fornecedores.Fornecedor4Controller import login_fornecedor4          # GB
from controllers.fornecedores.Fornecedor5Controller import login_jahu
from controllers.fornecedores.Fornecedor6Controller import login_laguna_bypass       # LAGUNA
from controllers.fornecedores.Fornecedor7Controller import login_rmp
from controllers.fornecedores.Fornecedor8Controller import login_sama_bypass         # SAMA
from controllers.fornecedores.Fornecedor9Controller import login_solroom             # SOLROOM
from controllers.fornecedores.Fornecedor10Controller import login_matriz_bypass      # SUPORTE MATRIZ
from controllers.fornecedores.Fornecedor11Controller import login_dpk_bypass         # DPK
from controllers.fornecedores.Fornecedor12Controller import login_takao_bypass       # TAKAO
from controllers.fornecedores.Fornecedor13Controller import login_skypecas
from controllers.fornecedores.Fornecedor14Controller import login_sky_bypass         # PELLEGRINO / SKY
from controllers.fornecedores.Fornecedor16Controller import login_furacao_bypass     # FURAÇÃO
from controllers.fornecedores.Fornecedor17Controller import login_pls_bypass         # ODAPEL / PLS

# -------------------------
# PROCESSAMENTOS (PRODUTOS)
# -------------------------
from controllers.produtos.produtoController1 import processar_lista_produtos_parallel
from controllers.produtos.produtoController2 import processar_lista_produtos_sequencial2
from controllers.produtos.produtoController3 import processar_lista_produtos_sequencial3
from controllers.produtos.produtoController4 import processar_lista_produtos_sequencial4
from controllers.produtos.produtoController5 import processar_lista_produtos_acaraujo
from controllers.produtos.produtoController6 import processar_lista_produtos_sequencial6
from controllers.produtos.produtoController7 import processar_lista_produtos_sequencial1
from controllers.produtos.produtoController8 import processar_lista_produtos_sequencial8
from controllers.produtos.produtoController9 import processar_lista_produtos_sequencial9
from controllers.produtos.produtoController10 import processar_lista_produtos_sequencial10
from controllers.produtos.produtoController11 import processar_lista_produtos_sequencial11
from controllers.produtos.produtoController12 import processar_lista_produtos_sequencial12
from controllers.produtos.produtoController13 import processar_lista_produtos_sequencial_sky
from controllers.produtos.produtoController14 import processar_lista_produtos_sequencial14
from controllers.produtos.produtoController16 import processar_lista_produtos_sequencial16
from controllers.produtos.produtoController17 import processar_lista_produtos_sequencial17


# ============================================================
# ✅ TESTE DE LOGIN
# ============================================================
async def testar_login(login_func, playwright_instance, timeout_segundos=60):
    try:
        browser, context, page = await asyncio.wait_for(
            login_func(playwright_instance),
            timeout=timeout_segundos
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
# ✅ EXECUTA 1 FORNECEDOR (com limite de concorrência)
# ============================================================
async def executar_fornecedor(config, playwright_instance, lista_produtos, sem):
    nome = config["nome"]

    async with sem:
        print(f"\n--- 🚀 Iniciando: {nome} ---")

        browser = None
        try:
            ok, browser, context, page, erro_login = await testar_login(
                config["login_func"], playwright_instance, timeout_segundos=60
            )

            if not ok:
                print(f"❌ Falha no login de {nome}: {erro_login}. Pulando...")
                return {
                    "fornecedor": nome,
                    "login_ok": False,
                    "erro": erro_login,
                    "itens": 0,
                    "dados": []
                }

            print(f"✅ Login {nome} realizado. Extraindo dados...")

            if config["tipo"] == "parallel":
                dados_fornecedor = await config["process_func"](context, lista_produtos, batch_size=5)
            else:
                dados_fornecedor = await config["process_func"](page, lista_produtos)

            qtd = len(dados_fornecedor) if dados_fornecedor else 0

            if qtd:
                print(f"📥 {qtd} itens processados em {nome}.")
            else:
                print(f"⚠️ Nenhum dado retornado de {nome}.")

            return {
                "fornecedor": nome,
                "login_ok": True,
                "erro": "",
                "itens": qtd,
                "dados": dados_fornecedor or []
            }

        except Exception as e:
            print(f"🔥 Erro crítico ao processar {nome}: {str(e)}")
            return {
                "fornecedor": nome,
                "login_ok": False,
                "erro": str(e),
                "itens": 0,
                "dados": []
            }

        finally:
            if browser:
                await browser.close()
                print(f"🔒 Navegador de {nome} fechado.")


async def main(concorrencia_fornecedores=5):
    async with async_playwright() as p:

        # 1) Buscar XLSX mais recente
        pasta_temp = "data/temp"
        ultimo_arquivo = get_latest_xlsx(pasta_temp)

        if not ultimo_arquivo:
            return {"erro": "Nenhum arquivo XLSX encontrado na pasta /data/temp"}

        print(f"📂 Carregando arquivo: {ultimo_arquivo}")

        # 2) Carregar produtos
        lista_produtos = load_produtos_from_xlsx(ultimo_arquivo)
        if not lista_produtos:
            return {"erro": "Nenhum produto válido encontrado no XLSX"}

        print(f"📦 {len(lista_produtos)} produtos carregados para processamento.")

        fornecedores_config = [
            # {"nome": "Fornecedor 1 (PortalComDip)", "login_func": login_portalcomdip, "process_func": processar_lista_produtos_parallel, "tipo": "parallel"},
            # {"nome": "Fornecedor 2 (Roles)", "login_func": login_roles, "process_func": processar_lista_produtos_sequencial2, "tipo": "sequencial"},
            # {"nome": "Fornecedor 3 (Acaraujo)", "login_func": login_acaraujo, "process_func": processar_lista_produtos_sequencial3, "tipo": "sequencial"},
            # {"nome": "Fornecedor 4 (GB)", "login_func": login_fornecedor4, "process_func": processar_lista_produtos_sequencial4, "tipo": "sequencial"},
            # {"nome": "Fornecedor 5 (Jahu)", "login_func": login_jahu, "process_func": processar_lista_produtos_acaraujo, "tipo": "sequencial"},
            {"nome": "Fornecedor 6 (Laguna)", "login_func": login_laguna_bypass, "process_func": processar_lista_produtos_sequencial6, "tipo": "sequencial"},
            # {"nome": "Fornecedor 7 (RMP)", "login_func": login_rmp, "process_func": processar_lista_produtos_sequencial1, "tipo": "sequencial"},
            {"nome": "Fornecedor 8 (Sama)", "login_func": login_sama_bypass, "process_func": processar_lista_produtos_sequencial8, "tipo": "sequencial"},
            # {"nome": "Fornecedor 9 (Solroom)", "login_func": login_solroom, "process_func": processar_lista_produtos_sequencial9, "tipo": "sequencial"},
            # {"nome": "Fornecedor 10 (Matriz)", "login_func": login_matriz_bypass, "process_func": processar_lista_produtos_sequencial10, "tipo": "sequencial"},
            # {"nome": "Fornecedor 11 (DPK)", "login_func": login_dpk_bypass, "process_func": processar_lista_produtos_sequencial11, "tipo": "sequencial"},
            # {"nome": "Fornecedor 12 (Takao)", "login_func": login_takao_bypass, "process_func": processar_lista_produtos_sequencial12, "tipo": "sequencial"},
            # {"nome": "Fornecedor 13 (Skypecas)", "login_func": login_skypecas, "process_func": processar_lista_produtos_sequencial_sky, "tipo": "sequencial"},
            # {"nome": "Fornecedor 14 (Sky/Pellegrino)", "login_func": login_sky_bypass, "process_func": processar_lista_produtos_sequencial14, "tipo": "sequencial"},
            # {"nome": "Fornecedor 16 (Furacao)", "login_func": login_furacao_bypass, "process_func": processar_lista_produtos_sequencial16, "tipo": "sequencial"},
            # {"nome": "Fornecedor 17 (PLS/Odapel)", "login_func": login_pls_bypass, "process_func": processar_lista_produtos_sequencial17, "tipo": "sequencial"},
        ]

        sem = asyncio.Semaphore(concorrencia_fornecedores)

        # Dispara tudo, mas o semaphore limita para 3 ao mesmo tempo
        tarefas = [
            executar_fornecedor(cfg, p, lista_produtos, sem)
            for cfg in fornecedores_config
        ]

        resultados_fornecedores = await asyncio.gather(*tarefas)

        # Consolidação final
        todos_resultados = []
        status_fornecedores = []

        for r in resultados_fornecedores:
            status_fornecedores.append({
                "fornecedor": r["fornecedor"],
                "login_ok": r["login_ok"],
                "erro": r["erro"],
                "itens": r["itens"]
            })
            if r["dados"]:
                todos_resultados.extend(r["dados"])

        total_ok = sum(1 for s in status_fornecedores if s["login_ok"])
        total_fail = len(status_fornecedores) - total_ok

        return {
            "status": "ok",
            "total_processado": len(todos_resultados),
            "dados": todos_resultados,
            "relatorio": {
                "fornecedores_total": len(status_fornecedores),
                "logins_ok": total_ok,
                "logins_falha": total_fail,
                "detalhes": status_fornecedores
            }
        }


if __name__ == "__main__":
    resultado = asyncio.run(main(concorrencia_fornecedores=3))
    print(f"\nRESUMO FINAL: {resultado.get('total_processado', 0)} itens extraídos no total.")
    rel = resultado.get("relatorio", {})
    print(f"LOGINS OK: {rel.get('logins_ok', 0)} | LOGINS FALHA: {rel.get('logins_falha', 0)}")
