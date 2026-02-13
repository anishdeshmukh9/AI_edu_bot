import os
import re
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from F5.F5_models import Feature5Input, Feature5Output
from F5.F5_meta_db import get_index, save_index
from F5.F5_ingest import ingest_video
from F5.F5_vector import load_faiss, retrieve_with_priority
from F5.F5_history_db import load_history, save_message
from F5.F5_transcript import load_transcript

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3,  # Slightly higher for more natural explanations
)

# Enhanced teacher-focused system prompt
SYSTEM_PROMPT = """You are an enthusiastic and knowledgeable teacher who LOVES to explain concepts in detail. Your goal is to help students truly understand the material, not just answer questions briefly.

🎓 YOUR TEACHING PHILOSOPHY:
- You believe in thorough, comprehensive explanations
- You break down complex topics into digestible parts
- You use examples, analogies, and step-by-step reasoning
- You connect concepts to help students see the bigger picture
- You're patient and encouraging, never dismissive

📚 INFORMATION YOU HAVE ACCESS TO:
You have TWO types of information from educational videos:

1. **[Timestamp - Speech]** = What the instructor SAID (spoken words, verbal explanations)
   → This is PRIMARY and more reliable for understanding concepts

2. **[Timestamp - Screen]** = What appeared ON SCREEN (formulas, diagrams, equations, written text)
   → This is SUPPLEMENTARY visual content that supports the explanation

⚖️ HOW TO USE THESE SOURCES:
- **Prioritize Speech**: The instructor's verbal explanation is your main source
- **Support with Screen**: Use screen content (formulas, diagrams) to enhance your explanation
- **Cross-verify**: When screen shows a formula and speech explains it, combine both
- **Be explicit**: Tell students "The instructor explained..." or "On screen, we can see..."

🎯 HOW TO RESPOND TO DIFFERENT QUESTIONS:

**1. CONCEPT EXPLANATION (Most Common)**
When students ask "Explain X", "What is Y?", "How does Z work?", "Why...":

✅ DO THIS:
- Give a THOROUGH, DETAILED explanation (aim for 8-15 sentences)
- Start with the core concept, then build layers of understanding
- Use the instructor's verbal explanation as your foundation
- Incorporate formulas/diagrams from screen when they add clarity
- Add context: "This concept is important because..."
- Include examples if they help understanding
- End with a key takeaway or connection to broader topics

✅ STRUCTURE YOUR EXPLANATION LIKE THIS:
1. Core definition/concept (2-3 sentences)
2. Detailed breakdown (4-6 sentences)
3. Supporting details from screen content (2-3 sentences)
4. Practical meaning or application (1-2 sentences)
5. Key insight or connection (1 sentence)

❌ DON'T DO THIS:
- Give 2-3 sentence surface-level answers
- Just list what was said without explaining
- Provide generic knowledge not from the video
- Be overly concise when detail would help

**2. TIMESTAMP-SPECIFIC QUESTIONS**
When asked "What happens at 2:30?" or "What's on screen at 1:45?":

✅ DO THIS:
- Report exactly what was said/shown at that timestamp
- Keep it focused but complete (3-5 sentences)
- If asked to explain what's at the timestamp, still provide thorough explanation
- Include both speech and screen content from that moment

**3. VERIFICATION QUESTIONS**
When asked "Is this formula correct?" or "Did the instructor say X?":

✅ DO THIS:
- Compare what student said vs. what's in your sources
- Answer clearly: "Yes, that's correct because..." or "Not exactly, the instructor said..."
- Explain the correct version thoroughly (4-6 sentences)
- Cross-check speech vs. screen for accuracy

**4. FORMULA/EQUATION QUESTIONS**
When asked about mathematical formulas or equations:

✅ DO THIS:
- State the exact formula from screen content
- Explain each component: "where X represents..., Y represents..."
- Describe what the formula calculates or represents
- Explain when/why it's used (if mentioned in speech)
- Walk through the logic or derivation if explained in the video (6-10 sentences total)

❌ DON'T DO THIS:
- Just state the formula without explanation
- Invent formulas not shown in the source material

🚫 CRITICAL RULES - NEVER BREAK THESE:

1. **NO HALLUCINATION**: Only use information from the provided sources
   - Don't invent formulas, facts, or details not in the video
   - If something isn't covered, say: "This specific detail wasn't covered in this part of the video, but based on what was explained..."

2. **NO GENERIC FILLER**: Don't give textbook definitions if the video doesn't cover it
   - Every explanation should be grounded in what the instructor actually taught

3. **NO LAZY SUMMARIES**: Avoid responses like:
   - "The video explains that X is important" (too vague)
   - "The instructor discusses Y" (what did they actually say?)
   - "Various concepts are covered" (be specific)

4. **BE COMPLETE**: Don't say "I don't have enough information" when you DO have information
   - Use what you have and explain thoroughly
   - Only claim missing info when truly absent from sources

✨ YOUR TONE:
- Warm and encouraging
- Enthusiastic about the subject
- Patient and thorough
- Like a passionate teacher who wants students to really "get it"
- Conversational but educational

📝 FORMATTING:
- Write in clear paragraphs, not bullet points (unless listing distinct items)
- Use natural transitions between ideas
- Bold key terms sparingly for emphasis
- Include timestamps when referencing specific moments: "At 2:34, the instructor explained..."

🎓 REMEMBER: 
You're not a search engine returning snippets. You're a TEACHER who:
- Explains thoroughly because understanding matters
- Takes time to break things down
- Connects ideas to help students learn
- Sees every question as an opportunity to teach something valuable

Your mission: Help students truly understand, not just get quick answers.
"""


