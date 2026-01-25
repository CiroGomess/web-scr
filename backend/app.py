from flask import Flask, request, jsonify
import os
import asyncio
import threading
import sys
import io
import uuid
from datetime import datetime, timedelta
from flask_cors import CORS
import glob
# ===================== IMPORTAÇÕES DO FLASK JWT ===================== #
from flask_jwt_extended import JWTManager, jwt_required
from controllers.routes.userController import user_bp
# ====================================================================
from services.db_saver import limpar_banco_processamento, atualizar_ultimo_processamento

# Importação do Runner de Processamento de Dados (Extração)
from runner import main

# 🟢 Runner do Carrinho de Compras
from runner_carrinho import executar_automacao_carrinho

# Controllers
from controllers.dadosController import carregar_lote_mais_recente
from controllers.routes.comparandoProd import comparar_precos_entre_fornecedores
from configs.db import get_connection
from zoneinfo import ZoneInfo

from utils.limpar_dados_temp import limpar_pasta_temp

# ====================================================================
# SISTEMA DE LOGS EM TEMPO REAL
# ====================================================================
LOG_FILE_PATH = "/tmp/web-scr-processing.log"
LOG_DIR = "data/logs"  # Diretório para salvar logs permanentes (seguindo padrão data/hist_dados)
PROCESSING_START_TIME = None
PROCESSING_SESSION_ID = None  # Identificador único para cada processamento
PROCESSING_METADATA = {
    "total_produtos": 0,
    "total_fornecedores": 15,  # Quantidade fixa de fornecedores
    "fornecedores_concluidos": 0,
    "itens_processados": 0,
    "logs": []
}

