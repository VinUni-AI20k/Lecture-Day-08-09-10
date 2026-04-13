"""
index.py — Sprint 1: Build RAG Index
====================================
Mục tiêu Sprint 1 (60 phút):
  - Đọc và preprocess tài liệu từ data/docs/
  - Chunk tài liệu theo cấu trúc tự nhiên (heading/section)
  - Gắn metadata: source, section, department, effective_date, access
  - Embed và lưu vào vector store (ChromaDB)

Definition of Done Sprint 1:
  ✓ Script chạy được và index đủ docs
  ✓ Có ít nhất 3 metadata fields hữu ích cho retrieval
  ✓ Có thể kiểm tra chunk bằng list_chunks()
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).resolve().parent.parent / "chroma_db"

# TODO Sprint 1: Điều chỉnh chunk size và overlap theo quyết định của nhóm
# Gợi ý từ slide: chunk 300-500 tokens, overlap 50-80 tokens
CHUNK_SIZE = 400       # tokens (ước lượng bằng số ký tự / 4)
CHUNK_OVERLAP = 80     # tokens overlap giữa các chunk
EMBEDDING_KEY = os.getenv("AUTHORIZATION_JINA")

# =============================================================================
# STEP 1: PREPROCESS
# Làm sạch text trước khi chunk và embed
# =============================================================================

def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    """
    Preprocess một tài liệu: extract metadata từ header và làm sạch nội dung.
    """
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": filepath,
        "section": "General",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
        "title": "Untitled",
    }
    
    content_start_idx = 0
    # Dòng 1 thường là Title
    if lines and lines[0].strip():
        metadata["title"] = lines[0].strip()
        content_start_idx = 1

    for i in range(content_start_idx, min(len(lines), 10)):
        line = lines[i].strip()
        if not line:
            continue
        
        # Parse metadata từ các dòng "Key: Value"
        if ":" in line:
            key, value = [part.strip() for part in line.split(":", 1)]
            lower_key = key.lower()
            if "source" in lower_key:
                metadata["source"] = value
                content_start_idx = i + 1
            elif "department" in lower_key:
                metadata["department"] = value
                content_start_idx = i + 1
            elif "effective date" in lower_key:
                metadata["effective_date"] = value
                content_start_idx = i + 1
            elif "access" in lower_key:
                metadata["access"] = value
                content_start_idx = i + 1
        
        if line.startswith("==="):
            # Gặp section heading đầu tiên -> phần header đã hết
            content_start_idx = i
            break

    # Lấy nội dung sau khi đã bỏ header
    content_lines = lines[content_start_idx:]
    cleaned_text = "\n".join(content_lines).strip()
    
    # Normalize khoảng trắng
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return {
        "text": cleaned_text,
        "metadata": metadata,
    }


# =============================================================================
# STEP 2: CHUNK
# Chia tài liệu thành các đoạn nhỏ theo cấu trúc tự nhiên
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Chunk một tài liệu theo cấu trúc Section/Phần/Điều.
    """
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []

    # Regex để bắt các pattern: === Section X: Title ===, === Phần X: Title ===, === Điều X: Title ===
    section_pattern = r"(=== (?:Section|Phần|Điều) \d+: .*? ===)"
    parts = re.split(section_pattern, text)

    current_section = "General"
    
    for i in range(len(parts)):
        part = parts[i].strip()
        if not part:
            continue
            
        if re.match(section_pattern, part):
            current_section = part.strip("= ").strip()
        else:
            # Đây là nội dung của section
            # Nếu là FAQ, chia thêm theo Q&A
            if "faq" in base_metadata.get("source", "").lower() or "faq" in base_metadata.get("title", "").lower():
                qa_pairs = re.split(r"(?=\nQ:)", "\n" + part)
                for qa in qa_pairs:
                    if qa.strip():
                        chunks.extend(_split_by_size(
                            qa.strip(),
                            base_metadata=base_metadata,
                            section=current_section
                        ))
            else:
                # Các loại doc khác, split theo paragraph nếu quá dài
                chunks.extend(_split_by_size(
                    part,
                    base_metadata=base_metadata,
                    section=current_section
                ))

    return chunks


