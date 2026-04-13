"""
2A2026000999 - LE HUY HONG NHAT
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DOCS_DIR = os.getenv("DOCS_DIR", "./data/docs")
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
    BM25_INDEX_DIR = os.getenv("BM25_INDEX_DIR", "./data/bm25_index")
    EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", 10))
    TOP_K_RERANK = int(os.getenv("TOP_K_RERANK", 3))
    THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", 0.35))