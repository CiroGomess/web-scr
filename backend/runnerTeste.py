import asyncio
from playwright.async_api import async_playwright

# --- IMPORTS ---
from controllers.fornecedores.Fornecedor14Controller import login_sky_bypass
from controllers.produtos.produtoController14 import processar_lista_produtos_sequencial14

async def main():
    print("🚀 Iniciando Runner de Teste (Fornecedor 4 - GB)...")

    # ================= LISTA DE PRODUTOS COMPLETA ================= #
    # Raw string com os dados copiados (Código.Index)
    raw_list = """
31968.1
16792.1
21115.1
21136.1
18471.1
14712.1
21620.1
12964.3
13578.1
29449
03634.1
10535.1
13473.1
13475.1
12178.1
08939.1
03637.1
11726.1
13479.1
22411.4
03628.1
16265.1
10960.1
18893.1
29472.2
11166.1
23605.1
10791.1
11315.1
17540.1
15061.1
12699.1
18287.1
25635.2
25635.1
12964.5
14354.3
26791.2
15740.5
22785.2
25418.3
24257.4
20147.3
14993.2
22013.3
22629.2
20126.3
22420.3
01418.5
31817.1
05519.4
22227.4
09524.3
03628
16446.4
13578
10791
10791.2
11315
11166
12699
16265
13475
13479
03634
10535
12178
08939
03637
11089.4
22629.1
12964.1
11089.1
15092.1
10462.1
14993.1
20147.1
20156
25418
16446.1
15740.1
20057.1
22411.2
14354.1
26791
18287
21136
18893
23605
25635
21115
14712
21620
16792
13473
22785
24257.3
18471
20147.2
16446.5
22420.2
01418.3
05519.3
22227.1
29472.1
17540
11726
15061
10960
21561.1
28891
20126.5
24257.1
29472
16792.3
21136.2
18471.2
29449.1
13475.2
12178.2
14712.2
11726.2
11166.2
13578.2
12699.2
13473.2
11315.2
08939.2
10960.2
21115.2
16446.3
11089.2
20156.1
20126.1
22411.3
22013.1
21561.2
22411.1
01418.1
15476.1
09524.1
22420.1
05519.1
22227.2
29472.4
01418
14354
26791.1
12964
12964.4
25418.1
05519
11089
09524
15740
15476
10462
21561
16446
28891.1
15092
14993
31817
22420
20156.2
20147
22411
20057
20126
22785.1
22013
22629
22227
24257
22227.6
15476.4
15740.4
05519.5
09524.2
11089.5
15092.2
14993.3
31968
24257.2
14354.2
12964.6
01418.4
20126.4
22013.4
24257.5
22227.5
20057.2
20147.4
22420.4
01418.2
12964.2
10462.2
16446.2
20156.3
25418.2
11089.3
28891.2
15740.3
22013.2
05519.2
05519.6
15476.2
20126.2
22227.3
22785.3
29472.3
15740.2

    """

    # 🛠️ PROCESSAMENTO DA LISTA (Limpeza e Formatação)
    # Remove espaços, linhas vazias e remove o sufixo (.1, .2) se existir
    lista_limpa = []
    seen_codes = set() # Opcional: para evitar duplicatas exatas na mesma busca se desejar

    for line in raw_list.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Se tiver ponto (ex: 31968.1), pega só a parte antes do ponto (31968)
        # O usuário pediu quantidade 1 para todos
        if '.' in line:
            code_only = line.split('.')[0]
        else:
            code_only = line
        
        # Adiciona na lista com quantidade 1
        lista_limpa.append({"codigo": code_only, "quantidade": 1})

    print(f"📋 Lista processada: {len(lista_limpa)} itens carregados para busca.")
    print(f"🔍 Exemplo dos primeiros 5: {[i['codigo'] for i in lista_limpa[:5]]}...")

    # ================= EXECUÇÃO PLAYWRIGHT ================= #
    async with async_playwright() as p:

        # 1) Login
        try:
            login_data = await login_sky_bypass(p)
            browser, context, page = login_data
        except Exception as e:
            print(f"\n❌ Falha crítica no login: {e}")
            return

        if not page:
            print("\n❌ Falha crítica: O login não retornou uma página válida.")
            if browser:
                await browser.close()
            return

        print("\n--- ✅ Login OK. Iniciando Pesquisa de Produtos ---")

        # 2) Chama o processamento com a lista limpa
        try:
            resultados = await processar_lista_produtos_sequencial14(login_data, lista_limpa)
        except Exception as e:
            print(f"\n❌ Erro durante o processamento da lista: {e}")
            resultados = []

        # 3) Exibe Resultados
        print("\n--- 📊 Resultado do Teste ---")
        if not resultados:
            print("Nenhum resultado retornado.")
        else:
            print(f"Total processado: {len(resultados)}")
            # Mostra apenas os 5 últimos para não poluir o console, ou todos se preferir
            for item in resultados[-5:]: 
                print(f"[{item.get('codigo')}] {item.get('nome')} | {item.get('preco_formatado')}")

        print("\n🏁 Teste finalizado. Fechando em 5 segundos...")
        await asyncio.sleep(5)

        if browser:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())