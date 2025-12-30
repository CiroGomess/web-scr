from flask import Flask, request, jsonify
import os
import asyncio
from runner import main  # importa sua função Playwright
from datetime import datetime
from flask_cors import CORS

from controllers.dadosController import carregar_lote_mais_recente

# IMPORTAÇÃO DA NOVA ROTA DE COMPARAÇÃO
from controllers.routes.comparandoProd import comparar_precos_entre_fornecedores


app = Flask(__name__, template_folder="views")
CORS(app)


UPLOAD_FOLDER = "data/temp"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"xlsx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({
                "success": False,
                "message": "Nenhum arquivo enviado"
            }), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({
                "success": False,
                "message": "Arquivo inválido"
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "message": "Formato não permitido. Envie .xlsx"
            }), 400

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        original = file.filename.replace(" ", "_")
        final_name = f"{timestamp}_{original}"

        save_path = os.path.join(UPLOAD_FOLDER, final_name)
        file.save(save_path)

        return jsonify({
            "success": True,
            "message": "Upload realizado com sucesso!",
            "data": {
                "file_path": save_path,
                "saved_as": final_name
            }
        }), 200

    except Exception as e:
        print("ERRO NO UPLOAD:", e)
        return jsonify({
            "success": False,
            "message": "Erro interno no servidor",
            "error": str(e)
        }), 500



@app.route("/processar", methods=["POST"])
def processar():

    try:
        # 1. Executa o Playwright para obter os resultados
        try:
            result = asyncio.run(main())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(main())
    
        

        # 4. Retorna a resposta JSON completa
        return jsonify({
            "message": "Processamento concluído e LOTE de dados salvo em um único arquivo!",
            "total_processado": result.get("total_processado", 0),
            "resultado": result # Retorna o resultado completo original do runner
        })

    except Exception as e:
        print("ERRO NO PROCESSAMENTO:", e)
        return jsonify(error=f"Erro ao processar: {str(e)}"), 500
@app.route("/produtos/consultar", methods=["GET"])
def consultar_produtos_recentes():
    """
    Consulta e retorna todos os dados do arquivo JSON de lote mais recente.
    """
    
    try:
        # Chama a função que encontra e lê o arquivo mais recente
        resultado = carregar_lote_mais_recente()
        
        # 1. Verifica se houve erro
        if "error" in resultado:
            status_code = 404 if "encontrado" in resultado["error"] else 500
            
            return jsonify({
                "message": "Falha na consulta de dados.",
                "error": resultado["error"]
            }), status_code

        # 2. Retorna os dados com sucesso
        return jsonify({
            "message": f"Dados carregados com sucesso do lote: {resultado['lote_nome']}",
            "dados_lote": resultado["dados"]
        }), 200

    except Exception as e:
        print(f"ERRO CRÍTICO NA ROTA: {str(e)}")
        return jsonify(error=f"Erro interno do servidor: {str(e)}"), 500



@app.route("/comparar", methods=["GET"])
def rota_comparar_produtos():
    """
    Rota que acessa o banco de dados, pega todos os produtos salvos
    e retorna quem é o fornecedor mais barato para cada código.
    """
    try:
        resultado = comparar_precos_entre_fornecedores()
        
        if not resultado["success"]:
            return jsonify({"error": resultado["error"]}), 500
            
        return jsonify(resultado), 200

    except Exception as e:
        return jsonify(error=f"Erro na rota de comparação: {str(e)}"), 500

if __name__ == "__main__":
    app.run(debug=True)
