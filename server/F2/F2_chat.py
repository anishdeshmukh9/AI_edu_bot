import os
from pathlib import Path
from typing import TypedDict, List
import sys

from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import logging

# Direct imports without using package structure
import importlib.util

# Get the directory where this file is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Import F2_models
spec = importlib.util.spec_from_file_location("F2_models", os.path.join(current_dir, "F2_models.py"))
F2_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F2_models)
Feature2Input = F2_models.Feature2Input
Feature2Output = F2_models.Feature2Output

# Import F2_ocr_db
spec = importlib.util.spec_from_file_location("F2_ocr_db", os.path.join(current_dir, "F2_ocr_db.py"))
F2_ocr_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F2_ocr_db)
save_ocr_extraction = F2_ocr_db.save_ocr_extraction
get_ocr_extraction = F2_ocr_db.get_ocr_extraction
get_all_ocr_extractions = F2_ocr_db.get_all_ocr_extractions
image_exists_in_chat = F2_ocr_db.image_exists_in_chat

# Import F2_history_db
spec = importlib.util.spec_from_file_location("F2_history_db", os.path.join(current_dir, "F2_history_db.py"))
F2_history_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F2_history_db)
load_history = F2_history_db.load_history
save_message = F2_history_db.save_message

# Import F2_ocr
spec = importlib.util.spec_from_file_location("F2_ocr", os.path.join(current_dir, "F2_ocr.py"))
F2_ocr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F2_ocr)
extract_text_from_image_url = F2_ocr.extract_text_from_image_url

logger = logging.getLogger(__name__)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.4,
)

# Teacher-focused system prompt for OCR doubt solving
SYSTEM_PROMPT = """
You are an expert, patient tutor who helps students solve doubts using images
(handwritten notes, textbook pages, equations, diagrams, derivations, etc.).

Your goal is not just to answer, but to make the student feel:
✔ understood
✔ guided step-by-step
✔ confident after reading the explanation

This system is primarily used on a MOBILE APP, so clarity and structure matter.

━━━━━━━━━━━━━━━━━━━━━━
🎯 YOUR ROLE
━━━━━━━━━━━━━━━━━━━━━━
You analyze OCR-extracted text from one or more uploaded images and explain the
student’s doubt clearly, accurately, and encouragingly.

Students may upload:
- Handwritten notes
- Formula sheets
- Textbook questions
- Diagrams
- Exam problems
- Mixed or noisy images (OCR may be imperfect)

Each image is labeled clearly as:
IMAGE 1, IMAGE 2, IMAGE 3, etc.

━━━━━━━━━━━━━━━━━━━━━━
📚 INFORMATION YOU HAVE
━━━━━━━━━━━━━━━━━━━━━━
- OCR-extracted text from uploaded images only
- The student’s question
- No external context beyond the images

━━━━━━━━━━━━━━━━━━━━━━
✅ HOW TO ANSWER (VERY IMPORTANT)
━━━━━━━━━━━━━━━━━━━━━━

### 1️⃣ UNDERSTAND THE DOUBT FIRST
- Carefully read the student’s question
- Identify which image(s) contain the relevant information
- If multiple images are related, explain how they connect
- If the question is vague, infer intent *only from the images*

Always orient the student:
Example:
“From IMAGE 1, I can see a list of trigonometric identities…”

---

### 2️⃣ EXPLAIN STEP-BY-STEP (MOBILE FRIENDLY)
- Keep paragraphs SHORT (2–4 lines max)
- Prefer numbered steps
- Avoid long dense blocks of text
- Explain *why* each step is done, not just *what*

If solving:
1. State what is given
2. Identify the formula
3. Apply step-by-step
4. Conclude clearly

---

### 3️⃣ FORMULA RENDERING (CRITICAL RULE)
Whenever you write a mathematical formula, equation, or identity:

👉 **You MUST wrap it like this (no exceptions):**

[[formula_start]] formula here [[formula_end]]

Examples:
- [[formula_start]] sin²x + cos²x = 1 [[formula_end]]
- [[formula_start]] sec²x − tan²x = 1 [[formula_end]]
- [[formula_start]] a² + b² = c² [[formula_end]]

❌ Do NOT write formulas outside these markers  
❌ Do NOT partially wrap formulas  
❌ Do NOT skip wrapping even for simple equations

This is required for frontend rendering.

---

### 4️⃣ REFERENCE IMAGES CLEARLY
Always tell the student where information comes from:
- “In IMAGE 1, the formula written is…”
- “IMAGE 2 shows a continuation of the same concept…”
- “The OCR text in IMAGE 1 seems unclear, but based on context…”

This builds **trust**.

---

### 5️⃣ HANDLE OCR ERRORS INTELLIGENTLY
OCR text may be noisy or incorrect.

Rules:
- Use context to infer the correct meaning
- Mention uncertainty when present
- Never invent symbols or values

Example:
“The OCR text shows ‘cosecéx’, which likely means cosec²x based on context.”

---

### 6️⃣ BE ENCOURAGING & STUDENT-FRIENDLY
Your tone should feel like a helpful tutor sitting next to the student.

Use:
- “This is a common confusion”
- “You’re on the right track”
- “Let’s break this down slowly”

End with reassurance or a small takeaway.

---

### 7️⃣ STAY FOCUSED
- Answer exactly what the student asked
- Do not go into unrelated theory
- Do not overload with extra formulas unless helpful

━━━━━━━━━━━━━━━━━━━━━━
❌ STRICT RULES (DO NOT VIOLATE)
━━━━━━━━━━━━━━━━━━━━━━

1. 🚫 NO HALLUCINATION  
   - Use ONLY the OCR text
   - If information is missing, say so clearly

2. 🚫 NO EXTERNAL KNOWLEDGE  
   - Do not bring textbook facts unless present in images

3. 🚫 NO FORMULA WITHOUT TAGS  
   - Every formula MUST be wrapped

4. 🚫 NO ASSUMPTIONS  
   - If something is unclear, acknowledge it

━━━━━━━━━━━━━━━━━━━━━━
📝 FORMATTING RULES (MOBILE OPTIMIZED)
━━━━━━━━━━━━━━━━━━━━━━
- Short paragraphs
- Line breaks between ideas
- Numbered steps for solutions
- Bold keywords sparingly
- Simple language over complex language

━━━━━━━━━━━━━━━━━━━━━━
🎓 FINAL GOAL
━━━━━━━━━━━━━━━━━━━━━━
After reading your answer, the student should feel:
✔ “I understand this now”
✔ “This was explained clearly”
✔ “I can solve similar problems”

Be clear. Be kind. Be accurate.
"""

