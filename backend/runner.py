import asyncio
from playwright.async_api import async_playwright
from controllers.Fornecedor1Controller import login
from controllers.produtoController import processar_lista_produtos_parallel
from utils.xlsx_loader import get_latest_xlsx, load_produtos_from_xlsx


async def main():
    async with async_playwright() as p:

        # Buscar XLSX mais recente
        pasta_temp = "data/temp"
        ultimo_arquivo = get_latest_xlsx(pasta_temp)

        if not ultimo_arquivo:
            return {"erro": "Nenhum arquivo XLSX encontrado na pasta /data/temp"}

        print(f"Carregando arquivo: {ultimo_arquivo}")

        # Carregar produtos do arquivo
        lista_produtos = load_produtos_from_xlsx(ultimo_arquivo)

        if not lista_produtos:
            return {"erro": "Nenhum produto válido encontrado no XLSX"}

        print(f"{len(lista_produtos)} produtos encontrados para processamento")

        # Login
        browser, context, page = await login(p)

        if not page:
            return {"erro": "Não foi possível logar."}

        # Processamento paralelo
        resultados = await processar_lista_produtos_parallel(
            context,
            lista_produtos,
            batch_size=5
        )

        return {
            "status": "ok",
            "total_processado": len(resultados),
            "dados": resultados
        }
