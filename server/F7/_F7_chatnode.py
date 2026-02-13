import os
from pathlib import Path
from typing import TypedDict
import sys
import tempfile
import logging

from langgraph.graph import StateGraph, START, END

# Direct imports without using package structure
import importlib.util

# Get the directory where this file is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Import _F7_models
spec = importlib.util.spec_from_file_location("_F7_models", os.path.join(current_dir, "_F7_models.py"))
F7_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F7_models)
Feature7Input = F7_models.Feature7Input
Feature7Output = F7_models.Feature7Output

# Import _F7_podcast_db
spec = importlib.util.spec_from_file_location("_F7_podcast_db", os.path.join(current_dir, "_F7_podcast_db.py"))
F7_podcast_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F7_podcast_db)
save_podcast = F7_podcast_db.save_podcast

# Import _F7_script_generator
spec = importlib.util.spec_from_file_location("_F7_script_generator", os.path.join(current_dir, "_F7_script_generator.py"))
F7_script_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F7_script_generator)
podcast_script_generator = F7_script_generator.podcast_script_generator

# Import _F7_audio_generator
spec = importlib.util.spec_from_file_location("_F7_audio_generator", os.path.join(current_dir, "_F7_audio_generator.py"))
F7_audio_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F7_audio_generator)
generate_podcast_audio = F7_audio_generator.generate_podcast_audio

logger = logging.getLogger(__name__)


class PodcastState(TypedDict):
    input: Feature7Input
    script: str
    audio_file_path: str
    audio_url: str
    duration_seconds: int
    output: Feature7Output


def script_generation_node(state: PodcastState):
    """Generate podcast script for the topic"""
    i = state["input"]
    
    logger.info(f"🎙️ Generating script for topic: '{i.topic}'")
    logger.info(f"   User: {i.user_id}, Chat: {i.chat_id}")
    
    # Use the script generator graph
    result = podcast_script_generator.invoke({
        "topic": i.topic
    })
    
    script = result["script"]
    state["script"] = script
    
    logger.info(f"✅ Script generated ({len(script)} characters)")
    
    return state


def audio_generation_node(state: PodcastState):
    """Convert script to audio with two distinct voices"""
    i = state["input"]
    script = state["script"]
    
    logger.info("🔊 Converting script to audio...")
    
    # Create temporary file for audio
    temp_dir = Path(tempfile.gettempdir())
    audio_filename = f"podcast_{i.user_id}_{i.chat_id}_{os.urandom(4).hex()}.mp3"
    audio_path = temp_dir / audio_filename
    
    try:
        # Generate audio from script
        duration_seconds = generate_podcast_audio(script, str(audio_path))
        
        logger.info(f"✅ Audio generated: {audio_path} ({duration_seconds}s)")
        
        state["audio_file_path"] = str(audio_path)
        state["duration_seconds"] = duration_seconds
        
    except Exception as e:
        logger.error(f"❌ Error generating audio: {e}")
        # Create a fallback short audio if generation fails
        state["audio_file_path"] = ""
        state["duration_seconds"] = 0
        raise
    
    return state
def upload_to_supabase_node(state: PodcastState):
    import os
    from supabase import create_client

    i = state["input"]
    audio_path = state["audio_file_path"]

    logger.info("☁️ Uploading audio to Supabase...")

    if not audio_path or not os.path.exists(audio_path):
        raise RuntimeError("Audio file missing")

    SUPABASE_URL = os.environ["SUPABASE_URL"]
    SUPABASE_KEY = os.environ["SUPABASE_KEY"]  # MUST be service_role

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    filename = os.path.basename(audio_path)
    storage_path = f"{i.user_id}/{i.chat_id}/{filename}"

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    supabase.storage.from_("podcasts").upload(
        storage_path,
        audio_bytes,
        file_options={
            "content-type": "audio/mpeg",
            "upsert": "true"
        }
    )

    audio_url = supabase.storage.from_("podcasts").get_public_url(storage_path)

    state["audio_url"] = audio_url
    logger.info(f"✅ Uploaded to Supabase: {audio_url}")

    return state

def save_history_node(state: PodcastState):
    """Save podcast to database"""
    i = state["input"]
    
    logger.info("💾 Saving podcast to database...")
    
    # Save to podcast history
    save_podcast(
        i.user_id,
        i.chat_id,
        i.topic,
        state["audio_url"],
        state["duration_seconds"]
    )
    
    logger.info("✅ Podcast saved to history")
    
    # Create output
    state["output"] = Feature7Output(
        audio_url=state["audio_url"],
        duration_seconds=state["duration_seconds"],
        topic=i.topic
    )
    
    return state


def cleanup_node(state: PodcastState):
    """Clean up temporary files"""
    audio_path = state.get("audio_file_path", "")
    
    if audio_path and os.path.exists(audio_path):
        try:
            logger.info(f"🧹 Cleaned up temporary file: {audio_path}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete temporary file: {e}")
    
    return state


# Build the graph
graph = StateGraph(PodcastState)

# Add nodes
graph.add_node("generate_script", script_generation_node)
graph.add_node("generate_audio", audio_generation_node)
graph.add_node("upload_audio", upload_to_supabase_node)
graph.add_node("save_history", save_history_node)
graph.add_node("cleanup", cleanup_node)

# Define flow
graph.add_edge(START, "generate_script")
graph.add_edge("generate_script", "generate_audio")
graph.add_edge("generate_audio", "upload_audio")
graph.add_edge("upload_audio", "save_history")
graph.add_edge("save_history", "cleanup")
graph.add_edge("cleanup", END)

# Compile the graph
podcast_generator_graph = graph.compile()