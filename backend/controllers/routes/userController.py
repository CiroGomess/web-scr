from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt
import psycopg2
from configs.db import get_connection  # Assumindo que sua conexão vem daqui

# Cria o Blueprint
user_bp = Blueprint('user_bp', __name__)

# ========================================================
# 🔐 ROTA: REGISTRAR USUÁRIO (CREATE)
# ========================================================
@user_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    senha_plana = data.get('senha')

    if not email or not senha_plana:
        return jsonify({"message": "Email e senha são obrigatórios"}), 400

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Verifica se usuário já existe
        cursor.execute("SELECT id FROM user_login WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"message": "Usuário já cadastrado"}), 409

        # 2. Criptografa a senha (Hash)
        # Gera o salt e o hash
        salt = bcrypt.gensalt()
        senha_hash = bcrypt.hashpw(senha_plana.encode('utf-8'), salt).decode('utf-8')

        # 3. Insere no banco
        cursor.execute(
            "INSERT INTO user_login (email, senha) VALUES (%s, %s) RETURNING id",
            (email, senha_hash)
        )
        user_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({"message": "Usuário criado com sucesso", "user_id": user_id}), 201

    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"message": "Erro no servidor", "error": str(e)}), 500
    finally:
        if conn: conn.close()


# ========================================================
# 🔓 ROTA: LOGIN (Gera o Token JWT)
# ========================================================
@user_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    senha_plana = data.get('senha')

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Busca usuário pelo email
        cursor.execute("SELECT id, email, senha FROM user_login WHERE email = %s", (email,))
        user = cursor.fetchone() # Retorna (id, email, senha_hash)

        if not user:
            return jsonify({"message": "Email ou senha incorretos"}), 401

        user_id, user_email, user_senha_hash = user

        # 2. Verifica se a senha bate com o hash
        if bcrypt.checkpw(senha_plana.encode('utf-8'), user_senha_hash.encode('utf-8')):
            
            # 3. Gera o Token JWT
            # identity pode ser o ID ou o Email (o que você quiser recuperar depois)
            access_token = create_access_token(identity=str(user_id))
            
            return jsonify({
                "message": "Login realizado com sucesso",
                "token": access_token,
                "user": {"id": user_id, "email": user_email}
            }), 200
        else:
            return jsonify({"message": "Email ou senha incorretos"}), 401

    except Exception as e:
        return jsonify({"message": "Erro no servidor", "error": str(e)}), 500
    finally:
        if conn: conn.close()


# ========================================================
# 🛡️ ROTA PROTEGIDA: LISTAR USUÁRIOS (READ)
# ========================================================
@user_bp.route('/users', methods=['GET'])
@jwt_required() # <--- Exige Token Válido
def get_users():
    conn = None
    try:
        # Pega o ID do usuário que está fazendo a requisição (opcional, para logs)
        current_user_id = get_jwt_identity()

        conn = get_connection()
        cursor = conn.cursor()

        # Traz id e email (nunca traga a senha, mesmo hash)
        cursor.execute("SELECT id, email, created_at FROM user_login")
        users = cursor.fetchall()

        lista_users = []
        for u in users:
            lista_users.append({
                "id": u[0],
                "email": u[1],
                "created_at": u[2]
            })

        return jsonify(lista_users), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


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

        cursor.execute("DELETE FROM user_login WHERE id = %s", (id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"message": "Usuário não encontrado"}), 404

        return jsonify({"message": "Usuário deletado com sucesso"}), 200

    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()