def _split_by_size(
    text: str,
    base_metadata: Dict,
    section: str,
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:
    """
    Split text dài thành chunks theo Paragraph (\n\n) để giữ ngữ cảnh tốt nhất.
    """
    if len(text) <= chunk_chars:
        return [{
            "text": text,
            "metadata": {**base_metadata, "section": section},
        }]

    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk_text = ""
    
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
            
        # Nếu cộng p vào chunk hiện tại vẫn chưa quá giới hạn
        if len(current_chunk_text) + len(p) + 2 <= chunk_chars:
            if current_chunk_text:
                current_chunk_text += "\n\n" + p
            else:
                current_chunk_text = p
        else:
            # Lưu chunk hiện tại
            if current_chunk_text:
                chunks.append({
                    "text": current_chunk_text,
                    "metadata": {**base_metadata, "section": section},
                })
                # Khởi tạo chunk mới với overlap (lấy n ký tự cuối của chunk cũ làm context)
                overlap_text = current_chunk_text[-overlap_chars:] if len(current_chunk_text) > overlap_chars else current_chunk_text
                current_chunk_text = overlap_text + "\n\n" + p
            else:
                # Trường hợp paragraph duy nhất đã quá dài -> buộc phải cắt theo ký tự
                # (Rất ít khi xảy ra với doc này)
                start = 0
                while start < len(p):
                    end = min(start + chunk_chars, len(p))
                    chunks.append({
                        "text": p[start:end],
                        "metadata": {**base_metadata, "section": section},
                    })
                    start = end - overlap_chars
                current_chunk_text = ""

    if current_chunk_text:
        chunks.append({
            "text": current_chunk_text,
            "metadata": {**base_metadata, "section": section},
        })

    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

def get_embedding(text: str, task: str = "retrieval.passage") -> List[float]:
    """
    Tạo embedding vector cho một đoạn text sử dụng JINA AI API.
    """
    import requests
    
    api_key = os.getenv("AUTHORIZATION_JINA")
    if not api_key:
        raise ValueError("AUTHORIZATION_JINA not found in environment. Please add to .env")
        
    url = "https://api.jina.ai/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "jina-embeddings-v5-text-small",
        "task": task,
        "normalized": True,
        "input": [text]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
    except Exception as e:
        print(f"Lỗi khi gọi JINA API: {e}")
        raise e


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → store.
    """
    import chromadb

    print(f"Đang build index từ: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"}
    )

    total_chunks = 0
    doc_files = list(docs_dir.glob("*.txt"))

    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return

    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")

        # Step 1: Preprocess
        doc = preprocess_document(raw_text, str(filepath))

        # Step 2: Chunk
        chunks = chunk_document(doc)
        print(f"    → {len(chunks)} chunks")

        # Step 3: Embed + Store
        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"
            embedding = get_embedding(chunk["text"])
            
            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk["text"])
            metadatas.append(chunk["metadata"])

        if ids:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
        
        total_chunks += len(chunks)

    print(f"\nHoàn thành! Tổng số chunks đã index: {total_chunks}")


# =============================================================================
# STEP 4: INSPECT / KIỂM TRA
# Dùng để debug và kiểm tra chất lượng index
# =============================================================================

def list_chunks(db_dir: Path = CHROMA_DB_DIR, n: int = 5) -> None:
    """
    In ra n chunk đầu tiên trong ChromaDB để kiểm tra chất lượng index.

    TODO Sprint 1:
    Implement sau khi hoàn thành build_index().
    Kiểm tra:
    - Chunk có giữ đủ metadata không? (source, section, effective_date)
    - Chunk có bị cắt giữa điều khoản không?
    - Metadata effective_date có đúng không?
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(limit=n, include=["documents", "metadatas"])

        print(f"\n=== Top {n} chunks trong index ===\n")
        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"[Chunk {i+1}]")
            print(f"  Source: {meta.get('source', 'N/A')}")
            print(f"  Section: {meta.get('section', 'N/A')}")
            print(f"  Effective Date: {meta.get('effective_date', 'N/A')}")
            print(f"  Text preview: {doc[:120]}...")
            print()
    except Exception as e:
        print(f"Lỗi khi đọc index: {e}")
        print("Hãy chạy build_index() trước.")


def inspect_metadata_coverage(db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Kiểm tra phân phối metadata trong toàn bộ index.

    Checklist Sprint 1:
    - Mọi chunk đều có source?
    - Có bao nhiêu chunk từ mỗi department?
    - Chunk nào thiếu effective_date?

    TODO: Implement sau khi build_index() hoàn thành.
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(include=["metadatas"])

        print(f"\nTổng chunks: {len(results['metadatas'])}")

        # TODO: Phân tích metadata
        # Đếm theo department, kiểm tra effective_date missing, v.v.
        departments = {}
        missing_date = 0
        for meta in results["metadatas"]:
            dept = meta.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1
            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1

        print("Phân bố theo department:")
        for dept, count in departments.items():
            print(f"  {dept}: {count} chunks")
        print(f"Chunks thiếu effective_date: {missing_date}")

    except Exception as e:
        print(f"Lỗi: {e}. Hãy chạy build_index() trước.")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 1: Build RAG Index")
    print("=" * 60)

    # Bước 1: Kiểm tra docs
    doc_files = list(DOCS_DIR.glob("*.txt"))
    print(f"\nTìm thấy {len(doc_files)} tài liệu:")
    for f in doc_files:
        print(f"  - {f.name}")

    # Bước 2: Test preprocess và chunking (không cần API key)
    print("\n--- Test preprocess + chunking file đầu tiên ---")
    for filepath in doc_files[:1]:  # Test với 1 file đầu
        raw = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw, str(filepath))
        chunks = chunk_document(doc)
        print(f"\nFile: {filepath.name}")
        print(f"  Metadata: {doc['metadata']}")
        print(f"  Số chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n  [Chunk {i+1}] Section: {chunk['metadata']['section']}")
            print(f"  Text: {chunk['text'][:150]}...")

    # Bước 3: Build index
    print("\n--- Build Full Index ---")
    build_index()

    # Bước 4: Kiểm tra index
    list_chunks()
    inspect_metadata_coverage()

    print("\nSprint 1 setup hoàn thành!")
    # print("Việc cần làm:")
    # print("  1. Implement get_embedding() - chọn OpenAI hoặc Sentence Transformers")
    # print("  2. Implement phần TODO trong build_index()")
    # print("  3. Chạy build_index() và kiểm tra với list_chunks()")
    # print("  4. Nếu chunking chưa tốt: cải thiện _split_by_size() để split theo paragraph")
