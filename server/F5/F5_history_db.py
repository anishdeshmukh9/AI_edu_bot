import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional

DB_PATH = Path("./f5_history.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_messages (
    user_id TEXT,
    chat_id TEXT,
    role TEXT,
    content TEXT,
    ts DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# Create index for better performance
cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_user_chat 
ON chat_messages(user_id, chat_id)
""")
conn.commit()


def save_message(user_id: str, chat_id: str, role: str, content: str):
    """Save a message to the chat history"""
    cursor.execute(
        "INSERT INTO chat_messages (user_id, chat_id, role, content) VALUES (?, ?, ?, ?)",
        (user_id, chat_id, role, content),
    )
    conn.commit()


def load_history(user_id: str, chat_id: str, limit: int = 10) -> List[Tuple[str, str]]:
    """Load recent chat history (for context in RAG)"""
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


def load_full_history(user_id: str, chat_id: str) -> List[Tuple[str, str]]:
    """Load complete chat history for a specific chat"""
    cursor.execute(
        """
        SELECT role, content FROM chat_messages
        WHERE user_id=? AND chat_id=?
        ORDER BY ts ASC
        """,
        (user_id, chat_id),
    )
    return cursor.fetchall()


def get_all_chat_ids(user_id: str) -> List[dict]:
    """Get all chat IDs for a user with message count and metadata"""
    cursor.execute(
        """
        SELECT 
            chat_id,
            COUNT(*) as message_count,
            MAX(ts) as last_updated
        FROM chat_messages
        WHERE user_id=?
        GROUP BY chat_id
        ORDER BY last_updated DESC
        """,
        (user_id,),
    )
    
    rows = cursor.fetchall()
    return [
        {
            "chat_id": row[0],
            "message_count": row[1],
            "last_updated": row[2]
        }
        for row in rows
    ]


def delete_chat(user_id: str, chat_id: str) -> bool:
    """Delete all messages for a specific chat"""
    try:
        cursor.execute(
            "DELETE FROM chat_messages WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting chat: {e}")
        return False


def chat_exists(user_id: str, chat_id: str) -> bool:
    """Check if a chat exists"""
    cursor.execute(
        "SELECT 1 FROM chat_messages WHERE user_id=? AND chat_id=? LIMIT 1",
        (user_id, chat_id),
    )
    return cursor.fetchone() is not None