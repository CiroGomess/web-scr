# routes/userController.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt
from configs.db import get_connection  # Agora retorna sqlite3 connection (websrc.db)

user_bp = Blueprint('user_bp', __name__)

# ========================================================
# 🔐 ROTA: REGISTRAR USUÁRIO (CREATE)
# ========================================================
@user_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email')
    senha_plana = data.get('senha')

    if not email or not senha_plana:
        return jsonify({"message": "Email e senha são obrigatórios"}), 400

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1) Verifica se usuário já existe
        cursor.execute("SELECT id FROM user_login WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({"message": "Usuário já cadastrado"}), 409

        # 2) Criptografa a senha (Hash)
        salt = bcrypt.gensalt()
        senha_hash = bcrypt.hashpw(senha_plana.encode('utf-8'), salt).decode('utf-8')

        # 3) Insere no banco (SQLite não usa RETURNING por padrão)
        cursor.execute(
            "INSERT INTO user_login (email, senha) VALUES (?, ?)",
            (email, senha_hash)
        )
        user_id = cursor.lastrowid
        conn.commit()

        return jsonify({"message": "Usuário criado com sucesso", "user_id": user_id}), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"message": "Erro no servidor", "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# ========================================================
# 🔓 ROTA: LOGIN (Gera o Token JWT)
# ========================================================
@user_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    senha_plana = data.get('senha')

    if not email or not senha_plana:
        return jsonify({"message": "Email e senha são obrigatórios"}), 400

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1) Busca usuário pelo email
        cursor.execute("SELECT id, email, senha FROM user_login WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "Email ou senha incorretos"}), 401

        # sqlite3.Row permite acessar por índice ou chave
        user_id = user[0]
        user_email = user[1]
        user_senha_hash = user[2]

        # 2) Verifica senha
        if bcrypt.checkpw(senha_plana.encode('utf-8'), user_senha_hash.encode('utf-8')):
            access_token = create_access_token(identity=str(user_id))
            return jsonify({
                "message": "Login realizado com sucesso",
                "token": access_token,
                "user": {"id": user_id, "email": user_email}
            }), 200

        return jsonify({"message": "Email ou senha incorretos"}), 401

    except Exception as e:
        return jsonify({"message": "Erro no servidor", "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# ========================================================
# 🛡️ ROTA PROTEGIDA: LISTAR USUÁRIOS (READ)
# ========================================================
@user_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    conn = None
    try:
        _current_user_id = get_jwt_identity()

        conn = get_connection()
        cursor = conn.cursor()

        # Se sua tabela NÃO tiver created_at, remova do SELECT
        cursor.execute("SELECT id, email, created_at FROM user_login")
        rows = cursor.fetchall()

        lista_users = []
        for r in rows:
            lista_users.append({
                "id": r[0],
                "email": r[1],
                "created_at": r[2]
            })

        return jsonify(lista_users), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# ========================================================
# 🛡️ ROTA PROTEGIDA: DELETAR USUÁRIO (DELETE)
# ========================================================
@user_bp.route('/users/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_user(id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM user_login WHERE id = ?", (id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"message": "Usuário não encontrado"}), 404

        return jsonify({"message": "Usuário deletado com sucesso"}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
