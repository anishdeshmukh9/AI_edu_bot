from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun, YouSearchTool
from langchain_core.tools import tool
from langchain_core.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
import sqlite3
import requests
import os
import json
from F1.llm import llm
from pydantic_models import pydantic_for_feature_1_chat_output
from F1.prompts import SYSTEM_PROMPT_F1 as SYSTEM_PROMPT
import subprocess
import tempfile
from pathlib import Path
import shutil
import time
from F1_history_db import save_message, load_full_history, get_all_chat_ids, update_last_assistant_message

load_dotenv()


# -------------------- Supabase Configuration --------------------




import time
import requests
import os
from  dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")                 # https://xxxx.supabase.co
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_KEY") # service_role key
SUPABASE_BUCKET = "manim"


def upload_to_supabase(file_path: str, user_id: str, chat_id: str) -> str:
    """
    Upload a video file to Supabase Storage (manim bucket) using Service Role API.

    Args:
        file_path: Local path to the video file
        user_id: User ID for organizing files
        chat_id: Chat ID for organizing files

    Returns:
        Public URL of the uploaded video
    """

    try:
        timestamp = int(time.time())
        filename = f"{user_id}/{chat_id}/manim_{timestamp}.mp4"

        with open(file_path, "rb") as f:
            file_data = f.read()

        upload_url = (
            f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
        )

        headers = {
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "video/mp4",
            "x-upsert": "true"
        }

        response = requests.put(
            upload_url,
            headers=headers,
            data=file_data,
            timeout=60
        )

        if response.status_code in (200, 201):
            public_url = (
                f"{SUPABASE_URL}/storage/v1/object/public/"
                f"{SUPABASE_BUCKET}/{filename}"
            )
            print(f"✅ Video uploaded to Supabase (manim bucket): {public_url}")
            return public_url

        else:
            print(
                f"❌ Supabase upload failed "
                f"[{response.status_code}]: {response.text}"
            )
            return ""

    except Exception as e:
        print(f"❌ Error uploading to Supabase: {e}")
        return ""
# -------------------- Tools --------------------

search_tool = DuckDuckGoSearchRun(region="us-en")
tools = [search_tool]

llm_with_tools = llm.bind_tools(tools)

llm_with_structure = llm.with_structured_output(
    pydantic_for_feature_1_chat_output
)


# -------------------- STATE --------------------------------

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str  # Added for user separation
    chat_id: str  # Added for chat separation
    needs_manim: bool  # Track if manim is needed
    structured_output: dict  # Store structured output separately


# ----------------------------------------------------------

# --------------------- HELPER FUNCTIONS ---------------

def get_last_structured_output(state: ChatState) -> pydantic_for_feature_1_chat_output:
    """Get the last structured output from state"""
    if state.get("structured_output"):
        return pydantic_for_feature_1_chat_output(**state["structured_output"])
    
    # Fallback: search in messages
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage):
            try:
                data = json.loads(msg.content)
                return pydantic_for_feature_1_chat_output(**data)
            except Exception:
                continue

    raise ValueError("No structured output found in state")


# -------------------- Nodes --------------------

def chat_node(state: ChatState):
    """Main chat node that generates responses"""
    messages = state["messages"]

    # Inject system prompt only once per thread
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    # First let the tool-capable LLM respond
    response = llm_with_tools.invoke(messages)

    # If LLM decided to call a tool → return it directly
    if response.tool_calls:
        return {"messages": [response]}

    # Otherwise produce structured output
    structured = llm_with_structure.invoke(messages)

    ai_message = AIMessage(
        content=structured.model_dump_json(indent=2)
    )

    # Store structured output and check if manim is needed
    needs_manim = structured.Need_of_manim.upper() == "YES"
    
    # Save the assistant's response to history database
    # We store the structured output JSON so it can be retrieved later
    if state.get("user_id") and state.get("chat_id"):
        try:
            print(f"💾 Saving assistant message to database: user_id={state['user_id']}, chat_id={state['chat_id']}")
            save_message(
                user_id=state["user_id"],
                chat_id=state["chat_id"],
                role="assistant",
                content=structured.model_dump_json()
            )
            print("✅ Assistant message saved successfully")
        except Exception as e:
            print(f"❌ Error saving assistant message: {e}")
            import traceback
            traceback.print_exc()

    return {
        "messages": [ai_message],
        "structured_output": structured.model_dump(),
        "needs_manim": needs_manim
    }


