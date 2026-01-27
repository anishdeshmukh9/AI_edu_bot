import sqlite3
from pathlib import Path

DB_PATH = Path("./f4_history.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
        user_id TEXT,
        chat_id TEXT,
        role TEXT,
        content TEXT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
)
conn.commit()


def save_message(user_id: str, chat_id: str, role: str, content: str):
    cursor.execute(
        "INSERT INTO chat_messages (user_id, chat_id, role, content) VALUES (?, ?, ?, ?)",
        (user_id, chat_id, role, content),
    )
    conn.commit()


def load_history(user_id: str, chat_id: str, limit: int = 8):
    cursor.execute(
        """
        SELECT role, content FROM chat_messages
        WHERE user_id=? AND chat_id=?
        ORDER BY ts ASC
        LIMIT ?
        """,
        (user_id, chat_id, limit),
    )
    return cursor.fetchall()

def load_full_history(user_id: str, chat_id: str):
    cursor.execute(
        """
        SELECT role, content FROM chat_messages
        WHERE user_id=? AND chat_id=?
        ORDER BY ts ASC
        """,
        (user_id, chat_id),
    )
    return cursor.fetchall()
