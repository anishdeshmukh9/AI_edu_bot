"""
Optimized Feature 8: Bhagavad Gita Life Counselor - Main Chat Node

Key Improvements:
1. Streamlined flow with better error handling
2. ChromaDB integration for faster retrieval
3. Hybrid search for better accuracy
4. Rich metadata extraction
5. Parallel processing where possible
"""

import os
from pathlib import Path
from typing import TypedDict, List, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langgraph.graph import StateGraph, START, END

# Import optimized modules
import importlib.util

current_dir = os.path.dirname(os.path.abspath(__file__))

# Import models
spec = importlib.util.spec_from_file_location("_F8_models", os.path.join(current_dir, "_F8_models.py"))
if not spec or not spec.loader:
    raise ImportError("Could not load _F8_models")
F8_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F8_models)
Feature8Input = F8_models.Feature8Input
Feature8Output = F8_models.Feature8Output
GitaShloka = F8_models.GitaShloka

# Import database
spec = importlib.util.spec_from_file_location("_F8_gita_db", os.path.join(current_dir, "_F8_gita_db.py"))
if not spec or not spec.loader:
    raise ImportError("Could not load _F8_gita_db")
F8_gita_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F8_gita_db)
save_counseling = F8_gita_db.save_counseling

# Import optimized RAG
spec = importlib.util.spec_from_file_location("_F8_gita_rag", os.path.join(current_dir, "_F8_gita_rag.py"))
if not spec or not spec.loader:
    raise ImportError("Could not load _F8_gita_rag_optimized")
F8_gita_rag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F8_gita_rag)
hybrid_search_gita = F8_gita_rag.hybrid_search_gita
ensure_gita_index_exists = F8_gita_rag.ensure_gita_index_exists

# Import optimized guidance generator
spec = importlib.util.spec_from_file_location("_F8_guidance_generator", os.path.join(current_dir, "_F8_guidance_generator.py"))
if not spec or not spec.loader:
    raise ImportError("Could not load _F8_guidance_generator_optimized")
F8_guidance_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F8_guidance_generator)
gita_guidance_generator = F8_guidance_generator.gita_guidance_generator

# Import audio modules
from F8._F8_audio_generator import generate_gita_audio
from F8._F8_supabase_audio import upload_audio

logger = logging.getLogger(__name__)


class GitaCounselingState(TypedDict):
    input: Feature8Input
    relevant_shlokas: List[dict]
    guidance: str
    key_teachings: List[str]
    life_examples: List[str]
    output: Optional[Feature8Output]
    error: Optional[str]