class ChatState(TypedDict):
    input: Feature5Input
    faiss_dir: str
    video_id: str
    answer: Feature5Output


def ingest_node(state: ChatState):
    i = state["input"]
    base = Path("./f5_store") / i.user_id / i.chat_id
    base.mkdir(parents=True, exist_ok=True)

    # Extract video_id for later use
    youtube_url = str(i.youtube_url)
    if "youtu.be/" in youtube_url:
        video_id = youtube_url.split("youtu.be/")[1].split("?")[0]
    else:
        video_id = youtube_url.split("v=")[1].split("&")[0]
    
    state["video_id"] = video_id

    faiss_dir = get_index(i.user_id, i.chat_id, str(i.youtube_url))
    if not faiss_dir:
        faiss_dir = ingest_video(str(i.youtube_url), base)
        save_index(i.user_id, i.chat_id, str(i.youtube_url), faiss_dir)

    state["faiss_dir"] = faiss_dir
    return state


def extract_timestamp(message: str):
    """
    Extract timestamp from messages like:
    - "What is discussed at 2:01?"
    - "what is on the screen on 3:11"
    - "Explain the formula at 2:45"
    Returns timestamp in seconds or None
    """
    patterns = [
        r'at\s+(\d{1,2}):(\d{2})',  # "at 2:01"
        r'on\s+(\d{1,2}):(\d{2})',  # "on 3:11"
        r'@\s*(\d{1,2}):(\d{2})',   # "@ 2:01"
        r'(\d{1,2}):(\d{2})',       # "2:01"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            return minutes * 60 + seconds
    
    return None


def get_transcript_context(video_id: str, timestamp: float = None, window: int = 45):
    """
    Get transcript context with clear timestamp markers.
    Increased window for more context.
    """
    transcript = load_transcript(video_id)
    
    if not transcript:
        return ""
    
    if timestamp is not None:
        relevant_lines = []
        for t in transcript:
            t_start = t["start"]
            t_end = t["end"]
            if (t_start >= timestamp - window and t_start <= timestamp + window) or \
               (t_end >= timestamp - window and t_end <= timestamp + window):
                mins = int(t_start) // 60
                secs = int(t_start) % 60
                relevant_lines.append(f"[{mins}:{secs:02d} - Speech] {t['text']}")
        
        return "\n".join(relevant_lines) if relevant_lines else ""
    else:
        lines = []
        for t in transcript:
            mins = int(t['start']) // 60
            secs = int(t['start']) % 60
            lines.append(f"[{mins}:{secs:02d} - Speech] {t['text']}")
        return "\n".join(lines)


def rag_node(state: ChatState):
    i = state["input"]
    video_id = state["video_id"]
    
    # Check if message contains a timestamp
    timestamp = extract_timestamp(i.message)
    
    # Get vector database
    db = load_faiss(state["faiss_dir"])
    
    # Retrieve relevant documents with transcript priority
    docs = retrieve_with_priority(db, i.message, k=15)  # Increased for more context
    
    # Separate transcript and OCR content
    transcript_docs = [d for d in docs if d.metadata.get("source") == "speech"]
    ocr_docs = [d for d in docs if d.metadata.get("source") == "visual"]
    
    # Build transcript context (prioritized)
    if timestamp is not None:
        transcript_context = get_transcript_context(video_id, timestamp, window=45)
    else:
        # Use retrieved transcript docs
        transcript_lines = []
        for d in transcript_docs:
            start = d.metadata['start']
            mins = int(start) // 60
            secs = int(start) % 60
            transcript_lines.append(f"[{mins}:{secs:02d} - Speech] {d.page_content}")
        transcript_context = "\n".join(transcript_lines)
    
    # Build OCR context (supplementary)
    ocr_lines = []
    for d in ocr_docs:
        start = d.metadata['start']
        mins = int(start) // 60
        secs = int(start) % 60
        ocr_lines.append(f"[{mins}:{secs:02d} - Screen] {d.page_content}")
    ocr_context = "\n".join(ocr_lines)
    
    # If timestamp-specific question, also get OCR at that specific time
    if timestamp is not None and ocr_docs:
        timestamp_ocr = []
        for d in ocr_docs:
            start = d.metadata['start']
            end = d.metadata.get('end', start + 8)
            if start <= timestamp <= end or abs(start - timestamp) <= 45:
                mins = int(start) // 60
                secs = int(start) % 60
                timestamp_ocr.append(f"[{mins}:{secs:02d} - Screen] {d.page_content}")
        
        if timestamp_ocr:
            ocr_context = "\n".join(timestamp_ocr)
    
    # Check if we have any context
    has_context = bool(transcript_context.strip() or ocr_context.strip())
    
    if not has_context:
        answer = "I don't have information about that topic from this video. The video content I have access to doesn't seem to cover this particular question. Could you try asking about a different topic from the video, or let me know if you'd like me to explain what topics are covered?"
        state["answer"] = Feature5Output(answer=answer, timestamps=[])
        return state
    
    # Load chat history for context
    history = load_history(i.user_id, i.chat_id, limit=8)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    
    # Add history
    for role, content in history:
        if role == "human":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
    
    # Build comprehensive context with SPEECH prioritized
    context_parts = []
    
    # SPEECH FIRST (Primary source)
    if transcript_context.strip():
        context_parts.append("=== PRIMARY SOURCE: WHAT THE INSTRUCTOR SAID (VERBAL EXPLANATION) ===")
        context_parts.append(transcript_context)
        context_parts.append("")  # Blank line for separation
    
    # SCREEN SECOND (Supplementary source)
    if ocr_context.strip():
        context_parts.append("=== SUPPLEMENTARY SOURCE: WHAT'S ON THE SCREEN (VISUAL CONTENT) ===")
        context_parts.append(ocr_context)
    
    full_context = "\n".join(context_parts)
    
    # Build user prompt that encourages thorough explanation
    user_prompt = f"""Here is the content from the educational video:

{full_context}

Student's Question: {i.message}

Remember:
- Provide a THOROUGH, DETAILED explanation (aim for 8-15 sentences for concept questions)
- The instructor's verbal explanation (Speech) is your PRIMARY source
- Screen content (formulas, diagrams) SUPPORTS the explanation
- Break down complex ideas step-by-step
- Help the student truly understand, don't just summarize
- Be specific about what the instructor said and what appeared on screen
- If this is a concept question, teach it comprehensively
- If this is a timestamp question, be precise but complete
- Include relevant timestamps when referencing specific moments

Now, teach this concept thoroughly:"""
    
    messages.append(HumanMessage(content=user_prompt))
    
    # Get LLM response
    answer = llm.invoke(messages).content
    
    # Save to history
    save_message(i.user_id, i.chat_id, "human", i.message)
    save_message(i.user_id, i.chat_id, "ai", answer)
    
    # Extract timestamps from all used documents
    all_docs = transcript_docs + ocr_docs
    timestamps = []
    for d in all_docs:
        start = d.metadata['start']
        mins = int(start) // 60
        secs = int(start) % 60
        timestamps.append(f"{mins}:{secs:02d}")
    
    timestamps = sorted(set(timestamps))
    
    state["answer"] = Feature5Output(
        answer=answer,
        timestamps=timestamps[:10],  # Return top 10 most relevant timestamps
    )
    return state


# Build the graph
graph = StateGraph(ChatState)
graph.add_node("ingest", ingest_node)
graph.add_node("rag", rag_node)

graph.add_edge(START, "ingest")
graph.add_edge("ingest", "rag")
graph.add_edge("rag", END)

video_rag_graph = graph.compile()