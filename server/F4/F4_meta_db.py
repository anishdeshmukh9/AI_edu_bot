import sqlite3
from pathlib import Path

DB_PATH = Path("./f4_meta.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS indexed_pdfs (
        user_id TEXT,
        chat_id TEXT,
        pdf_url TEXT,
        vector_dir TEXT,
        PRIMARY KEY (user_id, chat_id, pdf_url)
    )
    """
)
conn.commit()


def is_indexed(user_id: str, chat_id: str, pdf_url: str):
    cursor.execute(
        "SELECT vector_dir FROM indexed_pdfs WHERE user_id=? AND chat_id=? AND pdf_url=?",
        (user_id, chat_id, pdf_url),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def mark_indexed(user_id: str, chat_id: str, pdf_url: str, vector_dir: str):
    cursor.execute(
        "INSERT OR REPLACE INTO indexed_pdfs VALUES (?, ?, ?, ?)",
        (user_id, chat_id, pdf_url, vector_dir),
    )
    conn.commit()