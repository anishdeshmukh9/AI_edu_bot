from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage , AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun ,YouSearchTool
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

load_dotenv()


# -------------------- Tools --------------------

search_tool = DuckDuckGoSearchRun(region="us-en")
tools = [search_tool]

llm_with_tools = llm.bind_tools(tools)

llm_with_structure = llm.with_structured_output(
    pydantic_for_feature_1_chat_output
)



#--------------------STATE--------------------------------

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    
#----------------------------------------------------------

#---------------------hELPER FUNCTIONS---------------

def get_last_structured_output(state: ChatState) -> pydantic_for_feature_1_chat_output:
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage):
            try:
                data = json.loads(msg.content)
                return pydantic_for_feature_1_chat_output(**data)
            except Exception:
                continue

    raise ValueError("No AIMessage with structured output found in state")

# -------------------- Nodes --------------------

def chat_node(state: ChatState):
    messages = state["messages"]

    #  Inject system prompt only once per thread
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    # First let the tool-capable LLM respond
    response = llm_with_tools.invoke(messages)

    # If LLM decided to call a tool → return it directly
    if response.tool_calls:
        return {"messages": [response]}

    # 🔹 Otherwise produce structured output
    structured = llm_with_structure.invoke(messages)

    ai_message = AIMessage(
        content=structured.model_dump_json(indent=2)
    )

    return {"messages": [ai_message]}



def manim_node(state: ChatState) -> ChatState:

    
    try:
        output = get_last_structured_output(state)
        print(f" Retrieved structured output: {output.model_dump()}")
    except Exception as e:
        print(f" Error getting structured output: {e}")
        return state
    
    # 🛑 If already updated by manim → do nothing
    # Check if video path is valid (not a placeholder and file exists)
    if (output.manim_video_path and 
        not output.manim_video_path.startswith("/path/") and 
        os.path.exists(output.manim_video_path)):
        print(f"⏭  Video already generated: {output.manim_video_path}")
        return state
    
    prompt = output.main_video_prompt
    print(f"\n📝 Video Prompt: {prompt}")
    
    # 1) Generate Manim code using LLM
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
  - reasonable run_time (1 3 seconds per major animation)
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
        
   
        # 2) Create temporary directory and file for Manim code
        temp_dir = tempfile.mkdtemp()
        
        code_file = os.path.join(temp_dir, "generated_animation.py")
        
        with open(code_file, "w") as f:
            f.write(manim_code)
        
        # 3) Run Manim to generate the video
        
        # Execute manim command
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
            print("\n Manim STDERR:")
            print(result.stderr)
        
        if result.returncode != 0:
            video_path = "/path/demo.mp4"  # fallback
        else:
            
            # 4) Find the generated video - check multiple possible locations
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
                
                # Move video to permanent location
                permanent_dir = "./generated_videos"
                os.makedirs(permanent_dir, exist_ok=True)
                
                timestamp = int(time.time())
                final_video_path = os.path.join(permanent_dir, f"manim_video_{timestamp}.mp4")
                
                shutil.copy(str(video_files[0]), final_video_path)
                video_path = os.path.abspath(final_video_path)
            else:
               
                for root, dirs, files in os.walk(temp_dir):
                    print(f"  {root}:")
                    for d in dirs:
                        print(f"    📁 {d}/")
                    for f in files:
                        print(f"    📄 {f}")
                video_path = "/path/demo.mp4"  # fallback
        
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        video_path = "/path/demo.mp4"  # fallback on error
    
    # 5) Update the structured object
    output.manim_video_path = video_path
    
    # 6) Build a new AI message with updated JSON
    new_ai_msg = AIMessage(content=output.model_dump_json())
    
    # 7) Remove ALL previous structured AI messages, keep humans + tool msgs
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
    
    # 8) Append only the final updated structured output
    new_messages.append(new_ai_msg)
    
   
    return {"messages": new_messages}

#------------------------------------------------------

tool_node = ToolNode(tools)

# -------------------- Checkpointer --------------------

conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)


#---------------- conditional edge -------------------

def should_generate_manim(state: ChatState) -> str:
    output = get_last_structured_output(state)

    if output.Need_of_manim.upper() == "YES":
        return "manim_node"

    return END

def route_after_chat(state: ChatState) -> str:
    # 1) If tools are needed → go to tools
    tool_decision = tools_condition(state)
    if tool_decision == "tools":
        return "tools"

    # 2) Try structured output (may not exist yet)
    try:
        output = get_last_structured_output(state)
        if output.Need_of_manim.upper() == "YES":
            return "manim_node"
    except Exception:
        pass

    # 3) Else → we're done
    return END




# -------------------- Graph Builder --------------------

def chat_graph_engine():
    graph = StateGraph(ChatState)

    graph.add_node("chat_node", chat_node)
    graph.add_node("tools", tool_node)
    graph.add_node("manim_node", manim_node)

    graph.add_edge(START, "chat_node")

    #  SINGLE router
    graph.add_conditional_edges(
        "chat_node",
        route_after_chat,
        {
            "tools": "tools",
            "manim_node": "manim_node",
            END: END,
        },
    )

    # after tools → back to chat
    graph.add_edge("tools", "chat_node")

    # after manim → END (not back to chat)
    graph.add_edge("manim_node", END)
    graph.add_edge("tools", END)


    chatbot = graph.compile(checkpointer=checkpointer)
    return chatbot


# -------------------- Thread Utilities --------------------

def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)
