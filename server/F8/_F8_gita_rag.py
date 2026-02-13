"""
Optimized Bhagavad Gita RAG System with ChromaDB

Key Improvements:
1. ChromaDB for better performance and persistence
2. Intelligent document splitting based on verse structure
3. Rich metadata extraction for better retrieval
4. Semantic chunking for coherent context
"""

import os
import json
import logging
import tempfile
import requests
import re
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv
load_dotenv()

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata  # FIX: Added import

logger = logging.getLogger(__name__)

# -------------------------------------------------
# ENV CONFIG
# -------------------------------------------------

GITA_PDF_SUPABASE_URL = os.getenv("GITA_PDF_SUPABASE_URL")

if not GITA_PDF_SUPABASE_URL:
    raise RuntimeError("GITA_PDF_SUPABASE_URL not set in environment variables")

# -------------------------------------------------
# PATHS
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
CHROMA_PERSIST_DIR = BASE_DIR / "f8_gita_chroma_db"
GITA_METADATA_PATH = BASE_DIR / "f8_gita_metadata.json"

# -------------------------------------------------
# EMBEDDINGS
# -------------------------------------------------

embeddings = HuggingFaceEndpointEmbeddings(
    repo_id="sentence-transformers/all-MiniLM-L6-v2"
)

# -------------------------------------------------
# INTELLIGENT VERSE PARSER
# -------------------------------------------------

class GitaVerseParser:
    """
    Intelligent parser for Bhagavad Gita structure
    Identifies chapters, verses, and extracts rich metadata
    """
    
    # Patterns for identifying Gita structure
    CHAPTER_PATTERN = re.compile(r'Chapter\s+(\d+)', re.IGNORECASE)
    VERSE_PATTERN = re.compile(r'(?:Verse|Text)\s+(\d+)', re.IGNORECASE)
    SANSKRIT_PATTERN = re.compile(r'[\u0900-\u097F]+')  # Devanagari script
    
    @staticmethod
    def extract_chapter(text: str) -> Optional[int]:
        """Extract chapter number from text"""
        match = GitaVerseParser.CHAPTER_PATTERN.search(text)
        return int(match.group(1)) if match else None
    
    @staticmethod
    def extract_verse(text: str) -> Optional[int]:
        """Extract verse number from text"""
        match = GitaVerseParser.VERSE_PATTERN.search(text)
        return int(match.group(1)) if match else None
    
    @staticmethod
    def has_sanskrit(text: str) -> bool:
        """Check if text contains Sanskrit/Devanagari"""
        return bool(GitaVerseParser.SANSKRIT_PATTERN.search(text))
    
    @staticmethod
    def extract_themes(text: str) -> str:  # FIX: Changed return type from List[str] to str
        """Extract thematic keywords from verse text as comma-separated string"""
        # Common Gita themes
        theme_keywords = {
            'karma': ['karma', 'action', 'work', 'duty'],
            'dharma': ['dharma', 'righteousness', 'duty', 'moral'],
            'yoga': ['yoga', 'discipline', 'union', 'practice'],
            'knowledge': ['knowledge', 'wisdom', 'jnana', 'understanding'],
            'devotion': ['devotion', 'bhakti', 'love', 'worship'],
            'detachment': ['detachment', 'renunciation', 'equanimity'],
            'self': ['self', 'atman', 'soul', 'consciousness'],
            'supreme': ['supreme', 'divine', 'krishna', 'god'],
            'mind': ['mind', 'senses', 'control', 'meditation'],
            'results': ['results', 'fruits', 'attachment', 'desire']
        }
        
        text_lower = text.lower()
        found_themes = []
        
        for theme, keywords in theme_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                found_themes.append(theme)
        
        # FIX: Return comma-separated string instead of list
        return ', '.join(found_themes) if found_themes else 'general'

# -------------------------------------------------
# ADVANCED DOCUMENT PROCESSOR
# -------------------------------------------------

