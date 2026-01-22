from fastapi import FastAPI
from chat import chat_graph_egine

app = FastAPI(title="AI Backend API", version="1.0.0")


@app.get("/chat")
def chat():
    # Feature 1, 6
    chatbot = chat_graph_egine()
    return {"working": chatbot}


@app.get("/ocr")
def ocr():
    # Feature 2
    return {"working": True}


@app.post("/pdf_ingest")
def pdf_ingest():
    # Feature 4
    return {"working": True}


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
