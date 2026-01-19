# configs/db.py
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.getenv("SQLITE_PATH", "./configs/websrc.db")

def get_connection():
    conn = sqlite3.connect(SQLITE_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Boas práticas
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")

    return conn


if __name__ == "__main__":
    try:
        conn = get_connection()
        print("Conexao com SQLite realizada com sucesso")
        cur = conn.cursor()
        cur.execute("SELECT sqlite_version();")
        print(cur.fetchone()[0])
        conn.close()
    except Exception as e:
        print("Erro ao conectar no SQLite")
        print(str(e))