def manim_node(state: ChatState) -> ChatState:
    """Generate Manim video and upload to Supabase"""
    
    try:
        output = get_last_structured_output(state)
        print(f"📊 Retrieved structured output: {output.model_dump()}")
    except Exception as e:
        print(f"❌ Error getting structured output: {e}")
        return state
    
    # If already has a valid video URL (not placeholder), skip generation
    if (output.manim_video_path and 
        not output.manim_video_path.startswith("/path/") and 
        output.manim_video_path.startswith("http")):
        print(f"⭐ Video already generated: {output.manim_video_path}")
        return state
    
    prompt = output.main_video_prompt
    print(f"\n🎬 Video Prompt: {prompt}")
    
    # Generate Manim code using LLM
    manim_generation_prompt = f"""
Generate a complete Manim Community v0.19.x animation based on this request:

REQUEST:
{prompt}

STRICT TECHNICAL REQUIREMENTS (MUST FOLLOW EXACTLY):
- The scene class MUST be named: GeneratedScene
- The class MUST extend: Scene
- Use only valid Manim Community v0.19.x APIs
- Always include:
  - self.play(...) for all animations
  - self.wait() at the end
- Only output pure Python code (no markdown, no explanations, no comments outside code)
- The code MUST run without modification

GRAPHING & AXES SAFETY RULES (CRITICAL):
- Whenever using Axes or NumberPlane:
  - x_range MUST be a list of three values: [x_min, x_max, step]
  - y_range MUST be a list of three values: [y_min, y_max, step]
  - NEVER pass a single int or float to x_range or y_range
  - Example (correct):
    Axes(x_range=[-10, 10, 1], y_range=[0, 1, 0.1])

- Whenever using axes.plot():
  - x_range MUST be a list: [x_min, x_max, step]
  - Example (correct):
    axes.plot(func, x_range=[-10, 10, 0.1])

- NEVER generate:
  - x_range = -10
  - y_range = 10
  - axes.plot(func, x_range=-10)

FUNCTION PLOTTING RULES:
- All plotted functions MUST:
  - Be continuous in the chosen range
  - Avoid division by zero
  - Avoid overflow (e.g., exp(x) for large x)
- Clamp or limit domains if needed to keep values finite

VISUAL QUALITY RULES:
- Always include:
  - Axes with labels
  - A title Text or MathTex at the top
- Use:
  - smooth animations (Create, Write, FadeIn)
  - reasonable run_time (1-3 seconds per major animation)
- Use contrasting colors for curves and axes
- Keep layouts centered and readable

NUMPY RULES:
- If using math functions:
  - Import numpy as np
  - Use np.exp, np.sin, np.cos, etc. (not math.*)

STYLE & SIMPLICITY:
- Keep the animation simple, clean, and educational
- Do NOT overcrowd the scene
- Do NOT use advanced 3D features
- Do NOT use external assets or files

OUTPUT FORMAT:
- Only valid Python code
- No markdown
- No triple backticks
- No explanations

REFERENCE TEMPLATE (FOLLOW THIS STYLE):

from manim import *
import numpy as np

class GeneratedScene(Scene):
    def construct(self):
        title = Text("Title Here").to_edge(UP)
        self.play(Write(title))

        axes = Axes(
            x_range=[-10, 10, 1],
            y_range=[0, 1, 0.1],
            x_length=10,
            y_length=5,
            axis_config={{"include_numbers": True}}
        )

        labels = axes.get_axis_labels(x_label="x", y_label="y")
        self.play(Create(axes), Write(labels))

        def func(x):
            return 1 / (1 + np.exp(-x))

        graph = axes.plot(func, x_range=[-10, 10, 0.1], color=BLUE)
        self.play(Create(graph), run_time=2)

        self.wait()

NOW generate the complete Manim code for the given request.
"""


    
    try:
        # Get Manim code from LLM
        llm_response = llm.invoke(manim_generation_prompt)
        manim_code = llm_response.content
        
        # Extract code from markdown if present
        if "```python" in manim_code:
            manim_code = manim_code.split("```python")[1].split("```")[0].strip()
        elif "```" in manim_code:
            manim_code = manim_code.split("```")[1].split("```")[0].strip()
        
        # Create temporary directory and file for Manim code
        temp_dir = tempfile.mkdtemp()
        
        code_file = os.path.join(temp_dir, "generated_animation.py")
        
        with open(code_file, "w") as f:
            f.write(manim_code)
        
        # Run Manim to generate the video
        result = subprocess.run(
            [
                "manim",
                "-pql",  # preview quality low
                code_file,
                "GeneratedScene",
                "--disable_caching"
            ],
            capture_output=True,
            text=True,
            cwd=temp_dir
        )
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("\n⚠️ Manim STDERR:")
            print(result.stderr)
        
        if result.returncode != 0:
            video_url = "/path/demo.mp4"  # fallback
        else:
            # Find the generated video - check multiple possible locations
            possible_dirs = [
                os.path.join(temp_dir, "media", "videos", "generated_animation", "1080p60"),
                os.path.join(temp_dir, "media", "videos", "generated_animation", "480p15"),
                os.path.join(temp_dir, "media", "videos", "generated_animation"),
                os.path.join(temp_dir, "media", "videos"),
            ]
            
            video_files = []
            for possible_dir in possible_dirs:
                if os.path.exists(possible_dir):
                    files = list(Path(possible_dir).glob("*.mp4"))
                    if files:
                        video_files = files
                        print(f"✅ Found {len(files)} video file(s)")
                        break
            
            if video_files:
                # Upload to Supabase
                video_url = upload_to_supabase(
                    str(video_files[0]),
                    state["user_id"],
                    state["chat_id"]
                )
            else:
                print("❌ No video files found in expected directories")
                video_url = "/path/demo.mp4"  # fallback
        
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        video_url = "/path/demo.mp4"  # fallback on error
    
    # Update the structured output with video URL
    output.manim_video_path = video_url
    
    # Update the last assistant message in the database with the new video URL
    if state.get("user_id") and state.get("chat_id"):
        update_last_assistant_message(
            user_id=state["user_id"],
            chat_id=state["chat_id"],
            content=output.model_dump_json()
        )
    
    # Build a new AI message with updated JSON
    new_ai_msg = AIMessage(content=output.model_dump_json())
    
    # Remove old structured AI messages, keep humans + tool msgs
    new_messages = []
    for msg in state["messages"]:
        if isinstance(msg, AIMessage):   
            # skip old structured JSON messages
            try:
                json.loads(msg.content)
                continue
            except Exception:
                pass
        new_messages.append(msg)
    
    # Append the final updated structured output
    new_messages.append(new_ai_msg)
    
    return {
        "messages": new_messages,
        "structured_output": output.model_dump()
    }


