# utils/salvar_dados_processados.py

import os
import json
from datetime import datetime

# ============================================================
# 📌 Gerar data/hora BR
# ============================================================
def data_hora_br():
    agora = datetime.now()
    return agora.strftime("%d/%m/%Y %H:%M:%S")

# ============================================================
# 📌 Gerar nome do arquivo baseado no horário
# ============================================================
def gerar_nome_arquivo():
    agora = datetime.now()
    # Adicionamos "COMPLETO" no nome para diferenciar, se necessário
    return agora.strftime("%d-%m-%Y_%H-%M-%S_LOTE_processado.json")

# ============================================================
# 📌 Salvar a lista COMPLETA de itens de processamento
# Agora aceita 'lista_itens'
# ============================================================
def salvar_lista_processada(lista_itens, pasta="data/hist_dados"):

    # Cria pasta se não existir
    os.makedirs(pasta, exist_ok=True)
    
    # Prepara o objeto a ser salvo
    # Adicionamos um wrapper para a lista, e um timestamp para o LOTE
    dados_a_salvar = {
        "data_processamento_lote": data_hora_br(),
        "total_itens": len(lista_itens),
        "itens": lista_itens 
    }

    # Nome do arquivo
    nome_arquivo = gerar_nome_arquivo()
    caminho = os.path.join(pasta, nome_arquivo)

    # Salva o JSON
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados_a_salvar, f, ensure_ascii=False, indent=4)

    print(f"💾 Arquivo de LOTE salvo: {caminho}")

    return caminho

# (Você pode manter a função 'salvar_item_processado' se ela for usada em outro lugar,
# mas se não for, eu a removeria ou a renomearia para 'salvar_lista_processada' como acima.)
# Se você está usando salvar_item_processado dentro do 'produtoController', 
# talvez queira criar um novo arquivo 'salvar_lote.py' para a nova função.