from flask import Flask, request, jsonify
import os
import asyncio
from datetime import datetime, timedelta
from flask_cors import CORS

# ===================== IMPORTAÇÕES DO FLASK JWT ===================== #
# Importamos o Manager e o decorador para proteger rotas
from flask_jwt_extended import JWTManager, jwt_required
from controllers.routes.userController import user_bp 
# ====================================================================

# Importação do Runner (Playwright)
from runner import main 

# Controllers
from controllers.dadosController import carregar_lote_mais_recente
from controllers.routes.comparandoProd import comparar_precos_entre_fornecedores


app = Flask(__name__, template_folder="views")

# ===================== CONFIGURAÇÃO DO JWT ========================== #
# 1. Chave Secreta
app.config["JWT_SECRET_KEY"] = "R4Z5ce3aeFWo9NTXIEiRHbx32aOuSPPz" 

# 2. Tempo de Expiração (240 dias = ~8 meses)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=240)

jwt = JWTManager(app)
# ====================================================================

CORS(app)

# ===================== REGISTRO DE BLUEPRINTS ======================= #
# Registra as rotas de usuário (/auth/login, /auth/register, etc)
# Isso permite que o frontend faça login e receba o token.
app.register_blueprint(user_bp)
# ====================================================================


UPLOAD_FOLDER = "data/temp"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"xlsx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ====================================================================
# 📂 ROTA DE UPLOAD (🔒 PROTEGIDA)
# ====================================================================
@app.route("/upload", methods=["POST"])
@jwt_required() # <--- Usuário precisa do Token para enviar arquivo
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "message": "Nenhum arquivo enviado"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"success": False, "message": "Arquivo inválido"}), 400

        if not allowed_file(file.filename):
            return jsonify({"success": False, "message": "Formato não permitido. Envie .xlsx"}), 400

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


# ====================================================================
# 🤖 ROTA DE PROCESSAMENTO (🔒 PROTEGIDA)
# ====================================================================
@app.route("/processar", methods=["POST"])
@jwt_required() # <--- Usuário precisa do Token para rodar o robô
def processar():
    try:
        # Executa o Playwright (main) para obter os resultados e salvar no banco
        try:
            result = asyncio.run(main())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(main())
        
        # O salvamento no Banco ocorre dentro do main() -> db_saver
        
        return jsonify({
            "message": "Processamento concluído!",
            "total_processado": result.get("total_processado", 0),
            "resultado": result 
        })

    except Exception as e:
        print("ERRO NO PROCESSAMENTO:", e)
        return jsonify(error=f"Erro ao processar: {str(e)}"), 500


# ====================================================================
# 📊 ROTA DE CONSULTA (🔒 PROTEGIDA)
# ====================================================================
@app.route("/produtos/consultar", methods=["GET"])
@jwt_required() # <--- Usuário precisa do Token para ver dados
def consultar_produtos_recentes():
    """
    Consulta e retorna todos os dados do arquivo JSON de lote mais recente.
    """
    try:
        resultado = carregar_lote_mais_recente()
        
        if "error" in resultado:
            status_code = 404 if "encontrado" in resultado["error"] else 500
            
            return jsonify({
                "message": "Falha na consulta de dados.",
                "error": resultado["error"]
            }), status_code

        return jsonify({
            "message": f"Dados carregados com sucesso do lote: {resultado['lote_nome']}",
            "dados_lote": resultado["dados"]
        }), 200

    except Exception as e:
        print(f"ERRO CRÍTICO NA ROTA: {str(e)}")
        return jsonify(error=f"Erro interno do servidor: {str(e)}"), 500


# ====================================================================
# ⚖️ ROTA DE COMPARAÇÃO (🔒 PROTEGIDA)
# ====================================================================
@app.route("/comparar", methods=["GET"])
@jwt_required() # <--- Usuário precisa do Token para comparar preços
def rota_comparar_produtos():
    """
    Rota que acessa o banco de dados e compara preços.
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