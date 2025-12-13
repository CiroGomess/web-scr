# controllers/dadosController.py
import os
import json
from datetime import datetime


HIST_DADOS_FOLDER = "data/hist_dados"


def carregar_lote_mais_recente():
   
    if not os.path.exists(HIST_DADOS_FOLDER):
        return {"error": "Pasta de histórico não encontrada", "lote_nome": None}

    # 1. Listar e ordenar para encontrar o mais recente
    all_files = os.listdir(HIST_DADOS_FOLDER)
    json_files = [f for f in all_files if f.endswith("_LOTE_processado.json")]
    
    if not json_files:
        return {"error": "Nenhum arquivo de lote de dados (.json) encontrado na pasta.", "lote_nome": None}
        
    def extract_timestamp(filename):
        try:
            timestamp_str = filename.split("_LOTE_processado.json")[0]
            return datetime.strptime(timestamp_str, "%d-%m-%Y_%H-%M-%S")
        except ValueError:
            return datetime.min

    json_files.sort(key=extract_timestamp, reverse=True)
    lote_mais_recente = json_files[0]
    
    caminho_completo = os.path.join(HIST_DADOS_FOLDER, lote_mais_recente)

    # 2. Carregar os dados
    try:
        with open(caminho_completo, "r", encoding="utf-8") as f:
            dados = json.load(f)
        
        # 3. 🎯 NOVO PASSO: FILTRAGEM DOS ITENS
        if "itens" in dados:
            
            # Filtra a lista 'itens', removendo qualquer item onde "codigo" é None
            itens_filtrados = [
                item for item in dados["itens"] if item.get("codigo") is not None
            ]
            
            # Atualiza os dados originais com a lista filtrada
            dados["itens"] = itens_filtrados
            
            # Opcional: Atualiza a contagem total de itens após a filtragem
            dados["total_itens_filtrados"] = len(itens_filtrados)
            
            print(f"✔ Filtragem concluída. {len(itens_filtrados)} itens válidos.")


        return {
            "lote_nome": lote_mais_recente,
            "dados": dados
        }
        
    except json.JSONDecodeError:
        return {"error": f"Erro ao decodificar JSON do arquivo: {lote_mais_recente}", "lote_nome": lote_mais_recente}
    except Exception as e:
        return {"error": f"Erro ao carregar o arquivo {lote_mais_recente}: {str(e)}", "lote_nome": lote_mais_recente}