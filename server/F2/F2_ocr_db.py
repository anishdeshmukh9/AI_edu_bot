import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

DB_PATH = Path("./f2_ocr.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# OCR extracted text storage
cursor.execute("""
CREATE TABLE IF NOT EXISTS ocr_extractions (
    user_id TEXT,
    chat_id TEXT,
    image_url TEXT,
    extracted_text TEXT,
    extraction_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, chat_id, image_url)
)
""")
conn.commit()

# Create index for better performance
cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_user_chat_ocr 
ON ocr_extractions(user_id, chat_id)
""")
conn.commit()


def save_ocr_extraction(user_id: str, chat_id: str, image_url: str, extracted_text: str):
    """Save OCR extracted text for an image (avoids re-extraction)"""
    cursor.execute(
        """
        INSERT OR REPLACE INTO ocr_extractions 
        (user_id, chat_id, image_url, extracted_text, extraction_timestamp) 
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, chat_id, image_url, extracted_text, datetime.now().isoformat()),
    )
    conn.commit()


def get_ocr_extraction(user_id: str, chat_id: str, image_url: str) -> Optional[str]:
    """Get OCR extracted text for an image if it exists"""
    cursor.execute(
        """
        SELECT extracted_text FROM ocr_extractions
        WHERE user_id=? AND chat_id=? AND image_url=?
        """,
        (user_id, chat_id, image_url),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def get_all_ocr_extractions(user_id: str, chat_id: str) -> List[Dict[str, str]]:
    """Get all OCR extractions for a chat session"""
    cursor.execute(
        """
        SELECT image_url, extracted_text, extraction_timestamp 
        FROM ocr_extractions
        WHERE user_id=? AND chat_id=?
        ORDER BY extraction_timestamp ASC
        """,
        (user_id, chat_id),
    )
    
    rows = cursor.fetchall()
    return [
        {
            "image_url": row[0],
            "extracted_text": row[1],
            "extraction_timestamp": row[2]
        }
        for row in rows
    ]


def delete_chat_ocr(user_id: str, chat_id: str) -> bool:
    """Delete all OCR extractions for a specific chat"""
    try:
        cursor.execute(
            "DELETE FROM ocr_extractions WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting chat OCR: {e}")
        return False


def image_exists_in_chat(user_id: str, chat_id: str, image_url: str) -> bool:
    """Check if an image has already been processed in this chat"""
    cursor.execute(
        "SELECT 1 FROM ocr_extractions WHERE user_id=? AND chat_id=? AND image_url=? LIMIT 1",
        (user_id, chat_id, image_url),
    )
    return cursor.fetchone() is not None