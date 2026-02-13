from pydantic import BaseModel, Field, HttpUrl
from typing import List


class Feature4Input(BaseModel):
    user_id: str = Field(...)
    chat_id: str = Field(...)
    pdf_url: HttpUrl = Field(..., description="supabase url ")
    message: str = Field(...)


class Feature4Output(BaseModel):
    title: str
    body: str
    pages: List[int]
    youtube_links: List[HttpUrl]
    next_related_topic: List[str]
    next_questions: List[str]