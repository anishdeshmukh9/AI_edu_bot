import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional
import json

DB_PATH = Path("./f8_gita_counseling_history.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Gita counseling history table
cursor.execute("""
CREATE TABLE IF NOT EXISTS gita_counseling_history (
    user_id TEXT,
    chat_id TEXT,
    doubt TEXT,
    guidance TEXT,
    language TEXT,
    referenced_shlokas TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# Create index for better performance
cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_user_chat_gita 
ON gita_counseling_history(user_id, chat_id)
""")
conn.commit()


def save_counseling(
    user_id: str,
    chat_id: str,
    doubt: str,
    guidance: str,
    language: str,
    referenced_shlokas: list
):
    """Save a counseling session to the history"""
    # Convert shlokas list to JSON string
    shlokas_json = json.dumps(referenced_shlokas)
    
    cursor.execute(
        """
        INSERT INTO gita_counseling_history 
        (user_id, chat_id, doubt, guidance, language, referenced_shlokas) 
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, chat_id, doubt, guidance, language, shlokas_json),
    )
    conn.commit()


def get_gita_history(user_id: str, chat_id: str) -> List[Tuple[str, str, str, str, str]]:
    """
    Get all counseling sessions for a specific chat
    
    Returns:
        List of (doubt, guidance, language, referenced_shlokas_json, created_at)
    """
    cursor.execute(
        """
        SELECT doubt, guidance, language, referenced_shlokas, created_at 
        FROM gita_counseling_history
        WHERE user_id=? AND chat_id=?
        ORDER BY created_at ASC
        """,
        (user_id, chat_id),
    )
    return cursor.fetchall()


def get_all_gita_chat_ids(user_id: str) -> List[dict]:
    """Get all Gita counseling chat IDs for a user with metadata"""
    cursor.execute(
        """
        SELECT 
            chat_id,
            COUNT(*) as counseling_count,
            MAX(created_at) as last_updated
        FROM gita_counseling_history
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
            "counseling_count": row[1],
            "last_updated": row[2]
        }
        for row in rows
    ]


def delete_gita_chat(user_id: str, chat_id: str) -> bool:
    """Delete all counseling sessions for a specific chat"""
    try:
        cursor.execute(
            "DELETE FROM gita_counseling_history WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting Gita counseling chat: {e}")
        return False


def gita_chat_exists(user_id: str, chat_id: str) -> bool:
    """Check if a Gita counseling chat exists"""
    cursor.execute(
        "SELECT 1 FROM gita_counseling_history WHERE user_id=? AND chat_id=? LIMIT 1",
        (user_id, chat_id),
    )
    return cursor.fetchone() is not None