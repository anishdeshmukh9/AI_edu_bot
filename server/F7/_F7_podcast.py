"""
Feature 7: Podcast Generation API

This module provides endpoints for generating educational podcasts on any topic.
Unlike Feature 2 (OCR Chat), this feature generates audio-only responses.

Endpoints:
- POST /feature7/generate - Generate podcast for a topic
- GET /feature7/chats/{user_id} - Get all podcast chat IDs
- GET /feature7/history/{user_id}/{chat_id} - Get podcast history for a chat
- DELETE /feature7/chat/{user_id}/{chat_id} - Delete a podcast chat
"""

from fastapi import APIRouter, HTTPException
from typing import List
import logging
import os

# Direct imports without using package structure
import importlib.util

# Get the directory where this file is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Import models
spec = importlib.util.spec_from_file_location("F7_models", os.path.join(current_dir, "F7_models.py"))
F7_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F7_models)
Feature7Input = F7_models.Feature7Input
Feature7Output = F7_models.Feature7Output
PodcastMessageItem = F7_models.PodcastMessageItem
GetPodcastChatsResponse = F7_models.GetPodcastChatsResponse
GetPodcastHistoryResponse = F7_models.GetPodcastHistoryResponse
DeletePodcastChatResponse = F7_models.DeletePodcastChatResponse
PodcastChatSummary = F7_models.PodcastChatSummary

# Import database functions
spec = importlib.util.spec_from_file_location("F7_podcast_db", os.path.join(current_dir, "F7_podcast_db.py"))
F7_podcast_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F7_podcast_db)
get_podcast_history = F7_podcast_db.get_podcast_history
get_all_podcast_chat_ids = F7_podcast_db.get_all_podcast_chat_ids
delete_podcast_chat = F7_podcast_db.delete_podcast_chat
podcast_chat_exists = F7_podcast_db.podcast_chat_exists

# Import podcast generator graph
spec = importlib.util.spec_from_file_location("F7_chatnode", os.path.join(current_dir, "F7_chatnode.py"))
F7_chatnode = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F7_chatnode)
podcast_generator_graph = F7_chatnode.podcast_generator_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feature7", tags=["Podcast Generation"])


@router.post("/generate", response_model=Feature7Output)
async def generate_podcast(input_data: Feature7Input):
    """
    Generate a podcast for a given topic
    
    This endpoint:
    1. Generates a natural conversation script between two hosts (Alex and Sam)
    2. Converts the script to audio with distinct voices
    3. Uploads the audio to Supabase
    4. Returns the audio URL
    
    Args:
        input_data: Contains user_id, chat_id, and topic
        
    Returns:
        Feature7Output with audio_url, duration, and topic
    """
    try:
        logger.info(f"📻 Podcast generation request - User: {input_data.user_id}, Chat: {input_data.chat_id}")
        logger.info(f"📝 Topic: {input_data.topic}")
        
        # Invoke the podcast generator graph
        result = podcast_generator_graph.invoke({
            "input": input_data
        })
        
        output = result["output"]
        
        logger.info(f"✅ Podcast generated successfully!")
        logger.info(f"   Audio URL: {output.audio_url}")
        logger.info(f"   Duration: {output.duration_seconds}s")
        
        return output
        
    except Exception as e:
        logger.error(f"❌ Error generating podcast: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating podcast: {str(e)}")


@router.get("/chats/{user_id}", response_model=GetPodcastChatsResponse)
async def get_user_podcast_chats(user_id: str):
    """
    Get all podcast chat sessions for a user
    
    Returns list of chats with metadata:
    - chat_id
    - podcast_count (number of podcasts in this chat)
    - last_updated timestamp
    
    Args:
        user_id: User identifier
        
    Returns:
        GetPodcastChatsResponse with list of chat summaries
    """
    try:
        logger.info(f"📋 Fetching podcast chats for user: {user_id}")
        
        chats_data = get_all_podcast_chat_ids(user_id)
        
        chats = [
            PodcastChatSummary(
                chat_id=chat["chat_id"],
                podcast_count=chat["podcast_count"],
                last_updated=chat["last_updated"]
            )
            for chat in chats_data
        ]
        
        logger.info(f"✅ Found {len(chats)} podcast chats")
        
        return GetPodcastChatsResponse(
            user_id=user_id,
            chats=chats
        )
        
    except Exception as e:
        logger.error(f"❌ Error fetching podcast chats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching chats: {str(e)}")


@router.get("/history/{user_id}/{chat_id}", response_model=GetPodcastHistoryResponse)
async def get_podcast_chat_history(user_id: str, chat_id: str):
    """
    Get complete podcast history for a specific chat
    
    Returns all podcasts generated in this chat session in chronological order.
    Each podcast includes:
    - topic
    - audio_url (Supabase link to MP3 file)
    - duration_seconds
    - created_at timestamp
    
    Args:
        user_id: User identifier
        chat_id: Chat session identifier
        
    Returns:
        GetPodcastHistoryResponse with list of podcasts
    """
    try:
        logger.info(f"📜 Fetching podcast history - User: {user_id}, Chat: {chat_id}")
        
        # Check if chat exists
        if not podcast_chat_exists(user_id, chat_id):
            raise HTTPException(
                status_code=404,
                detail=f"Podcast chat not found for user_id={user_id}, chat_id={chat_id}"
            )
        
        # Get history
        history = get_podcast_history(user_id, chat_id)
        
        podcasts = [
            PodcastMessageItem(
                topic=topic,
                audio_url=audio_url,
                duration_seconds=duration,
                created_at=created_at
            )
            for topic, audio_url, duration, created_at in history
        ]
        
        logger.info(f"✅ Found {len(podcasts)} podcasts in chat")
        
        return GetPodcastHistoryResponse(
            user_id=user_id,
            chat_id=chat_id,
            podcasts=podcasts
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching podcast history: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@router.delete("/chat/{user_id}/{chat_id}", response_model=DeletePodcastChatResponse)
async def delete_podcast_chat_endpoint(user_id: str, chat_id: str):
    """
    Delete a podcast chat session
    
    This removes all podcasts associated with this chat from the database.
    Note: This does NOT delete the audio files from Supabase storage.
    You should implement a cleanup job to remove orphaned audio files.
    
    Args:
        user_id: User identifier
        chat_id: Chat session identifier
        
    Returns:
        DeletePodcastChatResponse with success status
    """
    try:
        logger.info(f"🗑️ Deleting podcast chat - User: {user_id}, Chat: {chat_id}")
        
        # Check if chat exists
        if not podcast_chat_exists(user_id, chat_id):
            raise HTTPException(
                status_code=404,
                detail=f"Podcast chat not found for user_id={user_id}, chat_id={chat_id}"
            )
        
        # Delete chat
        success = delete_podcast_chat(user_id, chat_id)
        
        if success:
            logger.info(f"✅ Podcast chat deleted successfully")
            return DeletePodcastChatResponse(
                success=True,
                message="Podcast chat deleted successfully",
                deleted_chat_id=chat_id
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete podcast chat")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting podcast chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting chat: {str(e)}")


# Health check endpoint
@router.get("/health")
async def health_check():
    """Check if Feature 7 (Podcast Generation) is working"""
    return {
        "status": "healthy",
        "feature": "Podcast Generation (Feature 7)",
        "description": "Generates educational podcasts with two-host conversations"
    }