def rag_search_node(state: GitaCounselingState):
    """
    Enhanced RAG search with hybrid retrieval and rich metadata
    """
    i = state["input"]
    
    logger.info("━" * 50)
    logger.info("🕉️  BHAGAVAD GITA COUNSELING REQUEST")
    logger.info("━" * 50)
    logger.info(f"👤 User: {i.user_id}")
    logger.info(f"💬 Chat: {i.chat_id}")
    logger.info(f"🌐 Language: {i.preferred_language}")
    logger.info(f"❓ Doubt: {i.doubt[:100]}...")
    logger.info("━" * 50)
    
    try:
        # Hybrid search for better accuracy
        logger.info("🔬 Performing hybrid search (semantic + keyword)...")
        documents = hybrid_search_gita(i.doubt, k=5)
        
        if not documents:
            logger.warning("⚠️  No documents found, falling back to standard search...")
            from F8._F8_gita_rag import search_gita
            documents = search_gita(i.doubt, k=5)
        
        # Convert documents to rich shloka format
        shlokas = []
        for doc in documents:
            shloka_dict = {
                "chapter": doc.metadata.get("chapter", 0),
                "verse": doc.metadata.get("verse", 0),
                "page_content": doc.page_content,
                "themes": doc.metadata.get("themes", ["general"]),
                "has_sanskrit": doc.metadata.get("has_sanskrit", False),
                # Preserve for compatibility
                "sanskrit_text": "",  # Will be in page_content
                "transliteration": "",  # Will be in page_content
                "meaning_english": doc.page_content if i.preferred_language == "english" else "",
                "meaning_hindi": doc.page_content if i.preferred_language == "hindi" else "",
                "theme": ", ".join(doc.metadata.get("themes", ["dharma"]))
            }
            shlokas.append(shloka_dict)
        
        state["relevant_shlokas"] = shlokas
        
        logger.info(f"✅ Found {len(shlokas)} relevant passages")
        for idx, shloka in enumerate(shlokas, 1):
            chapter = shloka.get('chapter', 'N/A')
            verse = shloka.get('verse', 'N/A')
            themes = shloka.get('themes', [])
            logger.info(f"   {idx}. Chapter {chapter}, Verse {verse} | {', '.join(themes[:2])}")
        
    except FileNotFoundError:
        logger.error("❌ Gita index not found! Creating index...")
        ensure_gita_index_exists()
        # Retry search
        documents = hybrid_search_gita(i.doubt, k=5)
        shlokas = [
            {
                "chapter": doc.metadata.get("chapter", 0),
                "verse": doc.metadata.get("verse", 0),
                "page_content": doc.page_content,
                "themes": doc.metadata.get("themes", ["general"]),
                "has_sanskrit": doc.metadata.get("has_sanskrit", False),
                "sanskrit_text": "",
                "transliteration": "",
                "meaning_english": doc.page_content if i.preferred_language == "english" else "",
                "meaning_hindi": doc.page_content if i.preferred_language == "hindi" else "",
                "theme": ", ".join(doc.metadata.get("themes", ["dharma"]))
            }
            for doc in documents
        ]
        state["relevant_shlokas"] = shlokas
    
    except Exception as e:
        logger.error(f"❌ Error in RAG search: {e}")
        state["error"] = f"Search error: {str(e)}"
        # Provide fallback empty list to continue flow
        state["relevant_shlokas"] = []
    
    return state


def guidance_generation_node(state: GitaCounselingState):
    """
    Generate Krishna's divine guidance with enhanced prompting
    """
    i = state["input"]
    shlokas = state["relevant_shlokas"]
    
    # Check if we have an error from previous node
    if state.get("error"):
        logger.error(f"❌ Skipping guidance generation due to error: {state['error']}")
        return state
    
    if not shlokas:
        logger.warning("⚠️  No shlokas found, providing general guidance...")
    
    logger.info("━" * 50)
    logger.info("🔮 GENERATING DIVINE GUIDANCE")
    logger.info("━" * 50)
    logger.info(f"📿 Using {len(shlokas)} sacred verses")
    logger.info(f"🌐 Language: {i.preferred_language}")
    logger.info("━" * 50)
    
    try:
        # Invoke the optimized guidance generator
        result = gita_guidance_generator.invoke({
            "doubt": i.doubt,
            "language": i.preferred_language,
            "relevant_shlokas": shlokas
        })
        
        state["guidance"] = result["guidance"]
        state["key_teachings"] = result["key_teachings"]
        state["life_examples"] = result["life_examples"]
        
        word_count = len(result["guidance"].split())
        logger.info(f"✅ Divine guidance generated")
        logger.info(f"   📝 {len(result['guidance'])} characters")
        logger.info(f"   📖 ~{word_count} words (~{word_count // 180}-{word_count // 150} min read)")
        logger.info(f"   💡 {len(result['key_teachings'])} key teachings extracted")
        logger.info(f"   🌟 {len(result['life_examples'])} life examples extracted")
        
    except Exception as e:
        logger.error(f"❌ Error generating guidance: {e}")
        state["error"] = f"Guidance generation error: {str(e)}"
        # Provide fallback guidance
        state["guidance"] = "Om Shanti. The divine wisdom guides you. Please try again."
        state["key_teachings"] = ["Trust in the divine process"]
        state["life_examples"] = ["Every challenge is an opportunity for growth"]
    
    return state


