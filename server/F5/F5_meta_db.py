import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path("./f5_meta.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS indexed_videos (
    user_id TEXT,
    chat_id TEXT,
    youtube_url TEXT,
    faiss_dir TEXT,
    PRIMARY KEY (user_id, chat_id, youtube_url)
)
""")
conn.commit()


def get_index(user_id: str, chat_id: str, url: str) -> Optional[str]:
    """Get FAISS directory for a specific video"""
    cursor.execute(
        "SELECT faiss_dir FROM indexed_videos WHERE user_id=? AND chat_id=? AND youtube_url=?",
        (user_id, chat_id, url),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def save_index(user_id: str, chat_id: str, url: str, faiss_dir: str):
    """Save FAISS directory for a video"""
    cursor.execute(
        "INSERT OR REPLACE INTO indexed_videos VALUES (?, ?, ?, ?)",
        (user_id, chat_id, url, faiss_dir),
    )
    conn.commit()


def get_youtube_url_for_chat(user_id: str, chat_id: str) -> Optional[str]:
    """Get YouTube URL associated with a chat"""
    cursor.execute(
        "SELECT youtube_url FROM indexed_videos WHERE user_id=? AND chat_id=? LIMIT 1",
        (user_id, chat_id),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def delete_chat_index(user_id: str, chat_id: str) -> bool:
    """Delete all indexed videos for a specific chat"""
    try:
        cursor.execute(
            "DELETE FROM indexed_videos WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting chat index: {e}")
        return False