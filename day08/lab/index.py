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

# Lazy-initialized OpenAI client (singleton — avoids creating per-call)
_openai_client = None

def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client

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

    for line in lines:
        if not header_done:
            # TODO: Parse metadata từ các dòng "Key: Value"
            # Ví dụ: "Source: policy/refund-v4.pdf" → metadata["source"] = "policy/refund-v4.pdf"
            if line.startswith("Source:"):
                metadata["source"] = line.replace("Source:", "").strip()
            elif line.startswith("Department:"):
                metadata["department"] = line.replace("Department:", "").strip()
            elif line.startswith("Effective Date:"):
                metadata["effective_date"] = line.replace("Effective Date:", "").strip()
            elif line.startswith("Access:"):
                metadata["access"] = line.replace("Access:", "").strip()
            elif line.startswith("==="):
                # Gặp section heading đầu tiên → kết thúc header
                header_done = True
                content_lines.append(line)
            elif line.strip() == "" or line.isupper():
                # Dòng tên tài liệu (toàn chữ hoa) hoặc dòng trống
                continue
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
    Chunk một tài liệu đã preprocess thành danh sách các chunk nhỏ.

    Args:
        doc: Dict với "text" và "metadata" (output của preprocess_document)

    Returns:
        List các Dict, mỗi dict là một chunk với:
          - "text": nội dung chunk
          - "metadata": metadata gốc + "section" của chunk đó

    TODO Sprint 1:
    1. Split theo heading "=== Section ... ===" hoặc "=== Phần ... ===" trước
    2. Nếu section quá dài (> CHUNK_SIZE * 4 ký tự), split tiếp theo paragraph
    3. Thêm overlap: lấy đoạn cuối của chunk trước vào đầu chunk tiếp theo
    4. Mỗi chunk PHẢI giữ metadata đầy đủ từ tài liệu gốc

    Gợi ý: Ưu tiên cắt tại ranh giới tự nhiên (section, paragraph)
    thay vì cắt theo token count cứng.
    """
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []

    # TODO: Implement chunking theo section heading
    # Bước 1: Split theo heading pattern "=== ... ==="
    sections = re.split(r"(===.*?===)", text)

    current_section = "General"
    current_section_text = ""

    for part in sections:
        if re.match(r"===.*?===", part):
            # Lưu section trước (nếu có nội dung)
            if current_section_text.strip():
                section_chunks = _split_by_size(
                    current_section_text.strip(),
                    base_metadata=base_metadata,
                    section=current_section,
                )
                chunks.extend(section_chunks)
            # Bắt đầu section mới
            current_section = part.strip("= ").strip()
            current_section_text = ""
        else:
            current_section_text += part

    # Lưu section cuối cùng
    if current_section_text.strip():
        section_chunks = _split_by_size(
            current_section_text.strip(),
            base_metadata=base_metadata,
            section=current_section,
        )
        chunks.extend(section_chunks)

    return chunks


def _split_by_size(
    text: str,
    base_metadata: Dict,
    section: str,
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:
    """
    Split text into chunks at paragraph (\\n\\n) boundaries with overlap.
    Never cuts inside a paragraph.
    """
    if len(text) <= chunk_chars:
        return [{"text": text, "metadata": {**base_metadata, "section": section}}]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[Dict[str, Any]] = []
    current_paras: List[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)

        if current_paras and current_len + para_len + 2 > chunk_chars:
            # Flush current chunk
            chunk_text = "\n\n".join(current_paras)
            chunks.append({"text": chunk_text, "metadata": {**base_metadata, "section": section}})

            # Build overlap: take whole paragraphs from the tail, up to overlap_chars
            overlap_paras: List[str] = []
            overlap_len = 0
            for p in reversed(current_paras):
                if overlap_len + len(p) + 2 <= overlap_chars:
                    overlap_paras.insert(0, p)
                    overlap_len += len(p) + 2
                else:
                    break

            current_paras = overlap_paras + [para]
            current_len = sum(len(p) + 2 for p in current_paras)
        else:
            current_paras.append(para)
            current_len += para_len + 2

    # Flush the final chunk
    if current_paras:
        chunks.append({
            "text": "\n\n".join(current_paras),
            "metadata": {**base_metadata, "section": section},
        })

    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text dùng OpenAI text-embedding-3-small.
    """
    client = _get_openai_client()
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small",
    )
    return response.data[0].embedding


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → store.
    """
    import chromadb
    from tqdm import tqdm

    print(f"Đang build index từ: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0
    doc_files = list(docs_dir.glob("*.txt"))

    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return

    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")

        doc = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc)

        for i, chunk in enumerate(tqdm(chunks, desc=f"    {filepath.stem}", leave=False)):
            chunk_id = f"{filepath.stem}_{i}"
            embedding = get_embedding(chunk["text"])
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk["text"]],
                metadatas=[chunk["metadata"]],
            )
        total_chunks += len(chunks)
        print(f"    → {len(chunks)} chunks indexed")

    print(f"\nHoàn thành! Tổng số chunks: {total_chunks}")


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

    # Bước 3: Build index
    print("\n--- Build Full Index ---")
    build_index()

    # Bước 4: Kiểm tra index
    print("\n--- Kiểm tra index ---")
    list_chunks(n=5)
    inspect_metadata_coverage()
