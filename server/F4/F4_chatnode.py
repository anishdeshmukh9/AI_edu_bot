import os
import uuid
from pathlib import Path
from typing import TypedDict, List

from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from F4.F4_models import Feature4Input, Feature4Output
from F4.F4_meta_db import is_indexed, mark_indexed
from F4.F4_history_db import load_history, save_message
from F4.F4_loader import load_and_split
from F4.F4_vector import get_vectorstore
from F4.F4_tools import youtube_search


llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

SYSTEM_PROMPT = """
You are an expert AI tutor and teacher.

Your role is to explain topics clearly, deeply, and intuitively to a student,
using the provided PDF context as the primary grounding source.

You are allowed and encouraged to use your own general knowledge to:
- simplify explanations
- add intuition
- give real-world analogies
- fill small conceptual gaps

However, your final answer MUST remain aligned with the PDF and its meaning.
Never contradict the PDF.
If the PDF is clearly wrong or incomplete, gently say so and explain the correct idea.

----------------------------------------
GROUNDING RULES
----------------------------------------
- Always use the provided PDF context as your main reference.
- Base your core explanation on what the PDF says.
- When you enrich with your own knowledge, keep it consistent with the PDF.
- If something is truly not present in the PDF and cannot be inferred safely,
  say: "This is not explicitly mentioned in the PDF, but in general..."

----------------------------------------
PAGE NUMBER RULES
----------------------------------------
- Your explanation must align with the referenced page numbers.
- Do NOT invent page numbers.
- When stating a fact that comes from the PDF, phrase it like:
  "According to the PDF (Page X), ..."

----------------------------------------
TOOL USAGE RULES
----------------------------------------
- For every major conceptual doubt, explanation request, or definition request:
  you MUST assume that:
  1) PDF context is your primary source
  2) YouTube search will be used by the system to recommend videos

So structure your explanation as if a student may also watch a video after.

----------------------------------------
FORMATTING RULES (VERY IMPORTANT)
----------------------------------------
- Use \\n for every line break.
- Use \\\\n for every paragraph break.

- If you write a formula, enclose it in:
  [[formula]] like this:
  [[formula]] a^2 + b^2 = c^2 [[formula]]

- If you write code, enclose it in:
  [[code]] ... [[code]]

- Do NOT use Markdown.
- Do NOT use bullet symbols like • or - .
- Use simple numbered points only if absolutely necessary.

----------------------------------------
STYLE RULES
----------------------------------------
- Explain like a great teacher, not like a textbook.
- Start from intuition, then go to definition, then to example.
- Keep the language simple and student-friendly.
- Avoid unnecessary jargon unless the PDF uses it.

----------------------------------------
HALLUCINATION POLICY (CONTROLLED)
----------------------------------------
- You are allowed to go slightly beyond the PDF to improve understanding.
- You may introduce missing but standard facts about the topic.
- But you must clearly signal when you do so by saying:
  "This is general knowledge beyond the PDF..."

----------------------------------------
FAIL-SAFE RULE
----------------------------------------
If the provided context is insufficient to answer properly:
- Say what is missing.
- Give a partial explanation.
- Ask the student a clarifying question.

----------------------------------------
Your goal:
Make the student truly understand the topic,
not just repeat what the PDF says.


IMPORTANT :- ANSWER SHOULD BE LESS THAN 100 WORDS
"""

class ChatState(TypedDict):
    input: Feature4Input
    vector_dir: str
    context: str
    pages: List[int]
    answer: Feature4Output


def ingest_node(state: ChatState):
    data = state["input"]

    base_dir = Path("./chroma_store") / data.user_id / data.chat_id
    base_dir.mkdir(parents=True, exist_ok=True)

    vector_dir = is_indexed(data.user_id, data.chat_id, str(data.pdf_url))

    if not vector_dir:
        docs = load_and_split(str(data.pdf_url))

        # ---------- HARD VALIDATION (PERMANENT FIX) ----------
        if not docs or len(docs) == 0:
            raise ValueError(
                "PDF ingestion failed: No text could be extracted from the PDF. "
                "The PDF may be empty, scanned, or unsupported."
            )

        valid_docs = []
        for d in docs:
            if d.page_content and d.page_content.strip():
                valid_docs.append(d)

        if not valid_docs:
            raise ValueError(
                "PDF ingestion failed: Extracted documents contain no usable text."
            )
        # ----------------------------------------------------

        vector_dir = str(base_dir / str(uuid.uuid4()))
        vs = get_vectorstore(vector_dir)

        # This call is now GUARANTEED SAFE
        vs.add_documents(valid_docs)

        mark_indexed(
            data.user_id,
            data.chat_id,
            str(data.pdf_url),
            vector_dir
        )

    state["vector_dir"] = vector_dir
    return state

def retrieve_node(state: ChatState):
    data = state["input"]
    vs = get_vectorstore(state["vector_dir"])

    docs = vs.similarity_search(data.message, k=4)

    context_blocks = []
    pages = []

    for d in docs:
        page = d.metadata.get("page", None)
        if page is not None:
            pages.append(page + 1)  # human-friendly
        context_blocks.append(f"(Page {page + 1}) {d.page_content}")

    state["context"] = "\n".join(context_blocks)
    state["pages"] = sorted(list(set(pages)))
    return state


def generate_node(state: ChatState):
    data = state["input"]

    history_rows = load_history(data.user_id, data.chat_id, limit=8)
    history_msgs = []

    for role, content in history_rows:
        if role == "human":
            history_msgs.append(HumanMessage(content=content))
        else:
            history_msgs.append(AIMessage(content=content))

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *history_msgs,
        HumanMessage(
            content=f"""
Relevant PDF Context:
{state['context']}

Current Question:
{data.message}
"""
        ),
    ]

    resp = llm.invoke(messages).content

    yt_links = youtube_search(data.message)

    out = Feature4Output(
        title="Answer from PDF",
        body=resp,
        pages=state["pages"],
        youtube_links=yt_links,
        next_related_topic=["Revise this section", "Explore related chapter"],
        next_questions=["Explain in simple words", "Give a real example"],
    )

    save_message(data.user_id, data.chat_id, "human", data.message)
    save_message(data.user_id, data.chat_id, "ai", resp)

    state["answer"] = out
    return state


graph = StateGraph(ChatState)

graph.add_node("ingest", ingest_node)
graph.add_node("retrieve", retrieve_node)
graph.add_node("generate", generate_node)

graph.add_edge(START, "ingest")
graph.add_edge("ingest", "retrieve")
graph.add_edge("retrieve", "generate")
graph.add_edge("generate", END)

pdf_rag_graph = graph.compile()