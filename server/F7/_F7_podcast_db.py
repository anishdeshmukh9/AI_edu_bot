import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional

DB_PATH = Path("./f7_podcast_history.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Podcast history table
cursor.execute("""
CREATE TABLE IF NOT EXISTS podcast_history (
    user_id TEXT,
    chat_id TEXT,
    topic TEXT,
    audio_url TEXT,
    duration_seconds INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# Create index for better performance
cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_user_chat_podcast 
ON podcast_history(user_id, chat_id)
""")
conn.commit()


def save_podcast(user_id: str, chat_id: str, topic: str, audio_url: str, duration_seconds: int):
    """Save a podcast to the history"""
    cursor.execute(
        "INSERT INTO podcast_history (user_id, chat_id, topic, audio_url, duration_seconds) VALUES (?, ?, ?, ?, ?)",
        (user_id, chat_id, topic, audio_url, duration_seconds),
    )
    conn.commit()


def get_podcast_history(user_id: str, chat_id: str) -> List[Tuple[str, str, int, str]]:
    """Get all podcasts for a specific chat"""
    cursor.execute(
        """
        SELECT topic, audio_url, duration_seconds, created_at FROM podcast_history
        WHERE user_id=? AND chat_id=?
        ORDER BY created_at ASC
        """,
        (user_id, chat_id),
    )
    return cursor.fetchall()


def get_all_podcast_chat_ids(user_id: str) -> List[dict]:
    """Get all podcast chat IDs for a user with metadata"""
    cursor.execute(
        """
        SELECT 
            chat_id,
            COUNT(*) as podcast_count,
            MAX(created_at) as last_updated
        FROM podcast_history
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
            "podcast_count": row[1],
            "last_updated": row[2]
        }
        for row in rows
    ]


def delete_podcast_chat(user_id: str, chat_id: str) -> bool:
    """Delete all podcasts for a specific chat"""
    try:
        cursor.execute(
            "DELETE FROM podcast_history WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting podcast chat: {e}")
        return False


def podcast_chat_exists(user_id: str, chat_id: str) -> bool:
    """Check if a podcast chat exists"""
    cursor.execute(
        "SELECT 1 FROM podcast_history WHERE user_id=? AND chat_id=? LIMIT 1",
        (user_id, chat_id),
    )
    return cursor.fetchone() is not None
