import asyncio
import time
import traceback
from playwright.async_api import async_playwright

# ===================== IMPORTS LOGIN ===================== #
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

# ===================== IMPORTS PRODUTO ===================== #
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
from controllers.produtos.produtoController15 import processar_lista_produtos_sequencial15
from controllers.produtos.produtoController16 import processar_lista_produtos_sequencial16
from controllers.produtos.produtoController17 import processar_lista_produtos_sequencial17

# ===================== CONFIG ===================== #
BATCH_SIZE = 5

# ===================== MAPA FORNECEDORES ===================== #
FORNECEDORES = [
    ("F1", login_f1, processar_lista_produtos_parallel),
    ("F2", login_f2, processar_lista_produtos_sequencial2),
    ("F3", login_f3, processar_lista_produtos_sequencial3),
    ("F4", login_f4, processar_lista_produtos_sequencial4),
    ("F5", login_f5, processar_lista_produtos_acaraujo),
    ("F6", login_f6, processar_lista_produtos_sequencial6),
    ("F7", login_f7, processar_lista_produtos_sequencial1),
    ("F8", login_f8, processar_lista_produtos_sequencial8),
    ("F9", login_f9, processar_lista_produtos_sequencial9),
    ("F10", login_f10, processar_lista_produtos_sequencial10),
    ("F11", login_f11, processar_lista_produtos_sequencial11),
    ("F12", login_f12, processar_lista_produtos_sequencial12),
    ("F13", login_f13, processar_lista_produtos_sequencial_sky),
    ("F14", login_f14, processar_lista_produtos_sequencial14),
    ("F15", login_f15, processar_lista_produtos_sequencial15),
    ("F16", login_f16, processar_lista_produtos_sequencial16),
    ("F17", login_f17, processar_lista_produtos_sequencial17),
]

# ===================== UTIL ===================== #
def chunked(lista, size):
    for i in range(0, len(lista), size):
        yield lista[i:i + size]

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")

# ===================== RELATÓRIO TXT ===================== #
def salvar_relatorio_txt(resumo):
    with open("resultado_fornecedores.txt", "w", encoding="utf-8") as f:
        f.write("RELATÓRIO DE EXECUÇÃO DOS FORNECEDORES\n")
        f.write("=" * 45 + "\n\n")

        for item in resumo:
            nome = item["nome"]
            ok = item["ok"]
            qtd = item["qtd"]
            status = "OK" if ok else "ERRO"
            f.write(f"Fornecedor: {nome}\n")
            f.write(f"Status: {status}\n")
            f.write(f"Itens processados: {qtd}\n")
            f.write("-" * 45 + "\n")

    print("\n📄 Arquivo resultado_fornecedores.txt gerado com sucesso!")

# ===================== LOG (.log) ===================== #
def salvar_relatorio_log(resumo, arquivo="resultado_fornecedores.log"):
    with open(arquivo, "w", encoding="utf-8") as f:
        f.write(f"LOG DE EXECUÇÃO DOS FORNECEDORES - {now_str()}\n")
        f.write("=" * 80 + "\n\n")

        for item in resumo:
            f.write(f"[{item['fim']}] Fornecedor: {item['nome']}\n")
            f.write(f"Status: {'SUCESSO' if item['ok'] else 'FALHA'}\n")
            f.write(f"Itens processados: {item['qtd']}\n")

            if not item["ok"]:
                f.write(f"Motivo: {item.get('erro_msg') or 'Motivo não informado'}\n")
                tb = item.get("traceback")
                if tb:
                    f.write("Traceback:\n")
                    f.write(tb.strip() + "\n")
            f.write("-" * 80 + "\n\n")

    print(f"🧾 Arquivo {arquivo} gerado com sucesso!")

# ===================== EXECUÇÃO FORNECEDOR ===================== #
async def executar_fornecedor(p, nome, login_fn, produto_fn, lista_produtos):
    inicio = now_str()
    log(f"🔐 [{nome}] Iniciando login")

    browser = None
    context = None
    page = None

    try:
        browser, context, page = await login_fn(p)

        if not context:
            msg = "Login falhou (context=None)"
            log(f"❌ [{nome}] {msg}")
            return {
                "nome": nome,
                "ok": False,
                "qtd": 0,
                "inicio": inicio,
                "fim": now_str(),
                "erro_msg": msg,
                "traceback": None,
            }

        log(f"🔎 [{nome}] Login OK, iniciando busca de produtos")

        # 🔥 AJUSTE ESPECÍFICO PARA O F1
        if nome == "F1":
            resultados = await produto_fn(
                context=context,
                lista_produtos=lista_produtos,
                batch_size=BATCH_SIZE
            )
        else:
            resultados = await produto_fn(
                (browser, context, page),
                lista_produtos
            )

        log(f"✅ [{nome}] Finalizado ({len(resultados)} itens)")
        return {
            "nome": nome,
            "ok": True,
            "qtd": len(resultados),
            "inicio": inicio,
            "fim": now_str(),
            "erro_msg": None,
            "traceback": None,
        }

    except Exception as e:
        tb = traceback.format_exc()
        log(f"🔥 [{nome}] Erro crítico: {e}")
        return {
            "nome": nome,
            "ok": False,
            "qtd": 0,
            "inicio": inicio,
            "fim": now_str(),
            "erro_msg": str(e),
            "traceback": tb,
        }

    finally:
        try:
            if context:
                await context.close()
            if browser:
                await browser.close()
        except:
            pass

# ===================== MAIN ===================== #
async def main():

    # ================= LISTA DE PRODUTOS ================= #
    lista_produtos = [
        {"codigo": "31968", "quantidade": 1},
        {"codigo": "16792", "quantidade": 1},
        {"codigo": "21115", "quantidade": 1},
        {"codigo": "21136", "quantidade": 1},
        {"codigo": "18471", "quantidade": 1},
    ]

    log(f"📦 Total de produtos para teste: {len(lista_produtos)}")

    async with async_playwright() as p:
        resumo_execucao = []

        for idx, grupo in enumerate(chunked(FORNECEDORES, BATCH_SIZE), start=1):
            log(f"\n🚀 INICIANDO LOTE {idx} ({len(grupo)} fornecedores)")

            tarefas = [
                executar_fornecedor(p, nome, login_fn, produto_fn, lista_produtos)
                for nome, login_fn, produto_fn in grupo
            ]

            resultados = await asyncio.gather(*tarefas)

            for item in resultados:
                resumo_execucao.append(item)
                status = "OK" if item["ok"] else "ERRO"
                log(f"📊 [{item['nome']}] Status: {status} | Itens: {item['qtd']}")

                if not item["ok"] and item.get("erro_msg"):
                    log(f"   ↳ Motivo: {item['erro_msg']}")

            log(f"✅ LOTE {idx} FINALIZADO\n")
            await asyncio.sleep(5)

        # mantém seu txt simples
        salvar_relatorio_txt(resumo_execucao)

        # novo .log detalhado (com motivo/traceback)
        salvar_relatorio_log(resumo_execucao)

    log("🏁 Runner finalizado")

# ===================== ENTRY ===================== #
if __name__ == "__main__":
    asyncio.run(main())