# ------------------------------------------------------

tool_node = ToolNode(tools)


# -------------------- Checkpointer --------------------

conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)


# ---------------- Conditional Edge -------------------

def route_after_chat(state: ChatState) -> str:
    """Route after chat node - check if tools are needed first"""
    # Check if tools are needed
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    
    # If no tools needed, go to END
    # Manim will be handled separately after the full response
    return END


def should_continue_after_tools(state: ChatState) -> str:
    """After tools execute, always return to chat to generate final response"""
    return "chat_node"


# -------------------- Graph Builder --------------------

def chat_graph_engine():
    """Build the LangGraph workflow"""
    graph = StateGraph(ChatState)

    # Add nodes
    graph.add_node("chat_node", chat_node)
    graph.add_node("tools", tool_node)
    graph.add_node("manim_node", manim_node)

    # Start with chat
    graph.add_edge(START, "chat_node")

    # Route from chat: either to tools or END
    graph.add_conditional_edges(
        "chat_node",
        route_after_chat,
        {
            "tools": "tools",
            END: END,
        },
    )

    # After tools, always go back to chat to generate final response
    graph.add_edge("tools", "chat_node")

    # Manim is NOT part of the main flow - it's handled post-processing
    graph.add_edge("manim_node", END)

    chatbot = graph.compile(checkpointer=checkpointer)
    return chatbot


# -------------------- Thread Utilities --------------------

def retrieve_all_threads():
    """Get all thread IDs from checkpointer"""
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)


def get_thread_id(user_id: str, chat_id: str) -> str:
    """Generate a unique thread ID for user and chat combination"""
    return f"{user_id}_{chat_id}"


# -------------------- Main Execution Function --------------------

def process_chat_message(user_id: str, chat_id: str, message: str):
    """
    Process a chat message with user and chat separation.
    
    Args:
        user_id: Unique user identifier
        chat_id: Unique chat identifier for this conversation
        message: User's message
        
    Returns:
        Full state dict including message history and structured output
    """
    # Save the user's message to history database
    try:
        print(f"💾 Saving user message to database: user_id={user_id}, chat_id={chat_id}")
        save_message(user_id=user_id, chat_id=chat_id, role="user", content=message)
        print("✅ User message saved successfully")
    except Exception as e:
        print(f"❌ Error saving user message: {e}")
        import traceback
        traceback.print_exc()
    
    # Create unique thread ID
    thread_id = get_thread_id(user_id, chat_id)
    
    # Initialize chatbot
    chatbot = chat_graph_engine()
    
    # Create config with thread_id for persistence
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    # Prepare initial state
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "user_id": user_id,
        "chat_id": chat_id,
        "needs_manim": False,
        "structured_output": {}
    }
    
    # Run the graph
    final_state = chatbot.invoke(initial_state, config)
    
    # Check if manim is needed and process it
    if final_state.get("needs_manim", False):
        print("\n🎬 Manim video generation requested, processing...")
        # Run manim node separately
        manim_state = manim_node(final_state)
        # Update final state with manim results
        final_state["structured_output"] = manim_state.get("structured_output", final_state.get("structured_output", {}))
        final_state["messages"] = manim_state.get("messages", final_state.get("messages", []))
    
    # Return the FULL state (like original version)
    # This includes: messages, user_id, chat_id, needs_manim, structured_output
    return final_state