class GitaDocumentProcessor:
    """
    Advanced processor for Gita documents
    Creates semantically coherent chunks with rich metadata
    """
    
    def __init__(self):
        # Recursive splitter for better semantic coherence
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            is_separator_regex=False
        )
        self.parser = GitaVerseParser()
    
    def process_documents(self, raw_docs: List[Document]) -> List[Document]:
        """
        Process raw PDF documents into optimized chunks
        
        Args:
            raw_docs: Raw documents from PDF loader
            
        Returns:
            List of processed documents with rich metadata
        """
        processed_docs = []
        current_chapter = None
        current_verse = None
        
        logger.info(f"📚 Processing {len(raw_docs)} raw documents...")
        
        for doc in raw_docs:
            # Track chapter context
            chapter = self.parser.extract_chapter(doc.page_content)
            if chapter:
                current_chapter = chapter
            
            # Track verse context
            verse = self.parser.extract_verse(doc.page_content)
            if verse:
                current_verse = verse
            
            # Split into semantic chunks
            chunks = self.text_splitter.split_documents([doc])
            
            # Enhance each chunk with metadata
            for chunk in chunks:
                # Preserve original metadata
                enhanced_metadata = {
                    **chunk.metadata,
                    'chapter': current_chapter or 0,
                    'verse': current_verse or 0,
                    'has_sanskrit': self.parser.has_sanskrit(chunk.page_content),
                    'themes': self.parser.extract_themes(chunk.page_content),  # FIX: Now returns string
                    'chunk_size': len(chunk.page_content),
                }
                
                # Create enhanced document
                enhanced_doc = Document(
                    page_content=chunk.page_content,
                    metadata=enhanced_metadata
                )
                processed_docs.append(enhanced_doc)
        
        logger.info(f"✅ Created {len(processed_docs)} optimized chunks")
        
        # Log statistics
        chapters_found = set(d.metadata.get('chapter', 0) for d in processed_docs if d.metadata.get('chapter', 0) > 0)
        logger.info(f"📖 Found content from {len(chapters_found)} chapters")
        
        return processed_docs

# -------------------------------------------------
# PDF DOWNLOAD + PARSE
# -------------------------------------------------

def download_and_parse_gita_pdf() -> List[Document]:
    """Download Bhagavad Gita PDF from Supabase and parse it"""
    logger.info("📥 Downloading Bhagavad Gita PDF from Supabase...")

    response = requests.get(GITA_PDF_SUPABASE_URL, timeout=60)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(response.content)
        pdf_path = tmp_file.name

    logger.info("📄 Parsing Bhagavad Gita PDF with PyPDFLoader...")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    logger.info(f"✅ Parsed {len(documents)} pages from Bhagavad Gita")
    
    # Cleanup
    try:
        os.remove(pdf_path)
    except:
        pass

    return documents

# -------------------------------------------------
# VECTORIZE WITH CHROMADB
# -------------------------------------------------

def vectorize_gita_once() -> Chroma:
    """
    One-time vectorization of Bhagavad Gita with ChromaDB
    """
    if CHROMA_PERSIST_DIR.exists():
        logger.warning("⚠️  ChromaDB collection already exists. Loading existing index.")
        return load_gita_index()

    logger.info("🕉️  Starting Bhagavad Gita vectorization with ChromaDB...")

    # Download and parse PDF
    raw_documents = download_and_parse_gita_pdf()
    
    # Process documents with intelligent splitting
    processor = GitaDocumentProcessor()
    processed_documents = processor.process_documents(raw_documents)

    # FIX: Filter complex metadata before creating ChromaDB
    logger.info("🔧 Filtering complex metadata for ChromaDB compatibility...")
    filtered_documents = filter_complex_metadata(processed_documents)
    
    logger.info("🔮 Creating ChromaDB vector store...")
    
    # Create ChromaDB collection
    vectorstore = Chroma.from_documents(
        documents=filtered_documents,  # FIX: Use filtered documents
        embedding=embeddings,
        persist_directory=str(CHROMA_PERSIST_DIR),
        collection_name="bhagavad_gita"
    )

    # Save metadata
    with open(GITA_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source": GITA_PDF_SUPABASE_URL,
                "total_pages": len(raw_documents),
                "total_chunks": len(processed_documents),
                "vectorized": True,
                "database": "ChromaDB"
            },
            f,
            indent=2
        )

    logger.info("✅ Bhagavad Gita vectorization completed successfully")
    return vectorstore

