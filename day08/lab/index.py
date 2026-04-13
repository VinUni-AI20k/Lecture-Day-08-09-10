# index.py
"""
Sprint 1: Xây dựng Index (Document Ingestion & Hybrid Indexing)
Mục tiêu: Đọc tài liệu từ data/docs/, parse metadata, split thành chunks, và build Chroma (Dense) + BM25S (Sparse) index.
"""

import os
import re
import pickle
from pathlib import Path
from typing import List, Dict, Any

import bm25s
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

# --- CẤU HÌNH ---
DOCS_DIR = os.getenv("DOCS_DIR", "./data/docs")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
BM25_INDEX_DIR = os.getenv("BM25_INDEX_DIR", "./data/bm25_index")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

ALIAS_MAP = {
    "it/access-control-sop.md": [
        "approval matrix for system access",
        "approval matrix",
        "access control sop",
    ]
}

def parse_metadata(content: str) -> dict:
    """
    Extract Source, Department, Effective Date, Access từ header của content.
    """
    # TODO: Implement parse_metadata
    pass

def split_into_chunks(content: str, base_meta: dict) -> list[Document]:
    """
    Semantic split theo section headers ===...===.
    Đầu ra là danh sách các object Document chứa chunks text và metadata.
    Nhớ xử lý Append alias vào metadata của chunk đầu tiên nếu file có trong ALIAS_MAP.
    """
    # TODO: Implement split_into_chunks
    pass

def build_vector_index(documents: list[Document]) -> Chroma:
    """
    Build hoặc load Chroma vector store từ danh sách Document.
    """
    # TODO: Implement build_vector_index
    pass

def build_bm25_index(documents: list[Document]) -> tuple:
    """
    Build BM25S sparse index và trả về (retriever, documents).
    Phải lưu (persist) ra thư mục BM25_INDEX_DIR.
    """
    # TODO: Implement build_bm25_index
    pass

def list_chunks(vectorstore):
    """
    In preview 10 chunks đầu tiên từ vector store để kiểm tra.
    """
    # TODO: Implement list_chunks
    pass

def build_all(docs_dir=DOCS_DIR):
    """
    Entry point Sprint 1: orchestrate toàn bộ quá trình xử lý:
    1. Lặp qua các file *.txt trong docs_dir
    2. Gọi parse_metadata
    3. Gọi split_into_chunks để gom toàn bộ chunks
    4. Gọi build_vector_index và build_bm25_index
    5. Gọi list_chunks để xác minh
    """
    # TODO: Implement build_all
    pass

if __name__ == "__main__":
    print("Bắt đầu chạy build_all() cho vòng khởi tạo Index...")
    build_all()
