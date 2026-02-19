# 🎓 Adyayan AI — Backend

> **AI-Powered Smart Learning Assistant**  
> Helping students truly understand concepts — not just memorize them.

Adyayan AI is an intelligent, personalized learning backend built with **FastAPI**.  
It adapts to each student's thinking level, tracks their learning journey, and provides multimodal, context-aware doubt resolution across text, images, PDFs, and videos.

---

## 🎬 Demo Video


<p align="center">
  <a href="https://www.youtube.com/watch?v=rR6R8H_F24A" target="_blank">
    <img src="https://img.youtube.com/vi/rR6R8H_F24A/0.jpg" width="70%" />
  </a>
</p>

<p align="center">
  ▶️ Click to Watch Full Demo
</p>
*(We host demo on YouTube to maintain repository performance.)*

---

## 🏆 Recognition & Achievements

### 📸 Hackathon & Project Highlights

<p align="center">
  <img src="assets/1000414759.jpg (1).jpeg" width="30%" />
    <img src="assets/SAVE_20260217_210217.jpg.jpeg" width="30%" />

  <img src="assets/1000414760.jpg (1).jpeg" width="30%" />
  <img src="assets/1000414761.jpg (1).jpeg" width="30%" />
</p>

<p align="center">
  <img src="assets/IMG_1860.JPG (1).jpeg" width="30%" />
  <img src="assets/IMG_1896.JPG (1).jpeg" width="30%" />
</p>

---

## 🗂️ Table of Contents

- [Features](#-features)
- [Architecture & Flow](#-architecture--flow)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [API Endpoints](#-api-endpoints)
- [Constraints & Mitigations](#-constraints--mitigations)

---

## ✨ Features

| ID | Feature | Description |
|----|---------|-------------|
| **F1** | 🔍 OCR Doubt Detection | Converts handwritten notes/questions into structured digital text and resolves doubts using AI reasoning |
| **F2** | 📺 YouTube RAG | Extracts key concepts from YouTube videos and answers context-aware queries about the video content |
| **F3** | 💬 Chat Mode with Manim | Step-by-step concept-based doubt resolution with auto-generated Manim visual animations for clarity |
| **F4** | 🎙️ Podcast Generation | Converts learning content and explanations into engaging podcast-style audio summaries |
| **F5** | 🤖 GitGPT Support | AI-powered assistant for understanding and navigating codebases and GitHub repositories |
| **F6** | 📝 Test Generation | Auto-generates quizzes and evaluates answers with detailed feedback using semantic and rubric-based scoring |

---

## 🏗️ Architecture & Flow

```mermaid
graph TD
    A[Student Request] --> B[API Gateway - FastAPI]

    B --> C{MCP / Agent Orchestrator}

    C -->|F1| D[OCR Module]
    C -->|F2| E[YouTube RAG Module]
    C -->|F3| F[Chat + Manim Module]
    C -->|F4| G[Podcast Generator]
    C -->|F5| H[GitGPT Support]
    C -->|F6| I[Test Generator & Evaluator]

    D --> J[Shared Intelligence Engines]
    E --> J
    F --> J
    G --> J
    H --> J
    I --> J

    J --> K[LLM Reasoning Engine]
    J --> L[RAG Engine]
    J --> M[Concept Intelligence]
    J --> N[Student Intelligence]

    K --> O[Response Generation]
    L --> O
    M --> O
    N --> O

    O --> P[Answer / Explanation]
    O --> Q[Animation / Manim Output]
    O --> R[Audio / Podcast Output]
    O --> S[Test & Feedback]

    P --> T[Storage & Memory Layer]
    Q --> T
    R --> T
    S --> T

    T --> U[(MongoDB)]
    T --> V[(Vector Store - FAISS / Chroma)]
    T --> W[Student Memory Profile]

    W --> C
```

### Flow Summary

1. **Student Request** — User sends a query via chat, OCR upload, YouTube link, or selects a mode.
2. **API Gateway** — FastAPI receives and validates the request.
3. **Agent Orchestration** — The MCP/Agent Orchestrator identifies the target feature module and manages context.
4. **Intelligence Processing** — Shared engines (LLM, RAG, Concept Intelligence, Student Intelligence) analyze the input.
5. **Response Generation** — Relevant feature modules produce answers, animations, audio, or test papers.
6. **Storage & Memory Update** — Interaction is persisted; student memory and learning profile are updated for future personalization.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | FastAPI |
| **AI Models** | OpenAI / Gemini / LLaMA |
| **OCR** | Paddleocr / Tesseract |
| **Speech-to-Text** | Whisper |
| **Vector Database** | FAISS, Chroma, Pinecone |
| **Database** | MongoDB, Supabase |
| **Agent Framework** | LangGraph / MCP |
| **Animation** | Manim |
| **Cloud Storage** | AWS S3 / GCS |

---

---


### Running the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: `http://localhost:8000/docs`

---



## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

---

## 📄 License

[MIT](LICENSE)

---

<p align="center">Built with ❤️ by Team WeLoveAgents</p>