# -------------------------------------------------
# LOAD INDEX
# -------------------------------------------------

def load_gita_index() -> Chroma:
    """Load existing ChromaDB index"""
    if not CHROMA_PERSIST_DIR.exists():
        raise FileNotFoundError(
            "Gita ChromaDB not found. Run vectorize_gita_once() first."
        )

    logger.info("📖 Loading Bhagavad Gita ChromaDB collection...")
    return Chroma(
        persist_directory=str(CHROMA_PERSIST_DIR),
        embedding_function=embeddings,
        collection_name="bhagavad_gita"
    )

# -------------------------------------------------
# ADVANCED SEARCH WITH FILTERING
# -------------------------------------------------

def search_gita(
    query: str,
    k: int = 5,
    chapter_filter: Optional[int] = None,
    theme_filter: Optional[str] = None
) -> List[Document]:
    """
    Advanced search with optional filtering
    
    Args:
        query: Search query
        k: Number of results
        chapter_filter: Optional chapter number to filter by
        theme_filter: Optional theme to filter by
    
    Returns:
        List of relevant documents
    """
    logger.info(f"🔎 Searching Gita for: {query[:60]}...")
    
    vectorstore = load_gita_index()
    
    # Build filter dictionary
    filter_dict = {}
    if chapter_filter:
        filter_dict["chapter"] = chapter_filter
    # FIX: Since themes is now a string, we can't use $contains
    # We'll skip theme filtering in metadata and rely on semantic search
    
    # Search with optional filtering
    if filter_dict:
        results = vectorstore.similarity_search(
            query, 
            k=k,
            filter=filter_dict
        )
    else:
        results = vectorstore.similarity_search(query, k=k)

    logger.info(f"✅ Found {len(results)} relevant passages")
    
    # Log what was found
    for i, doc in enumerate(results, 1):
        chapter = doc.metadata.get('chapter', 'N/A')
        verse = doc.metadata.get('verse', 'N/A')
        themes = doc.metadata.get('themes', 'N/A')
        logger.info(f"  {i}. Ch {chapter}, V {verse} | Themes: {themes}")
    
    return results

# -------------------------------------------------
# HYBRID SEARCH (SEMANTIC + KEYWORD)
# -------------------------------------------------

def hybrid_search_gita(query: str, k: int = 5) -> List[Document]:
    """
    Hybrid search combining semantic similarity and keyword matching
    """
    logger.info(f"🔬 Performing hybrid search for: {query[:60]}...")
    
    vectorstore = load_gita_index()
    
    # Get semantic results
    semantic_results = vectorstore.similarity_search(query, k=k*2)
    
    # Keyword boost: prioritize results with query terms
    query_terms = set(query.lower().split())
    
    scored_results = []
    for doc in semantic_results:
        content_lower = doc.page_content.lower()
        # Count keyword matches
        keyword_score = sum(1 for term in query_terms if term in content_lower)
        scored_results.append((keyword_score, doc))
    
    # Sort by keyword score (descending) and take top k
    scored_results.sort(key=lambda x: x[0], reverse=True)
    final_results = [doc for _, doc in scored_results[:k]]
    
    logger.info(f"✅ Hybrid search returned {len(final_results)} results")
    
    return final_results

# -------------------------------------------------
# ENSURE INDEX EXISTS
# -------------------------------------------------

def ensure_gita_index_exists():
    """Ensure ChromaDB index exists (create if missing)"""
    if not CHROMA_PERSIST_DIR.exists():
        logger.warning("⚠️  Gita index missing. Creating now...")
        vectorize_gita_once()
    else:
        logger.info("✅ Gita ChromaDB already exists")

# -------------------------------------------------
# GET SPECIFIC VERSE
# -------------------------------------------------

def get_verse(chapter: int, verse: int) -> Optional[Document]:
    """
    Retrieve a specific verse by chapter and verse number
    """
    logger.info(f"📿 Fetching Chapter {chapter}, Verse {verse}")
    
    vectorstore = load_gita_index()
    
    results = vectorstore.similarity_search(
        f"chapter {chapter} verse {verse}",
        k=1,
        filter={"chapter": chapter, "verse": verse}
    )
    
    return results[0] if results else None