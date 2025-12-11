import os
from glob import glob
import openpyxl

def get_latest_xlsx(folder_path):
    """Retorna o arquivo XLSX mais recente dentro da pasta especificada."""
    files = glob(os.path.join(folder_path, "*.xlsx"))
    if not files:
        return None
    latest_file = max(files, key=os.path.getmtime)
    return latest_file


def load_produtos_from_xlsx(file_path):
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wb.active

    produtos = []

    # Encontrar índices das colunas automaticamente
    headers = {cell.value: idx for idx, cell in enumerate(sheet[1])}

    col_cod = headers.get("CM_COD_AUT")
    col_qtd = headers.get("CM_QTD_DSP")

    if col_cod is None or col_qtd is None:
        raise Exception("Colunas CM_COD_AUT ou CM_QTD_DSP não foram encontradas no XLSX")

    for row in sheet.iter_rows(min_row=2):
        raw_codigo = row[col_cod].value
        quantidade = row[col_qtd].value

        # Ignorar linhas com quantidade inválida
        if not quantidade or quantidade <= 0:
            continue

        if raw_codigo is None:
            continue

        # Converter código "31968.1" → "31968"
        codigo_str = str(raw_codigo).split(".")[0]

        produtos.append({
            "codigo": codigo_str,
            "quantidade": int(quantidade)
        })

    return produtos
