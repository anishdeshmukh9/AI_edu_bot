from pydantic import BaseModel, HttpUrl
from typing import List, Optional


class Feature5Input(BaseModel):
    user_id: str
    chat_id: str
    youtube_url: HttpUrl
    message: str


class Feature5Output(BaseModel):
    answer: str
    timestamps: List[str]


class MessageItem(BaseModel):
    role: str  # 'human' or 'ai'
    content: str


class VideoRagResponse(BaseModel):
    user_id: str
    chat_id: str
    messages: List[MessageItem]
    latest_answer: Feature5Output


class ChatSummary(BaseModel):
    chat_id: str
    message_count: int
    youtube_url: Optional[str] = None
    last_updated: Optional[str] = None


class GetChatsResponse(BaseModel):
    user_id: str
    chats: List[ChatSummary]


class GetChatHistoryResponse(BaseModel):
    user_id: str
    chat_id: str
    messages: List[MessageItem]


class DeleteChatResponse(BaseModel):
    success: bool
    message: str
    deleted_chat_id: str