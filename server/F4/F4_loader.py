import requests
import tempfile
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_and_split(pdf_url: str):
    r = requests.get(pdf_url)
    r.raise_for_status()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(r.content)
        pdf_path = f.name

    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
    )

    return splitter.split_documents(docs)