from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage 
from pydantic_models import feature1_6, GetChatsRequest, GetConversationRequest
from chat import process_chat_message, retrieve_all_threads, get_thread_id
from F1_history_db import get_all_chat_ids, load_full_history
import logging


# Feature 2 - OCR Image Doubt Solver
from F2.F2_chat import ocr_doubt_solver_graph
from F2.F2_models import Feature2Input
from F2.F2_history_db import (
    load_full_history as f2_load_full_history,
    get_all_chat_ids as f2_get_all_chat_ids,
    delete_chat as f2_delete_chat,
    chat_exists as f2_chat_exists,
    get_image_count as f2_get_image_count
)
from F2.F2_ocr_db import (
    delete_chat_ocr as f2_delete_chat_ocr,
    get_all_ocr_extractions as f2_get_all_ocr_extractions
)
from pydantic import BaseModel
import shutil
from pathlib import Path


# Feature 4 pdf rag
from F4.F4_chatnode import pdf_rag_graph
from F4.F4_models import Feature4Input
from F4.F4_history_db import load_full_history as f4_load_full_history, get_all_chat_ids as f4_get_all_chat_ids

# Feature 5 video rag
from F5.F5_chatnode import video_rag_graph
from F5.F5_models import Feature5Input
from F5.F5_history_db import (
    load_full_history as f5_load_full_history,
    get_all_chat_ids as f5_get_all_chat_ids,
    delete_chat as f5_delete_chat,
    chat_exists as f5_chat_exists
)
from F5.F5_meta_db import get_youtube_url_for_chat, delete_chat_index

# Feature 7 - Podcast Generator
from F7._F7_chatnode import podcast_generator_graph
from F7._F7_models import Feature7Input
from F7._F7_podcast_db import (
    get_podcast_history as f7_get_podcast_history,
    get_all_podcast_chat_ids as f7_get_all_podcast_chat_ids,
    delete_podcast_chat as f7_delete_podcast_chat,
    podcast_chat_exists as f7_podcast_chat_exists
)



from F8._F8_chatnode import gita_counselor_graph
from F8._F8_models import Feature8Input
from F8._F8_gita_db import (
    get_gita_history as f8_get_gita_history,
    get_all_gita_chat_ids as f8_get_all_gita_chat_ids,
    delete_gita_chat as f8_delete_gita_chat,
    gita_chat_exists as f8_gita_chat_exists
)
from F8._F8_gita_rag import ensure_gita_index_exists
from F8._F8_models import Feature8Input


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="AI Backend API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins. For production, specify: ["http://localhost:3000", "https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# ============================================
# FEATURE 1: AI TEACHER CHAT
# ============================================

@app.post("/chat")
def chat(obj: feature1_6):
    """
    Feature 1: AI Teacher Chat - Returns full state with message history
    
    This uses the new user-separated process_chat_message function that:
    - Separates users by user_id and chat_id
    - Fixes search tool + manim execution (both work now)
    - Uploads videos to Supabase instead of local paths
    - Returns full conversation state with message history
    """
    try:
        logger.info(f"Feature 1 Chat: user_id={obj.user_id}, chat_id={obj.chat_id}")
        
        # Use the new process_chat_message function with all fixes
        full_state = process_chat_message(
            user_id=obj.user_id,
            chat_id=obj.chat_id,
            message=obj.message
        )
        
        # Load complete conversation history from database
        history = load_full_history(obj.user_id, obj.chat_id)
        
        # Format messages for frontend
        messages = [
            {"role": role, "content": content}
            for role, content in history
        ]
        
        # Return full state with complete message history
        return {
            "working": full_state,
            "user_id": obj.user_id,
            "chat_id": obj.chat_id,
            "messages": messages,
            "total_messages": len(messages)
        }
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/feature1_getthreads")
def feature1_getthreads():
    """
    Feature 1: Get all active thread IDs
    
    Returns a list of all conversation threads in the system.
    Thread IDs follow the format: {user_id}_{chat_id}
    """
    try:
        threads = retrieve_all_threads()
        
        # Parse thread IDs to extract user_id and chat_id
        parsed_threads = []
        for thread_id in threads:
            if "_" in thread_id:
                parts = thread_id.split("_", 1)
                parsed_threads.append({
                    "thread_id": thread_id,
                    "user_id": parts[0],
                    "chat_id": parts[1]
                })
            else:
                # Legacy thread without user/chat separation
                parsed_threads.append({
                    "thread_id": thread_id,
                    "user_id": "unknown",
                    "chat_id": "unknown"
                })
        
        return {
            "working": True,
            "total_threads": len(threads),
            "threads": parsed_threads
        }
        
    except Exception as e:
        logger.error(f"Error in feature1_getthreads: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/feature1_get_user_chats/{user_id}")
