from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict


class Feature2Input(BaseModel):
    """Input model for OCR-based doubt solving"""
    user_id: str
    chat_id: str
    image_url: HttpUrl  # Supabase image URL
    message: str  # Student's doubt/question


class ImageMetadata(BaseModel):
    """Metadata for extracted OCR text from an image"""
    image_url: str
    extracted_text: str
    extraction_timestamp: str


class Feature2Output(BaseModel):
    """Output model for OCR doubt solver"""
    answer: str
    referenced_images: List[str]  # List of Supabase URLs used for this answer


class MessageItem(BaseModel):
    """Single message in chat history"""
    role: str  # 'human' or 'ai'
    content: str
    referenced_images: Optional[List[str]] = []  # Images referenced in this message


class OcrDolubSolverResponse(BaseModel):
    """Complete response with chat history"""
    user_id: str
    chat_id: str
    messages: List[MessageItem]
    latest_answer: Feature2Output


class ChatSummary(BaseModel):
    """Summary of a chat session"""
    chat_id: str
    message_count: int
    image_count: int  # Number of unique images in this chat
    last_updated: Optional[str] = None


class GetChatsResponse(BaseModel):
    """Response for getting all chats"""
    user_id: str
    chats: List[ChatSummary]


class GetChatHistoryResponse(BaseModel):
    """Response for getting chat history"""
    user_id: str
    chat_id: str
    messages: List[MessageItem]
    images: List[ImageMetadata]  # All images in this chat


class DeleteChatResponse(BaseModel):
    """Response for deleting a chat"""
    success: bool
    message: str
    deleted_chat_id: str