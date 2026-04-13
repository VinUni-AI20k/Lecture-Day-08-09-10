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
    #Khanhnq
    """
    Extract Source, Department, Effective Date, Access từ header của content.
    """
    metadata = {
        "source": "unknown",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal"
    }
    
    # Metadata extraction pattern (Key: Value)
    meta_pattern = re.compile(r"^(Source|Department|Effective Date|Access):\s*(.+)$", re.IGNORECASE)
    
    lines = content.strip().split("\n")
    for line in lines:
        match = meta_pattern.match(line)
        if match:
            key = match.group(1).lower().replace(" ", "_")
            metadata[key] = match.group(2).strip()
        elif line.startswith("==="):
            # Kết thúc phần header khi gặp section đầu tiên
            break
            
    return metadata

def split_into_chunks(content: str, base_meta: dict) -> list[Document]:
    #Khanhnq
    """
    Semantic split theo section headers ===...===.
    Đầu ra là danh sách các object Document chứa chunks text và metadata.
    Nhớ xử lý Append alias vào metadata của chunk đầu tiên nếu file có trong ALIAS_MAP.
    """
    # Loại bỏ metadata header khỏi content để tránh trùng lặp
    cleaned_content = re.sub(r"^(Source|Department|Effective Date|Access):.*$\n?", "", content, flags=re.MULTILINE | re.IGNORECASE).strip()
    
    # Split by section headers
    section_parts = re.split(r"(===\s*.+?\s*===)", cleaned_content)
    
    documents = []
    current_section = "General"
    
    i = 0
    while i < len(section_parts):
        part = section_parts[i].strip()
        if not part:
            i += 1
            continue
            
        if re.match(r"===\s*.+?\s*===", part):
            current_section = part.strip("= ").strip()
            i += 1
            if i < len(section_parts):
                section_content = section_parts[i].strip()
                if section_content:
                    doc = Document(
                        page_content=section_content,
                        metadata={**base_meta, "section": current_section}
                    )
                    documents.append(doc)
                i += 1
        else:
            # Nội dung trước mọi section header
            doc = Document(
                page_content=part,
                metadata={**base_meta, "section": current_section}
            )
            documents.append(doc)
            i += 1

    # Xử lý Alias đặc biệt cho chunk đầu tiên
    source_key = base_meta.get("source", "").lower()
    # Tìm kiếm tương đối trong ALIAS_MAP
    for path_key, aliases in ALIAS_MAP.items():
        if path_key.lower() in source_key:
            if documents:
                alias_text = f"[Aliases: {', '.join(aliases)}]\n"
                documents[0].page_content = alias_text + documents[0].page_content
            break

    return documents

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
    #khanhnq
    """
    In preview 10 chunks đầu tiên từ vector store để kiểm tra.
    """
    try:
        # Lấy dữ liệu từ Chroma và giới hạn 10 bản ghi
        results = vectorstore.get(limit=10, include=["documents", "metadatas"])
        
        print("\n" + "="*50)
        print("PREVIEW CÁC CHUNKS TRONG INDEX")
        print("="*50)
        
        for i in range(len(results["ids"])):
            doc_content = results["documents"][i]
            meta = results["metadatas"][i]
            
            print(f"\n[Chunk {i+1}]")
            print(f"  Source: {meta.get('source', 'N/A')}")
            print(f"  Section: {meta.get('section', 'N/A')}")
            print(f"  Date: {meta.get('effective_date', 'N/A')}")
            print(f"  Preview: {doc_content[:150].replace('\\n', ' ')}...")
            
        print("="*50 + "\n")
    except Exception as e:
        print(f"Lỗi khi list_chunks: {e}")

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
