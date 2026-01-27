import asyncio
from playwright.async_api import async_playwright

# ===================== IMPORTS DOS FORNECEDORES ===================== #
from controllers.fornecedores.Fornecedor1Controller import login as login_f1
from controllers.fornecedores.Fornecedor2Controller import login_roles as login_f2
from controllers.fornecedores.Fornecedor3Controller import login_acaraujo as login_f3
from controllers.fornecedores.Fornecedor4Controller import login_fornecedor4 as login_f4
from controllers.fornecedores.Fornecedor5Controller import login_jahu as login_f5
from controllers.fornecedores.Fornecedor6Controller import login_laguna_bypass as login_f6
from controllers.fornecedores.Fornecedor7Controller import login_rmp as login_f7
from controllers.fornecedores.Fornecedor8Controller import login_sama_bypass as login_f8

from controllers.fornecedores.Fornecedor9Controller import login_solroom as login_f9
from controllers.fornecedores.Fornecedor10Controller import login_matriz_bypass as login_f10
from controllers.fornecedores.Fornecedor11Controller import login_dpk_bypass as login_f11
from controllers.fornecedores.Fornecedor12Controller import login_takao_bypass as login_f12
from controllers.fornecedores.Fornecedor13Controller import login_skypecas as login_f13
from controllers.fornecedores.Fornecedor14Controller import login_sky_bypass as login_f14
from controllers.fornecedores.Fornecedor15Controller import login_riojc_bypass as login_f15
from controllers.fornecedores.Fornecedor16Controller import login_furacao_bypass as login_f16
from controllers.fornecedores.Fornecedor17Controller import login_pls_bypass as login_f17


# ===================== LISTA DE FORNECEDORES ===================== #
FORNECEDORES = [
    ("F1_PORTALCOMDIP", login_f1),
    ("F2_ROLES", login_f2),
    ("F3_ACARAUJO", login_f3),
    ("F4_GB", login_f4),
    ("F5_JAHU", login_f5),
    ("F6_LAGUNA", login_f6),
    ("F7_RMP", login_f7),
    ("F8_SAMA", login_f8),
    ("F9_SOLROOM", login_f9),
    ("F10_MATRIZ", login_f10),
    ("F11_DPK", login_f11),
    ("F12_TAKAO", login_f12),
    ("F13_SKYPEÇAS", login_f13),
    ("F14_SKY_PELLEGRINO", login_f14),
    ("F15_RIOJC", login_f15),
    ("F16_FURACAO", login_f16),
    ("F17_PLS", login_f17),
]


# ===================== UTIL ===================== #
def chunked(lista, tamanho):
    """Divide lista em blocos de tamanho fixo"""
    for i in range(0, len(lista), tamanho):
        yield lista[i:i + tamanho]


# ===================== EXECUÇÃO INDIVIDUAL ===================== #
async def executar_login(p, nome, login_fn):
    print(f"\n==================== 🔐 TESTE LOGIN {nome} ====================")

    try:
        browser, context, page = await login_fn(p)

        if browser and context and page:
            print(f"✅ {nome} → LOGIN OK")
            try:
                await context.close()
                await browser.close()
            except:
                pass
            return nome, True

        print(f"❌ {nome} → LOGIN FALHOU (retorno None)")
        return nome, False

    except Exception as e:
        print(f"🔥 {nome} → EXCEPTION NÃO TRATADA: {e}")
        return nome, False


# ===================== MAIN ===================== #
async def main():
    resultados = {}

    async with async_playwright() as p:

        # 🔁 Executa em lotes de 5
        for idx, grupo in enumerate(chunked(FORNECEDORES, 5), start=1):
            print(f"\n==================== 🚀 INICIANDO LOTE {idx} ====================")

            tarefas = [
                executar_login(p, nome, login_fn)
                for nome, login_fn in grupo
            ]

            respostas = await asyncio.gather(*tarefas, return_exceptions=False)

            for nome, ok in respostas:
                resultados[nome] = ok

            print(f"==================== ✅ LOTE {idx} FINALIZADO ====================")
            await asyncio.sleep(3)  # respiro entre lotes

    # ===================== RESUMO FINAL ===================== #
    print("\n==================== 📊 RESUMO FINAL ====================")

    ok_list = [k for k, v in resultados.items() if v]
    fail_list = [k for k, v in resultados.items() if not v]

    print(f"\n✅ LOGINS OK ({len(ok_list)}):")
    for f in ok_list:
        print(f"   - {f}")

    print(f"\n❌ LOGINS COM ERRO ({len(fail_list)}):")
    for f in fail_list:
        print(f"   - {f}")

    print("\n==================== 🏁 FIM DO TESTE ====================\n")


# ===================== ENTRYPOINT ===================== #
if __name__ == "__main__":
    asyncio.run(main())
