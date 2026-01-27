from fastapi import FastAPI
from chat import chat_graph_engine
from langchain_core.messages import HumanMessage 
from pydantic_models import feature1_6
from fastapi.middleware.cors import CORSMiddleware

# feature 4 pdf rag. 
from F4.F4_chatnode import pdf_rag_graph
from F4.F4_models import Feature4Input
from F4.F4_history_db import load_full_history


app = FastAPI(title="AI Backend API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins. For production, specify: ["http://localhost:3000", "https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)
@app.post("/chat")
def chat(obj : feature1_6):
    # Feature 1, 6
    chatbot = chat_graph_engine()
    config = {"configurable":{"thread_id" : obj.chat_id}}
    return {"working": chatbot.invoke({"messages" : HumanMessage(content=obj.message)} , config=config )}


@app.get("/ocr")
def ocr():
    # Feature 2
    return {"working": True}



@app.post("/pdf_ingest")
def pdf_ingest(data: Feature4Input):
    state = {"input": data}
    result = pdf_rag_graph.invoke(state)

    history = load_full_history(data.user_id, data.chat_id)

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


@app.post("/youtube_ingest")
def youtube_ingest():
    # Feature 5
    return {"working": True}


@app.get("/test_generate")
def test_generate():
    # Feature 9
    return {"working": True}


@app.get("/video_tutor")
def video_tutor():
    # Feature 7
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
