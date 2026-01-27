from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from dotenv import load_dotenv
load_dotenv()


# ----------------------------------
# Embedding model (HuggingFace endpoint)
# ----------------------------------
embeddings = HuggingFaceEndpointEmbeddings(
    repo_id="sentence-transformers/all-MiniLM-L6-v2"
)

def get_vectorstore(persist_dir: str):
    return Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
    )