class LogCapture:
    """Captura logs do processamento em tempo real"""
    def __init__(self, log_file_path, log_dir=None):
        self.log_file_path = log_file_path
        self.log_dir = log_dir
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.log_buffer = []
        self.max_logs = 2000  # Aumentado para manter mais histórico de logs
        self.permanent_log_path = None  # Caminho do arquivo permanente
        
        # Cria diretório de logs se não existir
        if self.log_dir:
            try:
                os.makedirs(self.log_dir, exist_ok=True)
            except Exception:
                pass
        
    def write(self, text):
        """Intercepta prints e salva em arquivo e buffer"""
        if text.strip():  # Ignora linhas vazias
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {text.rstrip()}"
            
            # Salva no arquivo
            try:
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
            except Exception:
                pass
            
            # Mantém em buffer (últimos N logs)
            self.log_buffer.append(log_entry)
            if len(self.log_buffer) > self.max_logs:
                self.log_buffer.pop(0)
            
            # Também escreve no stdout original para aparecer nos logs do systemd
            self.original_stdout.write(text)
            self.original_stdout.flush()
    
    def flush(self):
        self.original_stdout.flush()
    
    def start(self):
        """Inicia a captura de logs"""
        sys.stdout = self
        sys.stderr = self
    
    def stop(self):
        """Para a captura de logs"""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
    
    def get_logs(self, last_n=500):
        """Retorna os últimos N logs (aumentado para manter mais histórico)"""
        return self.log_buffer[-last_n:] if self.log_buffer else []
    
    def get_all_logs(self):
        """Retorna todos os logs do buffer"""
        return self.log_buffer.copy() if self.log_buffer else []
    
    def clear(self):
        """Limpa os logs"""
        self.log_buffer = []
        self.permanent_log_path = None
        try:
            if os.path.exists(self.log_file_path):
                os.remove(self.log_file_path)
        except Exception:
            pass
    
    def create_permanent_log(self, session_id=None):
        """Cria um arquivo permanente para este processamento"""
        if not self.log_dir:
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            session_part = f"_{session_id[:8]}" if session_id else ""
            filename = f"processamento_{timestamp}{session_part}.log"
            self.permanent_log_path = os.path.join(self.log_dir, filename)
            
            # Cria o arquivo vazio
            with open(self.permanent_log_path, "w", encoding="utf-8") as f:
                f.write(f"=== LOG DE PROCESSAMENTO ===\n")
                f.write(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if session_id:
                    f.write(f"Session ID: {session_id}\n")
                f.write(f"{'='*50}\n\n")
            
            return self.permanent_log_path
        except Exception as e:
            print(f"⚠️ Erro ao criar arquivo de log permanente: {e}")
            return None
    
    def save_to_permanent(self):
        """Salva todos os logs do buffer no arquivo permanente"""
        if not self.permanent_log_path or not self.log_buffer:
            return
        
        try:
            with open(self.permanent_log_path, "a", encoding="utf-8") as f:
                for log_entry in self.log_buffer:
                    f.write(log_entry + "\n")
                f.write(f"\n{'='*50}\n")
                f.write(f"Total de linhas de log: {len(self.log_buffer)}\n")
                f.write(f"Fim do processamento: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        except Exception as e:
            print(f"⚠️ Erro ao salvar log permanente: {e}")

log_capture = LogCapture(LOG_FILE_PATH, LOG_DIR)



app = Flask(__name__, template_folder="views")

# ===================== CONFIGURAÇÃO DO JWT ========================== #
app.config["JWT_SECRET_KEY"] = "R4Z5ce3aeFWo9NTXIEiRHbx32aOuSPPz"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=240)

jwt = JWTManager(app)
# ====================================================================

# ===================== PRODUÇÃO ======================= #

# CORS(
#     app,
#     resources={r"/api/*": {
#         "origins": [
#             "http://206.0.29.133:3000",
#             "http://206.0.29.133",
#             "https://apvieira.uniqcode.com.br"
#         ]
#     }},
#     supports_credentials=False,
#     allow_headers=["Content-Type", "Authorization"],
#     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
# )

# ===================== LOCALMENTE ======================= #
CORS(app, resources={r"/*": {"origins": "*"}})

# ===================== REGISTRO DE BLUEPRINTS ======================= #
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
# Processamento em background para evitar timeout do Cloudflare (524)
# ====================================================================
def processar_em_background():
    """Executa o processamento em uma thread separada"""
    global PROCESSING_START_TIME, PROCESSING_METADATA, PROCESSING_SESSION_ID
    
    try:
        # Gera novo ID de sessão para este processamento
        PROCESSING_SESSION_ID = str(uuid.uuid4())
        
        # Inicia captura de logs (limpa logs anteriores)
        log_capture.clear()
        
        # Cria arquivo permanente para este processamento
        log_capture.create_permanent_log(PROCESSING_SESSION_ID)
        
        log_capture.start()
        PROCESSING_START_TIME = datetime.now()
        PROCESSING_METADATA = {
            "total_produtos": 0,
            "total_fornecedores": 15,
            "fornecedores_concluidos": 0,
            "itens_processados": 0,
            "logs": []
        }
        
        print("🔄 [BACKGROUND] Iniciando processamento em background...")
        
        # ✅ Limpa o banco antes de iniciar um novo processamento
        limpeza = limpar_banco_processamento()
        if not limpeza.get("success"):
            print(f"❌ [BACKGROUND] Erro ao limpar banco: {limpeza.get('error')}")
            # Salva logs mesmo em caso de erro
            log_capture.save_to_permanent()
            log_capture.stop()
            return

        print("🔄 [BACKGROUND] Executando main()...")
        try:
            result = asyncio.run(main())
            
            # Atualiza metadata com informações do resultado
            if result and isinstance(result, dict):
                PROCESSING_METADATA["itens_processados"] = result.get("total_processado", 0)
                if "relatorio" in result:
                    PROCESSING_METADATA["fornecedores_concluidos"] = result["relatorio"].get("logins_ok", 0)
                    
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(main())
            loop.close()
            
            if result and isinstance(result, dict):
                PROCESSING_METADATA["itens_processados"] = result.get("total_processado", 0)
                if "relatorio" in result:
                    PROCESSING_METADATA["fornecedores_concluidos"] = result["relatorio"].get("logins_ok", 0)

        print(f"✅ [BACKGROUND] Processamento concluído. Total: {result.get('total_processado', 0) if result else 0}")

        # ✅ Atualiza o controle de último processamento ao finalizar (OBRIGATÓRIO)
        ok_ctrl = atualizar_ultimo_processamento(datetime.now(ZoneInfo("America/Fortaleza")))
        if not ok_ctrl:
            print("⚠️ [BACKGROUND] Processou, mas falhou ao atualizar controle_ultimo_processamento.")
        else:
            print("✅ [BACKGROUND] Controle de último processamento atualizado.")

        # ✅ Limpa arquivos temporários (data/temp)
        limpeza_temp = limpar_pasta_temp("data/temp")
        if not limpeza_temp.get("success"):
            print(f"⚠️ [BACKGROUND] Falha ao limpar data/temp: {limpeza_temp}")
        else:
            print("✅ [BACKGROUND] Arquivos temporários limpos.")

        print("🎉 [BACKGROUND] Processamento finalizado com sucesso!")
        
        # Salva logs no arquivo permanente antes de parar
        log_capture.save_to_permanent()
        
        # Para captura de logs
        log_capture.stop()

    except Exception as e:
        print(f"❌ [BACKGROUND] Erro crítico no processamento: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Salva logs mesmo em caso de erro
        log_capture.save_to_permanent()
        
        log_capture.stop()


@app.route("/processar/logs", methods=["GET"])
@jwt_required()
def logs_processamento():
    """
    Retorna os logs do processamento em tempo real e informações de progresso
    """
    global PROCESSING_SESSION_ID
    
    try:
        # Obtém TODOS os logs do buffer (sem limite para manter histórico completo)
        logs = log_capture.get_all_logs()
        
        # Retorna também o session_id atual para o frontend validar
        current_session_id = PROCESSING_SESSION_ID
        
        # Calcula progresso baseado nos logs
        fornecedores_concluidos = 0
        itens_processados = 0
        total_produtos = 0
        
        # Extrai informações dos logs
        for log in logs:
            # Conta fornecedores concluídos
            if "✅ Login" in log and "realizado" in log:
                fornecedores_concluidos += 1
            # Conta itens processados
            if "📦 [" in log and "] " in log:
                try:
                    # Extrai número do item processado (ex: [1/173])
                    parts = log.split("📦 [")[1].split("]")[0]
                    if "/" in parts:
                        current, total = parts.split("/")
                        itens_processados = max(itens_processados, int(current))
                        total_produtos = max(total_produtos, int(total))
                except Exception:
                    pass
            # Conta itens salvos
            if "📥" in log and "itens processados" in log:
                try:
                    num = int(log.split("📥")[1].split("itens")[0].strip())
                    itens_processados = max(itens_processados, num)
                except Exception:
                    pass
        
        # Atualiza metadata
        PROCESSING_METADATA["fornecedores_concluidos"] = fornecedores_concluidos
        PROCESSING_METADATA["itens_processados"] = itens_processados
        if total_produtos > 0:
            PROCESSING_METADATA["total_produtos"] = total_produtos
        
        # Calcula estimativa de tempo
        tempo_decorrido = 0
        tempo_estimado_restante = 0
        
        if PROCESSING_START_TIME:
            tempo_decorrido = (datetime.now() - PROCESSING_START_TIME).total_seconds()
            
            # Estima tempo restante baseado no progresso
            if total_produtos > 0 and itens_processados > 0:
                progresso = itens_processados / total_produtos
                if progresso > 0:
                    tempo_total_estimado = tempo_decorrido / progresso
                    tempo_estimado_restante = max(0, tempo_total_estimado - tempo_decorrido)
            elif fornecedores_concluidos > 0:
                # Estima baseado em fornecedores
                progresso = fornecedores_concluidos / PROCESSING_METADATA["total_fornecedores"]
                if progresso > 0:
                    tempo_total_estimado = tempo_decorrido / progresso
                    tempo_estimado_restante = max(0, tempo_total_estimado - tempo_decorrido)
        
        return jsonify({
            "logs": logs,
            "session_id": current_session_id,  # ID da sessão atual
            "progresso": {
                "fornecedores_concluidos": fornecedores_concluidos,
                "total_fornecedores": PROCESSING_METADATA["total_fornecedores"],
                "itens_processados": itens_processados,
                "total_produtos": total_produtos if total_produtos > 0 else PROCESSING_METADATA["total_produtos"],
                "tempo_decorrido_segundos": int(tempo_decorrido),
                "tempo_estimado_restante_segundos": int(tempo_estimado_restante)
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "logs": [],
            "error": str(e)
        }), 500


@app.route("/processar/status", methods=["GET"])
@jwt_required()
def status_processamento():
    """
    Verifica o status do processamento em background.
    Retorna 'processing' se ainda está processando (data = 1970-01-01)
    Retorna 'completed' se terminou (data > 1970-01-01)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ultima_data_processamento 
            FROM controle_ultimo_processamento 
            WHERE id = 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return jsonify({
                "status": "unknown",
                "message": "Status do processamento não disponível"
            }), 200
        
        data_str = row[0]
        
        # Se a data é 1970-01-01, ainda está processando
        if "1970-01-01" in data_str or data_str.startswith("1970"):
            return jsonify({
                "status": "processing",
                "message": "Processamento em andamento..."
            }), 200
        
        # Se a data é mais recente, processamento concluído
        return jsonify({
            "status": "completed",
            "message": "Processamento concluído!",
            "ultima_data_processamento": data_str
        }), 200
        
    except Exception as e:
        print(f"❌ Erro ao verificar status: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route("/processar", methods=["POST"])
@jwt_required()
def processar():
    """
    Inicia o processamento em background e retorna imediatamente.
    Isso evita o timeout do Cloudflare (524) que ocorre após 100 segundos.
    """
    global PROCESSING_SESSION_ID
    
    try:
        # Gera um novo ID de sessão ANTES de iniciar o processamento
        # Isso permite que o frontend identifique quando é um novo processamento
        new_session_id = str(uuid.uuid4())
        
        # Inicia o processamento em uma thread separada
        thread = threading.Thread(target=processar_em_background, daemon=True)
        thread.start()
        
        # Atualiza o session_id global (será atualizado novamente na thread, mas isso garante que está disponível imediatamente)
        PROCESSING_SESSION_ID = new_session_id
        
        print("✅ Processamento iniciado em background. Retornando resposta imediata...")
        
        return jsonify({
            "success": True,
            "message": "Processamento iniciado em background.",
            "status": "processing",
            "session_id": new_session_id,  # ID único para este processamento
            "note": "O processamento está sendo executado em background. O overlay permanecerá aberto até a conclusão."
        }), 202  # 202 Accepted - requisição aceita mas ainda processando

    except Exception as e:
        print(f"❌ Erro ao iniciar processamento: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Erro ao iniciar processamento: {str(e)}"
        }), 500


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
