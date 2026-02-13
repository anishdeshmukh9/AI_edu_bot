from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from dotenv import load_dotenv
from typing import List
load_dotenv()


# ----------------------------------
# Embedding model (HuggingFace endpoint)
# ----------------------------------
embeddings = HuggingFaceEndpointEmbeddings(
    repo_id="sentence-transformers/all-MiniLM-L6-v2"
)


def create_faiss(docs, persist_dir: str):
    """Create FAISS vector database from documents"""
    db = FAISS.from_documents(docs, embeddings)
    db.save_local(persist_dir)
    return db


def load_faiss(persist_dir: str):
    """Load FAISS vector database"""
    return FAISS.load_local(
        persist_dir,
        embeddings,
        allow_dangerous_deserialization=True,
    )


def retrieve_with_priority(db, query: str, k: int = 12) -> List[Document]:
    """
    Retrieve documents with priority given to transcript over OCR.
    Returns more transcript documents than OCR documents.
    """
    # Get more documents initially
    all_docs = db.similarity_search(query, k=k * 2)
    
    # Separate by source
    transcript_docs = [d for d in all_docs if d.metadata.get("source") == "speech"]
    ocr_docs = [d for d in all_docs if d.metadata.get("source") == "visual"]
    
    # Prioritize transcript: ~70% transcript, ~30% OCR
    transcript_count = int(k * 0.7)
    ocr_count = k - transcript_count
    
    selected_transcript = transcript_docs[:transcript_count]
    selected_ocr = ocr_docs[:ocr_count]
    
    # If we don't have enough of one type, fill with the other
    if len(selected_transcript) < transcript_count and len(ocr_docs) > ocr_count:
        additional = transcript_count - len(selected_transcript)
        selected_ocr = ocr_docs[:ocr_count + additional]
    elif len(selected_ocr) < ocr_count and len(transcript_docs) > transcript_count:
        additional = ocr_count - len(selected_ocr)
        selected_transcript = transcript_docs[:transcript_count + additional]
    
    return selected_transcript + selected_ocr