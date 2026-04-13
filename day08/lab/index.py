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
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

# TODO Sprint 1: Điều chỉnh chunk size và overlap theo quyết định của nhóm
# Gợi ý từ slide: chunk 300-500 tokens, overlap 50-80 tokens
CHUNK_SIZE = 400       # tokens (ước lượng bằng số ký tự / 4)
CHUNK_OVERLAP = 80     # tokens overlap giữa các chunk


# =============================================================================
# STEP 1: PREPROCESS
# Làm sạch text trước khi chunk và embed
# =============================================================================

def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    """
    Preprocess một tài liệu: extract metadata từ header và làm sạch nội dung.

    Args:
        raw_text: Toàn bộ nội dung file text
        filepath: Đường dẫn file để làm source mặc định

    Returns:
        Dict chứa:
          - "text": nội dung đã clean
          - "metadata": dict với source, department, effective_date, access

    TODO Sprint 1:
    - Extract metadata từ dòng đầu file (Source, Department, Effective Date, Access)
    - Bỏ các dòng header metadata khỏi nội dung chính
    - Normalize khoảng trắng, xóa ký tự rác

    Gợi ý: dùng regex để parse dòng "Key: Value" ở đầu file.
    """
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": filepath,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }
    content_lines = []
    header_done = False

    METADATA_KEYS = ("Source:", "Department:", "Effective Date:", "Access:")

    for line in lines:
        if not header_done:
            if line.startswith("Source:"):
                metadata["source"] = line.replace("Source:", "").strip()
            elif line.startswith("Department:"):
                metadata["department"] = line.replace("Department:", "").strip()
            elif line.startswith("Effective Date:"):
                metadata["effective_date"] = line.replace("Effective Date:", "").strip()
            elif line.startswith("Access:"):
                metadata["access"] = line.replace("Access:", "").strip()
            elif line.startswith("==="):
                # Gặp section heading đầu tiên → kết thúc vùng header
                header_done = True
                content_lines.append(line)
            elif line.strip() == "":
                # Bỏ dòng trống trong vùng header
                continue
            elif line.strip().isupper() and not any(line.startswith(k) for k in METADATA_KEYS):
                # Dòng tiêu đề tài liệu viết HOA hoàn toàn (vd: "QUY TRÌNH KIỂM SOÁT...")
                # → bỏ qua, đã có trong tên file / source metadata
                continue
            else:
                # Các dòng khác (vd: "Ghi chú: ...") → giữ lại làm nội dung
                content_lines.append(line)
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)

    # TODO: Thêm bước normalize text nếu cần
    # Gợi ý: bỏ ký tự đặc biệt thừa, chuẩn hóa dấu câu
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)  # max 2 dòng trống liên tiếp

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
    Chunk tài liệu theo 3 nguyên tắc:
      1. Ưu tiên 1 section (=== ... ===) = 1 chunk — giữ ngữ nghĩa hoàn chỉnh
      2. Gộp section quá ngắn (< MIN_CHUNK_CHARS) vào section liền kề trước
      3. Split section quá dài (> MAX_CHUNK_CHARS) theo \n\n rồi fallback \n

    Mỗi chunk giữ đầy đủ metadata: source, department, effective_date, section.
    """
    MAX_CHUNK_CHARS = CHUNK_SIZE * 4  # section dài hơn này → split thêm

    text = doc["text"]
    base_metadata = doc["metadata"].copy()

    # ------------------------------------------------------------------ #
    # Bước 1: Parse ra danh sách (section_name, section_text)
    # ------------------------------------------------------------------ #
    raw_sections: List[tuple] = []   # [(section_name, text), ...]
    parts = re.split(r"(===.+?===)", text)

    current_name = "Ghi chú"
    current_text = ""

    for part in parts:
        if re.match(r"===.+?===", part):
            if current_text.strip():
                raw_sections.append((current_name, current_text.strip()))
            current_name = part.strip("= ").strip()
            current_text = ""
        else:
            current_text += part

    if current_text.strip():
        raw_sections.append((current_name, current_text.strip()))

    # ------------------------------------------------------------------ #
    # Bước 2: Split section quá dài, tạo chunk cuối cùng
    # (Mỗi section giữ nguyên = 1 chunk, không gộp)
    # ------------------------------------------------------------------ #
    chunks: List[Dict[str, Any]] = []

    for section_name, section_text in raw_sections:
        sub_chunks = _split_by_size(
            text=section_text,
            base_metadata=base_metadata,
            section=section_name,
            max_chars=MAX_CHUNK_CHARS,
        )
        chunks.extend(sub_chunks)

    return chunks


def _split_by_size(
    text: str,
    base_metadata: Dict,
    section: str,
    max_chars: int = CHUNK_SIZE * 4,
) -> List[Dict[str, Any]]:
    """
    Chia text thành các chunk <= max_chars.
    - Nếu text vừa → trả về 1 chunk nguyên
    - Split theo \n\n trước (ranh giới paragraph tự nhiên)
    - Fallback split theo \n nếu không có \n\n
    """
    def make_chunk(t: str) -> Dict:
        return {"text": t, "metadata": {**base_metadata, "section": section}}

    if len(text) <= max_chars:
        return [make_chunk(text)]

    # Ưu tiên \n\n, fallback \n
    separators = ["\n\n", "\n"]
    paragraphs = None
    for sep in separators:
        parts = [p.strip() for p in text.split(sep) if p.strip()]
        if len(parts) > 1:
            paragraphs = parts
            break

    # Không thể split → trả về nguyên (tránh mất dữ liệu)
    if not paragraphs:
        return [make_chunk(text)]

    chunks = []
    current = ""

    for para in paragraphs:
        if not current:
            current = para
        elif len(current) + len(para) + 2 <= max_chars:
            current += "\n\n" + para
        else:
            chunks.append(make_chunk(current))
            current = para

    if current:
        chunks.append(make_chunk(current))

    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

# Cấu hình Jina Embeddings v5
JINA_API_URL = "https://api.jina.ai/v1/embeddings"
JINA_MODEL = "jina-embeddings-v5-text-small"


def get_embedding(text: str, task: str = "retrieval.passage") -> List[float]:
    """
    Tạo embedding vector bằng Jina Embeddings v5 API.

    Args:
        text: Đoạn text cần embed
        task: Loại task cho Jina v5 (retrieval.passage, retrieval.query, text-matching)
              - "retrieval.passage": dùng khi index tài liệu
              - "retrieval.query":  dùng khi embed câu hỏi người dùng
    """
    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        raise ValueError(
            "Thiếu JINA_API_KEY! Thêm vào file .env:\n"
            "  JINA_API_KEY=jina_..."
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": JINA_MODEL,
        "input": [text],
        "task": task,
    }

    response = requests.post(JINA_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    return data["data"][0]["embedding"]


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → store.

    TODO Sprint 1:
    1. Cài thư viện: pip install chromadb
    2. Khởi tạo ChromaDB client và collection
    3. Với mỗi file trong docs_dir:
       a. Đọc nội dung
       b. Gọi preprocess_document()
       c. Gọi chunk_document()
       d. Với mỗi chunk: gọi get_embedding() và upsert vào ChromaDB
    4. In số lượng chunk đã index

    Gợi ý khởi tạo ChromaDB:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_or_create_collection(
            name="rag_lab",
            metadata={"hnsw:space": "cosine"}
        )
    """
    import chromadb

    print(f"Đang build index từ: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    # Khởi tạo ChromaDB — xóa collection cũ trước để tránh data cũ bị cộng dồn
    client = chromadb.PersistentClient(path=str(db_dir))
    try:
        client.delete_collection("rag_lab")
        print("  (Đã xóa collection cũ)")
    except Exception:
        pass  # Chưa có collection → bỏ qua
    collection = client.create_collection(
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

        # Gọi preprocess_document
        doc = preprocess_document(raw_text, str(filepath))

        # Gọi chunk_document
        chunks = chunk_document(doc)

        # Embed và lưu từng chunk vào ChromaDB
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"
            embedding = get_embedding(chunk["text"])
            
            # ChromaDB metadatas values only support str, int, float, or bool
            safe_meta = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v 
                         for k, v in chunk["metadata"].items()}
            
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk["text"]],
                metadatas=[safe_meta],
            )
            
        print(f"    → Đã lưu {len(chunks)} chunks vào ChromaDB")
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
    print("\n--- Test preprocess + chunking ---")
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

    # Bước 3: Build index (yêu cầu implement get_embedding)
    print("\n--- Build Full Index ---")
    build_index()

    # Bước 4: Kiểm tra index
    print("\n--- Inspect Index ---")
    list_chunks()
    inspect_metadata_coverage()

    print("\nSprint 1 setup hoàn thành!")
    print("Việc cần làm:")
    print("  1. Implement get_embedding() - chọn OpenAI hoặc Sentence Transformers")
    print("  2. Implement phần TODO trong build_index()")
    print("  3. Chạy build_index() và kiểm tra với list_chunks()")
    print("  4. Nếu chunking chưa tốt: cải thiện _split_by_size() để split theo paragraph")