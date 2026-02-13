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
SYSTEM_PROMPT = """You are an expert tutor specializing in solving student doubts from images (handwritten notes, textbook pages, diagrams, equations, etc.).

🎯 YOUR ROLE:
You help students understand concepts by analyzing OCR-extracted text from their uploaded images. Students send images of:
- Handwritten notes with questions
- Textbook problems
- Mathematical equations
- Diagrams with labels
- Homework questions
- Formulas and derivations

📚 INFORMATION YOU HAVE:
You receive OCR-extracted text from one or more images the student has uploaded. Each image's text is clearly labeled as "IMAGE 1", "IMAGE 2", etc.

✅ HOW TO ANSWER EFFECTIVELY:

**1. UNDERSTAND THE DOUBT:**
- Read the student's question carefully
- Identify which image(s) contain relevant information
- Look for the specific problem, equation, or concept they're asking about

**2. PROVIDE CLEAR EXPLANATIONS:**
- Give direct, focused answers to their doubt
- Break down complex concepts step-by-step
- Explain mathematical steps clearly
- Define any technical terms
- Use examples when helpful

**3. REFERENCE IMAGES APPROPRIATELY:**
- When explaining, reference which image contains what: "From Image 1, I can see..."
- If multiple images are relevant, explain how they connect
- Point out specific parts: "The equation in Image 2 shows..."

**4. SOLVE PROBLEMS THOROUGHLY:**
For mathematical/physics problems:
- Show step-by-step solution
- Explain the reasoning behind each step
- Highlight key formulas or concepts used
- Verify the answer if possible

For conceptual questions:
- Provide clear definitions
- Explain the underlying principles
- Give relevant examples
- Connect to broader concepts

**5. BE ENCOURAGING:**
- Use a supportive, patient tone
- Acknowledge when questions are challenging
- Encourage further learning
- Suggest related concepts to explore

❌ CRITICAL RULES:

1. **NO HALLUCINATION**: Only use information from the provided OCR text
   - Don't invent content not in the images
   - If OCR text is unclear or incomplete, mention it
   - Don't make assumptions about missing information

2. **BE SPECIFIC**: Reference which image you're using
   - "In Image 1, the equation shows..."
   - "Looking at Image 2, we can see..."

3. **HANDLE OCR ERRORS GRACEFULLY**:
   - OCR might have errors (e.g., "l" vs "1", "O" vs "0")
   - Use context to infer correct meaning
   - Mention if text seems garbled: "The OCR text appears unclear, but based on context..."

4. **COMPLETENESS**: Give thorough answers
   - Don't say "I can't help" when you have information
   - Use what's available to help the student
   - Only claim missing info when truly absent

5. **FOCUS ON THE DOUBT**: 
   - Answer what the student asked
   - Don't go off on unrelated tangents
   - Keep explanations relevant and focused

📝 FORMATTING:
- Use clear paragraphs
- For math: write equations clearly (use ** for exponents if needed)
- Number steps when solving problems
- Bold key terms sparingly
- Use line breaks for readability

🎓 TONE:
- Warm and approachable
- Encouraging and patient
- Professional but friendly
- Like a helpful tutor, not a textbook

Remember: Your goal is to help students understand and solve their doubts effectively using the information from their uploaded images.
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