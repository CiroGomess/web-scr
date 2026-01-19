import sqlite3
import os

# Nome do arquivo do banco de dados
DB_FILENAME = 'websrc.db'
SQL_SCRIPT_FILENAME = 'websrc.sql'

def create_database():
    # Verifica se o arquivo SQL existe
    if not os.path.exists(SQL_SCRIPT_FILENAME):
        print(f"Erro: O arquivo '{SQL_SCRIPT_FILENAME}' não foi encontrado.")
        return

    # Remove o banco antigo se quiser recriar do zero (opcional, cuidado!)
    # if os.path.exists(DB_FILENAME):
    #     os.remove(DB_FILENAME)
    #     print(f"Banco antigo '{DB_FILENAME}' removido.")

    try:
        # Conecta ao SQLite (ele cria o arquivo se não existir)
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()

        print(f"Conectado ao banco '{DB_FILENAME}'.")

        # Lê o conteúdo do arquivo .sql
        with open(SQL_SCRIPT_FILENAME, 'r', encoding='utf-8') as sql_file:
            sql_script = sql_file.read()

        # Executa o script SQL
        cursor.executescript(sql_script)
        conn.commit()
        
        print("Tabelas criadas com sucesso!")

    except sqlite3.Error as e:
        print(f"Erro ao criar o banco de dados: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_database()