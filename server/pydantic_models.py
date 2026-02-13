# here we will define the pydantic structure of the project.. 
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field, HttpUrl, FilePath
from typing import Optional, Literal


class feature1_6(BaseModel):
    user_id: str = Field(..., description="user id is compulsory")
    chat_id: str = Field(..., description="chat id")
    message: str = Field(description="Human message for llm")
     

class pydantic_for_feature_1_chat_output(BaseModel):
    title: str = Field(..., description="Title of the answer")
    body: str = Field(..., description="body of the answer if it contains code enclose with [[CODE]] if contains formula [[FORMULA]]")
    links: list[str] = Field(default=[], description="links from search tool")
    Need_of_manim: Literal["YES", "No"] = Field(default="No", description="only yes if you think manim animation is needed.")
    manim_video_path: str = Field(default="/path/demo.mp4", description="the manim video URL from Supabase if available else return /path/demo.mp4")
    main_video_prompt: str = Field(default="", description="proper prompt for AI to generate manim animation, by mentioning all the required context (only when need of manim)")
    next_related_topic: list[str] = Field(default=[], description="related topics that student can explore any 2")
    next_questions: list[str] = Field(default=[], description="next possible related questions (any 2)")


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    user_id: str = Field(..., description="Unique user identifier")
    chat_id: str = Field(..., description="Unique chat/conversation identifier")
    message: str = Field(..., description="User's message to the AI")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[pydantic_for_feature_1_chat_output] = Field(None, description="Structured chat output")
    error: Optional[str] = Field(None, description="Error message if any")
    
    
class GetChatsRequest(BaseModel):
    user_id: str


class GetConversationRequest(BaseModel):
    user_id: str
    chat_id: str