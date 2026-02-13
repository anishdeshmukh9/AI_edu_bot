import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
import logging

logger = logging.getLogger(__name__)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.7,  # Higher temperature for more natural conversation
)

# System prompt for generating podcast script
PODCAST_SCRIPT_PROMPT = """You are a podcast script writer who creates engaging, natural conversations between two hosts discussing educational topics.

**YOUR TASK:**
Generate a podcast script for TWO HOSTS (Alex and Sam) discussing the given topic. The podcast should be:
- Educational yet entertaining
- Natural and conversational (like friends talking)
- 5-10 minutes long when spoken (approximately 1000-2000 words)
- Engaging with questions, examples, and back-and-forth dialogue

**HOSTS:**
- **Alex** (Host 1): More enthusiastic, asks questions, relates concepts to everyday life
- **Sam** (Host 2): More analytical, provides deeper explanations, brings in examples

**SCRIPT FORMAT:**
Write the script EXACTLY in this format:

Alex: [First line of dialogue]
Sam: [Response]
Alex: [Next line]
Sam: [Response]
...

**SCRIPT STRUCTURE:**

1. **INTRODUCTION (15-20% of script)**
   - Alex introduces the topic with enthusiasm
   - Sam adds context or an interesting hook
   - Set expectations for what will be covered

2. **MAIN CONTENT (60-70% of script)**
   - Break the topic into 3-4 key points
   - Use back-and-forth dialogue naturally
   - Include:
     * Questions from Alex
     * Explanations from Sam
     * Real-world examples from both
     * "Aha!" moments
     * Simple analogies
   - Build on each other's points
   - Natural transitions between subtopics

3. **CONCLUSION (10-15% of script)**
   - Sam summarizes key takeaways
   - Alex relates it back to practical application
   - Encouraging closing remarks

**TONE GUIDELINES:**
✅ Natural conversation (use "you know", "actually", "so basically", etc.)
✅ Questions and interruptions (authentic dialogue)
✅ Enthusiasm and curiosity
✅ Simple language (avoid jargon, or explain it if needed)
✅ Personal touches ("I always wondered...", "That reminds me of...")

❌ Don't sound like a lecture or presentation
❌ Don't be overly formal
❌ Don't use complex vocabulary unnecessarily
❌ Don't make it too short (aim for 1000-2000 words)

**EXAMPLE SNIPPET:**

Alex: Hey everyone! Today we're diving into something super cool - quantum entanglement. Sam, I've heard this term thrown around, but honestly, it sounds like science fiction!

Sam: Ha! I get that reaction a lot. But here's the thing - it's real, and it's actually one of the strangest phenomena in physics. So basically, quantum entanglement is when two particles become connected in such a way that the state of one instantly affects the other, no matter how far apart they are.

Alex: Wait, instantly? Like, faster than light?

Sam: Great question! Not quite. It doesn't violate relativity because you can't actually transmit information this way. But the correlation is instant, which is what freaked Einstein out. He called it "spooky action at a distance."

Alex: Okay, so give me a real-world example. How do we know this is actually happening?

[Continue natural back-and-forth...]

**CRITICAL RULES:**
1. Only use "Alex:" and "Sam:" as speaker labels
2. Each line should be conversational length (1-3 sentences typically)
3. Include natural conversation elements (questions, agreements, building on points)
4. Make it educational but not boring
5. Total script should be 1000-2000 words for 5-10 minute podcast

Now, generate a complete podcast script for the given topic following this exact format.
"""


class PodcastScriptState(TypedDict):
    topic: str
    script: str


def generate_script_node(state: PodcastScriptState):
    """Generate podcast script for the topic"""
    topic = state["topic"]
    
    logger.info(f"🎙️ Generating podcast script for topic: '{topic}'")
    
    messages = [
        SystemMessage(content=PODCAST_SCRIPT_PROMPT),
        HumanMessage(content=f"""Generate a complete podcast script for this topic:

TOPIC: {topic}

Remember:
- Natural conversation between Alex and Sam
- 1000-2000 words
- Educational yet engaging
- Use only "Alex:" and "Sam:" format
- 5-10 minutes when spoken

Generate the complete script now:""")
    ]
    
    response = llm.invoke(messages).content
    
    logger.info(f"✅ Script generated ({len(response)} characters)")
    
    state["script"] = response
    return state


# Build the graph
graph = StateGraph(PodcastScriptState)
graph.add_node("generate_script", generate_script_node)

graph.add_edge(START, "generate_script")
graph.add_edge("generate_script", END)

podcast_script_generator = graph.compile()
