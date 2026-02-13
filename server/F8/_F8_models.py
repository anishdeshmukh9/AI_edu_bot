from pydantic import BaseModel
from typing import List, Optional


class Feature8Input(BaseModel):
    """Input model for Bhagavad Gita counseling"""
    user_id: str
    chat_id: str
    doubt: str  # Life problem/doubt from the student
    preferred_language: str  # "english" or "hindi"


class GitaShloka(BaseModel):
    """Model for a single shloka with its meaning"""
    chapter: int
    verse: int
    sanskrit_text: str
    transliteration: str
    meaning_english: str
    meaning_hindi: str


class Feature8Output(BaseModel):
    """Output model for Krishna's guidance"""
    guidance: str  # Krishna's complete guidance in preferred language
    referenced_shlokas: List[GitaShloka]  # Relevant shlokas that support the guidance
    life_examples: List[str]  # Real-world examples mentioned
    key_teachings: List[str]  # Key takeaways from the guidance


class GitaCounselingItem(BaseModel):
    """Single counseling entry in chat history"""
    doubt: str
    guidance: str
    language: str
    referenced_shlokas: List[GitaShloka]
    created_at: str


class GitaChatSummary(BaseModel):
    """Summary of a Gita counseling chat session"""
    chat_id: str
    counseling_count: int
    last_updated: Optional[str] = None


class GetGitaChatsResponse(BaseModel):
    """Response for getting all Gita counseling chats"""
    user_id: str
    chats: List[GitaChatSummary]


class GetGitaHistoryResponse(BaseModel):
    """Response for getting Gita counseling chat history"""
    user_id: str
    chat_id: str
    counselings: List[GitaCounselingItem]


class DeleteGitaChatResponse(BaseModel):
    """Response for deleting a Gita counseling chat"""
    success: bool
    message: str
    deleted_chat_id: str
    
class Feature8Output(BaseModel):
    guidance: str
    referenced_shlokas: List[GitaShloka]
    life_examples: List[str]
    key_teachings: List[str]
    audio_url: str