def feature1_get_user_chats(user_id: str):
    """
    Feature 1: Get all chats for a specific user
    
    Returns all chat IDs associated with a given user from the history database.
    """
    try:
        # Get all chat IDs for this user from the history database
        chat_ids = get_all_chat_ids(user_id)
        
        # Format the response
        chats = [
            {
                "chat_id": chat_id,
                "thread_id": f"{user_id}_{chat_id}"
            }
            for chat_id in chat_ids
        ]
        
        return {
            "working": True,
            "user_id": user_id,
            "total_chats": len(chats),
            "chats": chats
        }
        
    except Exception as e:
        logger.error(f"Error in feature1_get_user_chats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature1_get_conversation")
def feature1_get_conversation(data: GetConversationRequest):
    """
    Feature 1: Get complete conversation history for a specific chat
    
    Returns all messages in the conversation in chronological order.
    """
    try:
        # Load conversation history from database
        history = load_full_history(data.user_id, data.chat_id)
        
        # Format messages
        messages = [
            {"role": role, "content": content}
            for role, content in history
        ]
        
        return {
            "working": True,
            "user_id": data.user_id,
            "chat_id": data.chat_id,
            "messages": messages,
            "total_messages": len(messages)
        }
        
    except Exception as e:
        logger.error(f"Error in feature1_get_conversation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# FEATURE 2: OCR IMAGE DOUBT SOLVER
# ============================================

# Pydantic models for Feature 2 endpoints
class Feature2GetChatsRequest(BaseModel):
    user_id: str


class Feature2GetChatHistoryRequest(BaseModel):
    user_id: str
    chat_id: str


class Feature2DeleteChatRequest(BaseModel):
    user_id: str
    chat_id: str


@app.post("/ocr_doubt_solver")
def ocr_doubt_solver(data: Feature2Input):
    """
    Feature 2: Main OCR Doubt Solver endpoint
    
    Process a student's doubt about an uploaded image and return the answer with full chat history.
    Automatically extracts text from new images and uses all previously uploaded images as context.
    
    Args:
        data: Feature2Input containing user_id, chat_id, image_url (Supabase), message
    
    Returns:
        Complete chat history with latest AI answer and referenced images
    """
    try:
        logger.info(f"Feature 2 OCR Doubt Solver: user_id={data.user_id}, chat_id={data.chat_id}")
        logger.info(f"Image URL: {data.image_url}")
        logger.info(f"Student doubt: {data.message[:100]}...")
        
        state = {"input": data}
        result = ocr_doubt_solver_graph.invoke(state)

        # Load full history
        history = f2_load_full_history(data.user_id, data.chat_id)
        messages = [
            {"role": r, "content": c, "referenced_images": imgs} 
            for r, c, imgs in history
        ]

        return {
            "user_id": data.user_id,
            "chat_id": data.chat_id,
            "messages": messages,
            "latest_answer": result["answer"].model_dump(),
            "total_messages": len(messages)
        }
        
    except Exception as e:
        logger.error(f"Error in ocr_doubt_solver: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature2_get_chats")
def feature2_get_chats(data: Feature2GetChatsRequest):
    """
    Feature 2: Get all chat IDs for a specific user with metadata
    
    Returns all chats associated with a user, including message counts,
    number of images, and last update timestamps.
    
    Args:
        data: Contains user_id
    
    Returns:
        List of chats with chat_id, message_count, image_count, last_updated
    """
    try:
        logger.info(f"Feature 2 Get Chats: user_id={data.user_id}")
        
        chat_data = f2_get_all_chat_ids(data.user_id)
        
        # Enrich with image count
        chats = []
        for chat in chat_data:
            image_count = f2_get_image_count(data.user_id, chat["chat_id"])
            chats.append({
                "chat_id": chat["chat_id"],
                "message_count": chat["message_count"],
                "image_count": image_count,
                "last_updated": chat["last_updated"]
            })
        
        return {
            "user_id": data.user_id,
            "chats": chats,
            "total_chats": len(chats)
        }
        
    except Exception as e:
        logger.error(f"Error in feature2_get_chats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature2_get_chat_history")
def feature2_get_chat_history(data: Feature2GetChatHistoryRequest):
    """
    Feature 2: Get complete chat history for a specific OCR doubt-solving chat
    
    Returns all messages with their referenced images and all OCR extractions for this chat.
    
    Args:
        data: Contains user_id and chat_id
    
    Returns:
        Complete message history with image metadata
    """
    try:
        logger.info(f"Feature 2 Get Chat History: user_id={data.user_id}, chat_id={data.chat_id}")
        
        # Check if chat exists
        if not f2_chat_exists(data.user_id, data.chat_id):
            raise HTTPException(
                status_code=404,
                detail=f"Chat not found for user_id={data.user_id}, chat_id={data.chat_id}"
            )
        
        # Load complete history
        history = f2_load_full_history(data.user_id, data.chat_id)
        messages = [
            {"role": r, "content": c, "referenced_images": imgs} 
            for r, c, imgs in history
        ]
        
        # Get all OCR extractions for this chat
        ocr_extractions = f2_get_all_ocr_extractions(data.user_id, data.chat_id)
        
        return {
            "user_id": data.user_id,
            "chat_id": data.chat_id,
            "messages": messages,
            "images": ocr_extractions,
            "total_messages": len(messages),
            "total_images": len(ocr_extractions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in feature2_get_chat_history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature2_delete_chat")
def feature2_delete_chat(data: Feature2DeleteChatRequest):
    """
    Feature 2: Delete an OCR doubt-solving chat and all associated data
    
    Deletes the chat from history database and OCR extraction database.
    
    Args:
        data: Contains user_id and chat_id
    
    Returns:
        Success status and confirmation message
    """
    try:
        logger.info(f"Feature 2 Delete Chat: user_id={data.user_id}, chat_id={data.chat_id}")
        
        # Check if chat exists
        if not f2_chat_exists(data.user_id, data.chat_id):
            raise HTTPException(
                status_code=404,
                detail=f"Chat not found for user_id={data.user_id}, chat_id={data.chat_id}"
            )
        
        # Delete from history database
        history_deleted = f2_delete_chat(data.user_id, data.chat_id)
        
        # Delete from OCR database
        ocr_deleted = f2_delete_chat_ocr(data.user_id, data.chat_id)
        
        logger.info(f"Chat deletion: history={history_deleted}, ocr={ocr_deleted}")
        
        if history_deleted:
            return {
                "success": True,
                "message": f"Chat {data.chat_id} successfully deleted with all OCR data",
                "deleted_chat_id": data.chat_id
            }
        else:
            return {
                "success": False,
                "message": "Chat deletion failed or chat was already empty",
                "deleted_chat_id": data.chat_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in feature2_delete_chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# FEATURE 4: PDF RAG
# ============================================

@app.post("/pdf_ingest")
def pdf_ingest(data: Feature4Input):
    state = {"input": data}
    result = pdf_rag_graph.invoke(state)

    history = f4_load_full_history(data.user_id, data.chat_id)

    messages = [
        {"role": role, "content": content}
        for role, content in history
    ]

    return {
        "user_id": data.user_id,
        "chat_id": data.chat_id,
        "messages": messages,
        "latest_answer": result["answer"].model_dump(),
    }
    
    


@app.post("/get_user_chats")
def get_user_chats(data: GetChatsRequest):
    """
    Get all chat IDs for a specific user.
    
    Args:
        data: Contains user_id
    
    Returns:
        user_id and list of all chat_ids
    """
    try:
        chat_ids = f4_get_all_chat_ids(data.user_id)
        
        return {
            "user_id": data.user_id,
            "chat_ids": chat_ids,
            "total_chats": len(chat_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_conversation")
def get_conversation(data: GetConversationRequest):
    """
    Get complete conversation history for a specific chat.
    
    Args:
        data: Contains user_id and chat_id
    
    Returns:
        user_id, chat_id, and all messages in the conversation
    """
    try:
        history = f4_load_full_history(data.user_id, data.chat_id)
        
        messages = [
            {"role": role, "content": content}
            for role, content in history
        ]
        
        return {
            "user_id": data.user_id,
            "chat_id": data.chat_id,
            "messages": messages,
            "total_messages": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# FEATURE 5: VIDEO RAG (YOUTUBE TUTOR)
# ============================================

# Pydantic models for Feature 5 endpoints
class Feature5GetChatsRequest(BaseModel):
    user_id: str


class Feature5GetChatHistoryRequest(BaseModel):
    user_id: str
    chat_id: str


class Feature5DeleteChatRequest(BaseModel):
    user_id: str
    chat_id: str


@app.post("/video_rag")
def video_rag(data: Feature5Input):
    """
    Feature 5: Main Video RAG endpoint
    
    Process a question about a YouTube video and return the answer with full chat history.
    
    Args:
        data: Feature5Input containing user_id, chat_id, youtube_url, message
    
    Returns:
        Complete chat history with latest AI answer and relevant timestamps
    """
    try:
        logger.info(f"Feature 5 Video RAG: user_id={data.user_id}, chat_id={data.chat_id}")
        
        state = {"input": data}
        result = video_rag_graph.invoke(state)

        history = f5_load_full_history(data.user_id, data.chat_id)
        messages = [
            {"role": r, "content": c} for r, c in history
        ]

        return {
            "user_id": data.user_id,
            "chat_id": data.chat_id,
            "messages": messages,
            "latest_answer": result["answer"].model_dump(),
        }
        
    except Exception as e:
        logger.error(f"Error in video_rag: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature5_get_chats")
def feature5_get_chats(data: Feature5GetChatsRequest):
    """
    Feature 5: Get all chat IDs for a specific user with metadata
    
    Returns all chats associated with a user, including message counts,
    YouTube URLs, and last update timestamps.
    
    Args:
        data: Contains user_id
    
    Returns:
        List of chats with chat_id, message_count, youtube_url, last_updated
    """
    try:
        logger.info(f"Feature 5 Get Chats: user_id={data.user_id}")
        
        chat_data = f5_get_all_chat_ids(data.user_id)
        
        # Enrich with YouTube URL if available
        chats = []
        for chat in chat_data:
            youtube_url = get_youtube_url_for_chat(data.user_id, chat["chat_id"])
            chats.append({
                "chat_id": chat["chat_id"],
                "message_count": chat["message_count"],
                "youtube_url": youtube_url,
                "last_updated": chat["last_updated"]
            })
        
        return {
            "user_id": data.user_id,
            "chats": chats,
            "total_chats": len(chats)
        }
        
    except Exception as e:
        logger.error(f"Error in feature5_get_chats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature5_get_chat_history")
def feature5_get_chat_history(data: Feature5GetChatHistoryRequest):
    """
    Feature 5: Get complete chat history for a specific video chat
    
    Returns all messages in the conversation in human-ai format.
    
    Args:
        data: Contains user_id and chat_id
    
    Returns:
        Complete message history for the chat
    """
    try:
        logger.info(f"Feature 5 Get Chat History: user_id={data.user_id}, chat_id={data.chat_id}")
        
        # Check if chat exists
        if not f5_chat_exists(data.user_id, data.chat_id):
            raise HTTPException(
                status_code=404,
                detail=f"Chat not found for user_id={data.user_id}, chat_id={data.chat_id}"
            )
        
        # Load complete history
        history = f5_load_full_history(data.user_id, data.chat_id)
        messages = [
            {"role": r, "content": c} for r, c in history
        ]
        
        return {
            "user_id": data.user_id,
            "chat_id": data.chat_id,
            "messages": messages,
            "total_messages": len(messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in feature5_get_chat_history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature5_delete_chat")
def feature5_delete_chat(data: Feature5DeleteChatRequest):
    """
    Feature 5: Delete a video chat and all associated data
    
    Deletes the chat from history database, meta database, and removes FAISS indices.
    
    Args:
        data: Contains user_id and chat_id
    
    Returns:
        Success status and confirmation message
    """
    try:
        logger.info(f"Feature 5 Delete Chat: user_id={data.user_id}, chat_id={data.chat_id}")
        
        # Check if chat exists
        if not f5_chat_exists(data.user_id, data.chat_id):
            raise HTTPException(
                status_code=404,
                detail=f"Chat not found for user_id={data.user_id}, chat_id={data.chat_id}"
            )
        
        # Delete from history database
        history_deleted = f5_delete_chat(data.user_id, data.chat_id)
        
        # Delete from meta database (indexed videos)
        index_deleted = delete_chat_index(data.user_id, data.chat_id)
        
        # Delete FAISS index files
        try:
            chat_dir = Path("./f5_store") / data.user_id / data.chat_id
            if chat_dir.exists():
                shutil.rmtree(chat_dir)
                logger.info(f"Deleted FAISS directory: {chat_dir}")
        except Exception as e:
            logger.warning(f"Could not delete FAISS directory: {e}")
        
        if history_deleted:
            return {
                "success": True,
                "message": f"Chat {data.chat_id} successfully deleted",
                "deleted_chat_id": data.chat_id
            }
        else:
            return {
                "success": False,
                "message": "Chat deletion failed or chat was already empty",
                "deleted_chat_id": data.chat_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in feature5_delete_chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# FEATURE 7: PODCAST GENERATOR
# ============================================

# Pydantic models for Feature 7 endpoints
class Feature7GetChatsRequest(BaseModel):
    user_id: str


class Feature7GetChatHistoryRequest(BaseModel):
    user_id: str
    chat_id: str


class Feature7DeleteChatRequest(BaseModel):
    user_id: str
    chat_id: str


@app.post("/podcast_generate")
def podcast_generate(data: Feature7Input):
    """
    Feature 7: Main Podcast Generator endpoint
    
    Generate an educational podcast on any topic with natural two-host conversation.
    
    Args:
        data: Feature7Input containing user_id, chat_id, topic
    
    Returns:
        Audio URL and podcast metadata
    """
    try:
        logger.info(f"Feature 7 Podcast Generator: user_id={data.user_id}, chat_id={data.chat_id}")
        logger.info(f"Topic: {data.topic}")
        
        state = {"input": data}
        result = podcast_generator_graph.invoke(state)

        return {
            "user_id": data.user_id,
            "chat_id": data.chat_id,
            "audio_url": result["output"].audio_url,
            "duration_seconds": result["output"].duration_seconds,
            "topic": result["output"].topic
        }
        
    except Exception as e:
        logger.error(f"Error in podcast_generate: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature7_get_chats")
def feature7_get_chats(data: Feature7GetChatsRequest):
    """
    Feature 7: Get all podcast chat IDs for a specific user with metadata
    
    Returns all chats associated with a user, including podcast counts
    and last update timestamps.
    
    Args:
        data: Contains user_id
    
    Returns:
        List of chats with chat_id, podcast_count, last_updated
    """
    try:
        logger.info(f"Feature 7 Get Chats: user_id={data.user_id}")
        
        chat_data = f7_get_all_podcast_chat_ids(data.user_id)
        
        return {
            "user_id": data.user_id,
            "chats": chat_data,
            "total_chats": len(chat_data)
        }
        
    except Exception as e:
        logger.error(f"Error in feature7_get_chats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature7_get_chat_history")
def feature7_get_chat_history(data: Feature7GetChatHistoryRequest):
    """
    Feature 7: Get complete podcast history for a specific chat
    
    Returns all podcasts generated in this chat session.
    
    Args:
        data: Contains user_id and chat_id
    
    Returns:
        Complete podcast history for the chat
    """
    try:
        logger.info(f"Feature 7 Get Chat History: user_id={data.user_id}, chat_id={data.chat_id}")
        
        # Check if chat exists
        if not f7_podcast_chat_exists(data.user_id, data.chat_id):
            raise HTTPException(
                status_code=404,
                detail=f"Podcast chat not found for user_id={data.user_id}, chat_id={data.chat_id}"
            )
        
        # Load complete history
        history = f7_get_podcast_history(data.user_id, data.chat_id)
        podcasts = [
            {
                "topic": topic,
                "audio_url": audio_url,
                "duration_seconds": duration,
                "created_at": created_at
            }
            for topic, audio_url, duration, created_at in history
        ]
        
        return {
            "user_id": data.user_id,
            "chat_id": data.chat_id,
            "podcasts": podcasts,
            "total_podcasts": len(podcasts)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in feature7_get_chat_history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature7_delete_chat")
def feature7_delete_chat(data: Feature7DeleteChatRequest):
    """
    Feature 7: Delete a podcast chat and all associated data
    
    Deletes the chat from podcast history database.
    
    Args:
        data: Contains user_id and chat_id
    
    Returns:
        Success status and confirmation message
    """
    try:
        logger.info(f"Feature 7 Delete Chat: user_id={data.user_id}, chat_id={data.chat_id}")
        
        # Check if chat exists
        if not f7_podcast_chat_exists(data.user_id, data.chat_id):
            raise HTTPException(
                status_code=404,
                detail=f"Podcast chat not found for user_id={data.user_id}, chat_id={data.chat_id}"
            )
        
        # Delete from podcast database
        success = f7_delete_podcast_chat(data.user_id, data.chat_id)
        
        if success:
            return {
                "success": True,
                "message": f"Podcast chat {data.chat_id} successfully deleted",
                "deleted_chat_id": data.chat_id
            }
        else:
            return {
                "success": False,
                "message": "Podcast chat deletion failed or chat was already empty",
                "deleted_chat_id": data.chat_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in feature7_delete_chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



"""
Feature 8: Bhagavad Gita Life Counselor - FastAPI Endpoints

Add this section to your main.py file under the "FEATURE 8" section.
"""

# ============================================
# FEATURE 8: BHAGAVAD GITA LIFE COUNSELOR
# ============================================

# Add these imports at the top of main.py with other feature imports:
"""

"""

# Add this at application startup (after app initialization):
"""
# Ensure Gita index exists at startup
@app.on_event("startup")
async def startup_event():
    logger.info("🕉️  Initializing Bhagavad Gita Life Counselor...")
    try:
        ensure_gita_index_exists()
        logger.info("✅ Gita index ready")
    except Exception as e:
        logger.error(f"❌ Error initializing Gita index: {e}")
"""

# Pydantic models for Feature 8 endpoints
class Feature8GetChatsRequest(BaseModel):
    user_id: str


class Feature8GetChatHistoryRequest(BaseModel):
    user_id: str
    chat_id: str


class Feature8DeleteChatRequest(BaseModel):
    user_id: str
    chat_id: str


@app.post("/gita_counseling")
def gita_counseling(data: Feature8Input):
    """
    Feature 8: Main Bhagavad Gita Life Counselor endpoint

    Returns:
    - Audio guidance (Supabase URL)
    - Full structured counseling data
    """
    try:
        logger.info(
            f"🕉️  Gita Counseling Request - "
            f"User: {data.user_id}, Chat: {data.chat_id}"
        )
        logger.info(f"📿 Language: {data.preferred_language}")
        logger.info(f"❓ Doubt: {data.doubt[:100]}...")

        # Invoke LangGraph
        state = {"input": data}
        result = gita_counselor_graph.invoke(state)

        output = result["output"]

        return {
            # --- identifiers ---
            "user_id": data.user_id,
            "chat_id": data.chat_id,
            "language": data.preferred_language,

            # --- audio (PRIMARY OUTPUT) ---
            "audio_url": output.audio_url,

            # --- textual + structured data ---
            "guidance": output.guidance,
            "referenced_shlokas": [
                s.model_dump() for s in output.referenced_shlokas
            ],
            "life_examples": output.life_examples,
            "key_teachings": output.key_teachings,
        }

    except Exception as e:
        logger.error(
            f"❌ Error in gita_counseling: {str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
    
    
@app.post("/feature8_get_chats")
def feature8_get_chats(data: Feature8GetChatsRequest):
    """
    Feature 8: Get all Gita counseling chat IDs for a specific user with metadata
    
    Returns all chats associated with a user, including counseling counts
    and last update timestamps.
    
    Args:
        data: Contains user_id
    
    Returns:
        List of chats with chat_id, counseling_count, last_updated
    """
    try:
        logger.info(f"📋 Feature 8 Get Chats: user_id={data.user_id}")
        
        chat_data = f8_get_all_gita_chat_ids(data.user_id)
        
        return {
            "user_id": data.user_id,
            "chats": chat_data,
            "total_chats": len(chat_data)
        }
        
    except Exception as e:
        logger.error(f"❌ Error in feature8_get_chats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature8_get_chat_history")
def feature8_get_chat_history(data: Feature8GetChatHistoryRequest):
    """
    Feature 8: Get complete counseling history for a specific Gita chat
    
    Returns all counseling sessions in this chat with guidance and shlokas.
    
    Args:
        data: Contains user_id and chat_id
    
    Returns:
        Complete counseling history for the chat
    """
    try:
        logger.info(f"📜 Feature 8 Get Chat History: user_id={data.user_id}, chat_id={data.chat_id}")
        
        # Check if chat exists
        if not f8_gita_chat_exists(data.user_id, data.chat_id):
            raise HTTPException(
                status_code=404,
                detail=f"Gita counseling chat not found for user_id={data.user_id}, chat_id={data.chat_id}"
            )
        
        # Load complete history
        import json
        history = f8_get_gita_history(data.user_id, data.chat_id)
        
        counselings = [
            {
                "doubt": doubt,
                "guidance": guidance,
                "language": language,
                "referenced_shlokas": json.loads(shlokas_json),
                "created_at": created_at
            }
            for doubt, guidance, language, shlokas_json, created_at in history
        ]
        
        return {
            "user_id": data.user_id,
            "chat_id": data.chat_id,
            "counselings": counselings,
            "total_counselings": len(counselings)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in feature8_get_chat_history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feature8_delete_chat")
def feature8_delete_chat(data: Feature8DeleteChatRequest):
    """
    Feature 8: Delete a Gita counseling chat and all associated data
    
    Deletes the chat from counseling history database.
    
    Args:
        data: Contains user_id and chat_id
    
    Returns:
        Success status and confirmation message
    """
    try:
        logger.info(f"🗑️  Feature 8 Delete Chat: user_id={data.user_id}, chat_id={data.chat_id}")
        
        # Check if chat exists
        if not f8_gita_chat_exists(data.user_id, data.chat_id):
            raise HTTPException(
                status_code=404,
                detail=f"Gita counseling chat not found for user_id={data.user_id}, chat_id={data.chat_id}"
            )
        
        # Delete from database
        success = f8_delete_gita_chat(data.user_id, data.chat_id)
        
        if success:
            return {
                "success": True,
                "message": f"Gita counseling chat {data.chat_id} successfully deleted",
                "deleted_chat_id": data.chat_id
            }
        else:
            return {
                "success": False,
                "message": "Gita counseling chat deletion failed or chat was already empty",
                "deleted_chat_id": data.chat_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in feature8_delete_chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@app.get("/feature8_health")
async def feature8_health():
    """Check if Feature 8 (Gita Life Counselor) is working"""
    return {
        "status": "healthy",
        "feature": "Bhagavad Gita Life Counselor (Feature 8)",
        "description": "Divine guidance from Lord Krishna based on eternal Gita wisdom"
    }

# ============================================
# OTHER FEATURES (PLACEHOLDERS)
# ============================================

@app.get("/test_generate")
def test_generate():
    # Feature 9
    return {"working": True}


@app.get("/live_class")
def live_class():
    # Feature 11
    return {"working": True}


@app.get("/emotion")
def emotion():
    # Feature 12
    return {"working": True}


@app.get("/profile")
def profile():
    # Feature 8
    return {"working": True}


@app.get("/manim")
def manim():
    # Feature 3
    return {"working": True}


@app.get("/concepts")
def concepts():
    return {"working": True}