class ChatState(TypedDict):
    input: Feature2Input
    all_ocr_texts: List[dict]  # List of {image_url, text} for all images in chat
    current_image_url: str
    answer: Feature2Output


def ocr_extraction_node(state: ChatState):
    """Extract OCR text from the current image if not already extracted"""
    i = state["input"]
    image_url = str(i.image_url)
    
    logger.info(f"📸 Processing image for user={i.user_id}, chat={i.chat_id}")
    logger.info(f"🔗 Image URL: {image_url}")
    
    # Check if this image was already processed in this chat
    if image_exists_in_chat(i.user_id, i.chat_id, image_url):
        logger.info("✅ Image already processed, skipping OCR extraction")
        existing_text = get_ocr_extraction(i.user_id, i.chat_id, image_url)
    else:
        logger.info("🔍 New image detected, performing OCR extraction...")
        # Extract text from image
        extracted_text = extract_text_from_image_url(image_url)
        
        # Save extraction to database
        save_ocr_extraction(i.user_id, i.chat_id, image_url, extracted_text)
        logger.info(f"💾 Saved OCR extraction ({len(extracted_text)} chars)")
    
    state["current_image_url"] = image_url
    return state


def context_building_node(state: ChatState):
    """Build context from all images in this chat"""
    i = state["input"]
    
    # Get all OCR extractions for this chat
    all_extractions = get_all_ocr_extractions(i.user_id, i.chat_id)
    
    logger.info(f"📚 Building context from {len(all_extractions)} images in chat")
    
    state["all_ocr_texts"] = all_extractions
    return state


def answer_doubt_node(state: ChatState):
    """Generate answer to student's doubt using OCR context"""
    i = state["input"]
    all_ocr_texts = state["all_ocr_texts"]
    
    # Load chat history for context
    history = load_history(i.user_id, i.chat_id, limit=6)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    
    # Add history (excluding the current question)
    for role, content, images in history:
        if role == "human":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
    
    # Build context from all images
    context_parts = []
    context_parts.append("=" * 60)
    context_parts.append("IMAGES UPLOADED BY STUDENT (OCR EXTRACTED TEXT)")
    context_parts.append("=" * 60)
    context_parts.append("")
    
    referenced_images = []
    for idx, extraction in enumerate(all_ocr_texts, 1):
        context_parts.append(f"📷 IMAGE {idx}: {extraction['image_url']}")
        context_parts.append(f"{'─' * 60}")
        context_parts.append(extraction['extracted_text'])
        context_parts.append("")
        referenced_images.append(extraction['image_url'])
    
    full_context = "\n".join(context_parts)
    
    # Build user prompt
    user_prompt = f"""{full_context}

{'=' * 60}
STUDENT'S DOUBT/QUESTION:
{'=' * 60}
{i.message}

{'=' * 60}
INSTRUCTIONS:
{'=' * 60}
1. Read all the images' OCR text carefully
2. Identify which image(s) are relevant to the student's doubt
3. Provide a clear, thorough explanation/solution
4. Reference specific images when explaining (e.g., "In Image 1...")
5. If solving a problem, show step-by-step work
6. Be encouraging and supportive
7. Focus on helping the student understand

Now, help the student with their doubt:"""
    
    messages.append(HumanMessage(content=user_prompt))
    
    logger.info(f"🤖 Generating answer for doubt: '{i.message[:50]}...'")
    
    # Get LLM response
    answer = llm.invoke(messages).content
    
    logger.info(f"✅ Answer generated ({len(answer)} chars)")
    
    # Save to history (save the current image URL that triggered this question)
    save_message(i.user_id, i.chat_id, "human", i.message, [state["current_image_url"]])
    save_message(i.user_id, i.chat_id, "ai", answer, referenced_images)
    
    # Create output
    state["answer"] = Feature2Output(
        answer=answer,
        referenced_images=referenced_images
    )
    
    return state


# Build the graph
graph = StateGraph(ChatState)
graph.add_node("ocr_extract", ocr_extraction_node)
graph.add_node("build_context", context_building_node)
graph.add_node("answer_doubt", answer_doubt_node)

graph.add_edge(START, "ocr_extract")
graph.add_edge("ocr_extract", "build_context")
graph.add_edge("build_context", "answer_doubt")
graph.add_edge("answer_doubt", END)

ocr_doubt_solver_graph = graph.compile()
