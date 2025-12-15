import os
import psycopg2
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SSLMODE = os.getenv("DB_SSLMODE", "disable")

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode=DB_SSLMODE,
        options="-c client_encoding=UTF8"
    )


if __name__ == "__main__":
    try:
        conn = get_connection()
        print("Conexao com PostgreSQL realizada com sucesso")

        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        print(cursor.fetchone())

        cursor.close()
        conn.close()

    except Exception as e:
        print("Erro ao conectar no PostgreSQL")
        print(str(e).encode("utf-8", errors="ignore").decode("utf-8"))