def save_history_node(state: GitaCounselingState):
    """
    Save counseling session to database with error handling
    """
    i = state["input"]
    
    logger.info("━" * 50)
    logger.info("💾 SAVING COUNSELING SESSION")
    logger.info("━" * 50)
    
    try:
        # Convert shlokas for storage
        shlokas_for_storage = state["relevant_shlokas"]
        
        # Save to database
        save_counseling(
            i.user_id,
            i.chat_id,
            i.doubt,
            state["guidance"],
            i.preferred_language,
            shlokas_for_storage
        )
        
        logger.info("✅ Counseling session saved to history")
        
        # Create output model
        # For compatibility, create GitaShloka objects
        referenced_shlokas = []
        for shloka in state["relevant_shlokas"]:
            try:
                shloka_obj = GitaShloka(
                    chapter=shloka.get("chapter", 0),
                    verse=shloka.get("verse", 0),
                    sanskrit_text=shloka.get("sanskrit_text", ""),
                    transliteration=shloka.get("transliteration", ""),
                    meaning_english=shloka.get("meaning_english", shloka.get("page_content", "")),
                    meaning_hindi=shloka.get("meaning_hindi", "")
                )
                referenced_shlokas.append(shloka_obj)
            except Exception as e:
                logger.warning(f"⚠️  Could not create GitaShloka object: {e}")
                continue
        
        state["output"] = Feature8Output(
            guidance=state["guidance"],
            referenced_shlokas=referenced_shlokas,
            life_examples=state["life_examples"],
            key_teachings=state["key_teachings"],
            audio_url=""  # Will be filled by audio generation node
        )
        
    except Exception as e:
        logger.error(f"❌ Error saving to database: {e}")
        state["error"] = f"Database error: {str(e)}"
        # Still create output even if DB save fails
        state["output"] = Feature8Output(
            guidance=state.get("guidance", ""),
            referenced_shlokas=[],
            life_examples=state.get("life_examples", []),
            key_teachings=state.get("key_teachings", []),
            audio_url=""
        )
    
    return state


def audio_generation_node(state: GitaCounselingState):
    """
    Convert guidance to audio and upload to Supabase with error handling
    """
    i = state["input"]
    guidance_text = state.get("guidance", "")
    
    logger.info("━" * 50)
    logger.info("🎙️  GENERATING AUDIO")
    logger.info("━" * 50)
    
    if not guidance_text:
        logger.error("❌ No guidance text to convert to audio")
        if state.get("output"):
            state["output"].audio_url = ""
        return state
    
    try:
        # Generate MP3
        logger.info("🎵 Converting text to speech...")
        audio_path = generate_gita_audio(guidance_text)
        logger.info(f"✅ Audio generated: {audio_path}")
        
        # Upload to Supabase
        logger.info("☁️  Uploading to Supabase...")
        audio_url = upload_audio(audio_path, i.user_id, i.chat_id)
        logger.info(f"✅ Audio uploaded: {audio_url[:50]}...")
        
        # Update output
        if state.get("output"):
            state["output"].audio_url = audio_url
        
        # Cleanup local file
        try:
            os.remove(audio_path)
            logger.info("🗑️  Cleaned up local audio file")
        except Exception as e:
            logger.warning(f"⚠️  Could not delete temp audio: {e}")
        
        logger.info("━" * 50)
        logger.info("✅ AUDIO GENERATION COMPLETE")
        logger.info("━" * 50)
        
    except Exception as e:
        logger.error(f"❌ Error in audio generation: {e}")
        state["error"] = f"Audio generation error: {str(e)}"
        if state.get("output"):
            state["output"].audio_url = ""
    
    return state


# Build the optimized graph
graph = StateGraph(GitaCounselingState)

# Add nodes
graph.add_node("rag_search", rag_search_node)
graph.add_node("generate_guidance", guidance_generation_node)
graph.add_node("save_history", save_history_node)
graph.add_node("audio_generation", audio_generation_node)

# Define optimized flow
graph.add_edge(START, "rag_search")
graph.add_edge("rag_search", "generate_guidance")
graph.add_edge("generate_guidance", "save_history")
graph.add_edge("save_history", "audio_generation")
graph.add_edge("audio_generation", END)

# Compile the graph
gita_counselor_graph = graph.compile()

logger.info("✅ Optimized Gita Counselor Graph compiled successfully")