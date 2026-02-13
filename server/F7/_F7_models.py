from pydantic import BaseModel
from typing import List, Optional


class Feature7Input(BaseModel):
    """Input model for podcast generation"""
    user_id: str
    chat_id: str
    topic: str  # Topic for the podcast


class Feature7Output(BaseModel):
    """Output model for podcast generation"""
    audio_url: str  # Supabase audio URL
    duration_seconds: int  # Approximate duration
    topic: str


class PodcastMessageItem(BaseModel):
    """Single podcast entry in chat history"""
    topic: str
    audio_url: str
    duration_seconds: int
    created_at: str


class PodcastChatSummary(BaseModel):
    """Summary of a podcast chat session"""
    chat_id: str
    podcast_count: int
    last_updated: Optional[str] = None


class GetPodcastChatsResponse(BaseModel):
    """Response for getting all podcast chats"""
    user_id: str
    chats: List[PodcastChatSummary]


class GetPodcastHistoryResponse(BaseModel):
    """Response for getting podcast chat history"""
    user_id: str
    chat_id: str
    podcasts: List[PodcastMessageItem]


class DeletePodcastChatResponse(BaseModel):
    """Response for deleting a podcast chat"""
    success: bool
    message: str
    deleted_chat_id: str
