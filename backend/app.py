from flask import Flask, request, jsonify
import os
import asyncio
from datetime import datetime, timedelta
from flask_cors import CORS

# ===================== IMPORTAÇÕES DO FLASK JWT ===================== #
from flask_jwt_extended import JWTManager, jwt_required
from controllers.routes.userController import user_bp
# ====================================================================
from services.db_saver import limpar_banco_processamento

# Importação do Runner de Processamento de Dados (Extração)
from runner import main

# 🟢 Runner do Carrinho de Compras
from runner_carrinho import executar_automacao_carrinho

# Controllers
from controllers.dadosController import carregar_lote_mais_recente
from controllers.routes.comparandoProd import comparar_precos_entre_fornecedores
from configs.db import get_connection
from zoneinfo import ZoneInfo





app = Flask(__name__, template_folder="views")

# ===================== CONFIGURAÇÃO DO JWT ========================== #
app.config["JWT_SECRET_KEY"] = "R4Z5ce3aeFWo9NTXIEiRHbx32aOuSPPz"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=240)

jwt = JWTManager(app)
# ====================================================================

CORS(app)

# ===================== REGISTRO DE BLUEPRINTS ======================= #
app.register_blueprint(user_bp)
# ====================================================================

UPLOAD_FOLDER = "data/temp"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"xlsx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def atualizar_ultimo_processamento(dt_br):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO controle_ultimo_processamento (id, ultima_data_processamento, atualizado_em)
            VALUES (1, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET ultima_data_processamento = EXCLUDED.ultima_data_processamento,
                atualizado_em = EXCLUDED.atualizado_em;
        """, (dt_br, dt_br))

        conn.commit()

    except Exception:
        if conn:
            conn.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()



# ====================================================================
# 📂 ROTA DE UPLOAD (🔒 PROTEGIDA)
# ====================================================================
@app.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "message": "Nenhum arquivo enviado"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"success": False, "message": "Arquivo inválido"}), 400

        if not allowed_file(file.filename):
            return jsonify({"success": False, "message": "Formato não permitido. Envie .xlsx"}), 400

        # Data/hora Brasil (Fortaleza)
        br_tz = ZoneInfo("America/Fortaleza")
        now_br = datetime.now(br_tz)

        timestamp = now_br.strftime("%Y-%m-%d_%H-%M-%S")
        original = file.filename.replace(" ", "_")
        final_name = f"{timestamp}_{original}"

        save_path = os.path.join(UPLOAD_FOLDER, final_name)
        file.save(save_path)

        # Atualiza no banco a última data de processamento
        try:
            atualizar_ultimo_processamento(now_br)
        except Exception as db_err:
            # Se falhar no banco, você pode optar por remover o arquivo para não ficar "upload sem registro"
            try:
                os.remove(save_path)
            except Exception:
                pass

            return jsonify({
                "success": False,
                "message": "Upload salvo, mas falhou ao registrar no banco",
                "error": str(db_err)
            }), 500

        return jsonify({
            "success": True,
            "message": "Upload realizado com sucesso!",
            "data": {
                "file_path": save_path,
                "saved_as": final_name,
                "data_processamento_br": now_br.isoformat()
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
# 🤖 ROTA DE PROCESSAMENTO DE DADOS (EXTRAÇÃO)
# ====================================================================
@app.route("/processar", methods=["POST"])
@jwt_required()
def processar():
    try:
        # ✅ Limpa o banco antes de iniciar um novo processamento
        limpeza = limpar_banco_processamento()
        if not limpeza.get("success"):
            return jsonify(error=f"Erro ao limpar banco: {limpeza.get('error')}"), 500

        try:
            result = asyncio.run(main())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(main())

        return jsonify({
            "message": "Processamento concluído!",
            "total_processado": result.get("total_processado", 0),
            "resultado": result
        })

    except Exception as e:
        print("ERRO NO PROCESSAMENTO:", e)
        return jsonify(error=f"Erro ao processar: {str(e)}"), 500


# ====================================================================
# 📊 ROTA DE CONSULTA
# ====================================================================
@app.route("/produtos/consultar", methods=["GET"])
@jwt_required()
def consultar_produtos_recentes():
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
# ⚖️ ROTA DE COMPARAÇÃO
# ====================================================================
@app.route("/comparar", methods=["GET"])
@jwt_required()
def rota_comparar_produtos():
    try:
        resultado = comparar_precos_entre_fornecedores()

        if not resultado["success"]:
            return jsonify({"error": resultado["error"]}), 500

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify(error=f"Erro na rota de comparação: {str(e)}"), 500


# ====================================================================
# 🛒 ROTA DE AUTOMAÇÃO DE CARRINHO (ROBÔ DE COMPRA)
# ====================================================================
@app.route("/automacao/carrinho/lote", methods=["POST"])
@jwt_required()
def automacao_carrinho_lote():
    """
    Recebe uma LISTA de itens e o NOME do fornecedor.
    Executa o robô para adicionar esses itens ao carrinho do fornecedor.
    """
    try:
        # 1) Tratamento robusto do JSON (evita 400/415)
        raw_data = request.get_data()
        data = request.get_json(force=True, silent=True)

        if data is None:
            import json
            try:
                if raw_data:
                    data = json.loads(raw_data)
                else:
                    return jsonify({"success": False, "message": "Corpo da requisição vazio."}), 400
            except Exception as json_err:
                print(f"❌ Erro ao decodificar JSON manual: {json_err}")
                return jsonify({"success": False, "message": "JSON inválido."}), 400

        # 2) Extração dos dados
        fornecedor = (data.get("fornecedor", "") or "").strip()
        lista_itens = data.get("itens", [])

        if not fornecedor:
            return jsonify({"success": False, "message": "Campo 'fornecedor' é obrigatório."}), 400

        if not isinstance(lista_itens, list) or len(lista_itens) == 0:
            return jsonify({"success": False, "message": "Lista de itens vazia."}), 400

        # 3) Validação mínima dos itens
        itens_normalizados = []
        for idx, item in enumerate(lista_itens):
            if not isinstance(item, dict):
                return jsonify({"success": False, "message": f"Item inválido no índice {idx}."}), 400

            codigo = str(item.get("codigo", "")).strip()
            quantidade = item.get("quantidade", 1)

            try:
                quantidade = int(quantidade)
            except Exception:
                quantidade = 1

            if not codigo:
                return jsonify({"success": False, "message": f"Item sem 'codigo' no índice {idx}."}), 400

            if quantidade < 1:
                quantidade = 1

            # UF opcional
            uf = (item.get("uf") or "").strip().upper() if "uf" in item else None

            item_norm = {"codigo": codigo, "quantidade": quantidade}
            if uf:
                item_norm["uf"] = uf

            itens_normalizados.append(item_norm)

        print(f"📥 RAW DATA recebido: {raw_data}")
        print(f"🤖 Iniciando robô de compras para: {fornecedor} | {len(itens_normalizados)} itens.")

        # 4) Execução do Robô (Playwright via runner_carrinho.py)
        try:
            resultado_robo = asyncio.run(executar_automacao_carrinho(fornecedor, itens_normalizados))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            resultado_robo = loop.run_until_complete(executar_automacao_carrinho(fornecedor, itens_normalizados))

        # 5) Retorno
        if resultado_robo.get("success"):
            return jsonify({
                "success": True,
                "message": "Automação finalizada com sucesso!",
                "detalhes": resultado_robo
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Houve um erro na execução do robô.",
                "erro_robo": resultado_robo.get("error"),
                "detalhes": resultado_robo
            }), 500

    except Exception as e:
        print(f"❌ Erro CRÍTICO na rota de automação: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
