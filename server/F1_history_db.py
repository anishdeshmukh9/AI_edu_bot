"""
Feature 1 History Database Module
Handles persistent storage and retrieval of chat conversations
"""

import sqlite3
from typing import List, Tuple
import os
from pathlib import Path

# Database path
DB_PATH = "feature1_history.db"


def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, chat_id, id)
        )
    """)
    
    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_chat 
        ON conversations(user_id, chat_id)
    """)
    
    conn.commit()
    conn.close()


def save_message(user_id: str, chat_id: str, role: str, content: str):
    """
    Save a single message to the database
    
    Args:
        user_id: User identifier
        chat_id: Chat identifier
        role: Message role ('user' or 'assistant')
        content: Message content
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO conversations (user_id, chat_id, role, content)
        VALUES (?, ?, ?, ?)
    """, (user_id, chat_id, role, content))
    
    conn.commit()
    conn.close()


def load_full_history(user_id: str, chat_id: str) -> List[Tuple[str, str]]:
    """
    Load complete conversation history for a specific chat
    
    Args:
        user_id: User identifier
        chat_id: Chat identifier
        
    Returns:
        List of tuples [(role, content), ...] in chronological order
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT role, content 
        FROM conversations 
        WHERE user_id = ? AND chat_id = ?
        ORDER BY id ASC
    """, (user_id, chat_id))
    
    history = cursor.fetchall()
    conn.close()
    
    return history

def get_all_chat_ids(user_id: str) -> List[str]:
    """
    Get all chat IDs for a user ordered by most recent activity
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT chat_id
        FROM conversations
        WHERE user_id = ?
        GROUP BY chat_id
        ORDER BY MAX(timestamp) DESC
    """, (user_id,))
    
    chat_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return chat_ids


def delete_chat(user_id: str, chat_id: str):
    """
    Delete a specific chat conversation
    
    Args:
        user_id: User identifier
        chat_id: Chat identifier
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM conversations 
        WHERE user_id = ? AND chat_id = ?
    """, (user_id, chat_id))
    
    conn.commit()
    conn.close()


def get_all_users() -> List[str]:
    """
    Get all unique user IDs in the database
    
    Returns:
        List of user IDs
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT user_id 
        FROM conversations
    """)
    
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return user_ids


def update_last_assistant_message(user_id: str, chat_id: str, content: str):
    """
    Update the most recent assistant message for a chat
    Used when updating manim video URLs after generation
    
    Args:
        user_id: User identifier
        chat_id: Chat identifier
        content: New content to replace the last assistant message
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get the ID of the last assistant message
    cursor.execute("""
        SELECT id FROM conversations 
        WHERE user_id = ? AND chat_id = ? AND role = 'assistant'
        ORDER BY id DESC
        LIMIT 1
    """, (user_id, chat_id))
    
    result = cursor.fetchone()
    
    if result:
        message_id = result[0]
        cursor.execute("""
            UPDATE conversations 
            SET content = ?
            WHERE id = ?
        """, (content, message_id))
        
        conn.commit()
    
    conn.close()


# Initialize database on module import
init_db()