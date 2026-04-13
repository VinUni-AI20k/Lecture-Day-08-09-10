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
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List
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

# Embedding/index config (override bằng ENV nếu cần)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))

_OPENAI_CLIENT = None

HEADER_META_RE = re.compile(r"^(Source|Department|Effective Date|Access):\s*(.+?)\s*$")
SECTION_HEADING_RE = re.compile(r"^===\s*(.+?)\s*===\s*$")


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
    lines = raw_text.splitlines()
    metadata = {
        "source": filepath,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }
    content_lines = []
    in_header = True
    metadata_key_map = {
        "Source": "source",
        "Department": "department",
        "Effective Date": "effective_date",
        "Access": "access",
    }

    for raw_line in lines:
        stripped = raw_line.strip()

        if in_header:
            meta_match = HEADER_META_RE.match(stripped)
            if meta_match:
                key, value = meta_match.groups()
                metadata[metadata_key_map[key]] = value.strip()
                continue

            # Bỏ dòng tiêu đề in hoa và dòng trống ở phần header.
            if stripped == "" or stripped.isupper():
                continue

            # Header kết thúc tại dòng nội dung đầu tiên (không bắt buộc phải là heading).
            in_header = False

        content_lines.append(raw_line.rstrip())

    cleaned_text = "\n".join(content_lines)

    # TODO: Thêm bước normalize text nếu cần
    # Gợi ý: bỏ ký tự đặc biệt thừa, chuẩn hóa dấu câu
    # Normalize: bỏ ký tự đặc biệt thừa, chuẩn hóa dấu cách
    cleaned_text = re.sub(r"[\r\t]+", " ", cleaned_text)
    cleaned_text = re.sub(r" +", " ", cleaned_text)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)  # max 2 dòng trống liên tiếp

    return {
        "text": cleaned_text.strip(),
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
    chunks: List[Dict[str, Any]] = []

    current_section = "General"
    current_lines: List[str] = []
    sections: List[Dict[str, str]] = []

    for line in text.splitlines():
        heading_match = SECTION_HEADING_RE.match(line.strip())
        if heading_match:
            previous_text = "\n".join(current_lines).strip()
            if previous_text:
                sections.append({"section": current_section, "text": previous_text})
            current_section = heading_match.group(1).strip()
            current_lines = []
            continue

        current_lines.append(line)

    final_text = "\n".join(current_lines).strip()
    if final_text:
        sections.append({"section": current_section, "text": final_text})

    for section in sections:
        chunks.extend(
            _split_by_size(
                section["text"],
                base_metadata=base_metadata,
                section=section["section"],
            )
        )

    return chunks


def _split_long_paragraph(paragraph: str, max_chars: int) -> List[str]:
    """Tách paragraph dài thành các đoạn nhỏ hơn, ưu tiên tách theo câu."""
    paragraph = paragraph.strip()
    if not paragraph:
        return []
    if len(paragraph) <= max_chars:
        return [paragraph]

    sentences = [s.strip() for s in re.split(r"(?<=[.!?;:])\s+", paragraph) if s.strip()]
    if len(sentences) <= 1:
        return [
            paragraph[i:i + max_chars].strip()
            for i in range(0, len(paragraph), max_chars)
            if paragraph[i:i + max_chars].strip()
        ]

    pieces: List[str] = []
    current: List[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence) + 1

        if current and current_len + sentence_len > max_chars:
            pieces.append(" ".join(current).strip())
            current = []
            current_len = 0

        if len(sentence) > max_chars:
            pieces.extend(
                [
                    sentence[i:i + max_chars].strip()
                    for i in range(0, len(sentence), max_chars)
                    if sentence[i:i + max_chars].strip()
                ]
            )
            continue

        current.append(sentence)
        current_len += sentence_len

    if current:
        pieces.append(" ".join(current).strip())

    return pieces


def _split_by_size(
    text: str,
    base_metadata: Dict[str, Any],
    section: str,
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:
    """
    Helper: Split text dài thành chunks với overlap.

    TODO Sprint 1:
    Hiện tại dùng split đơn giản theo ký tự.
    Cải thiện: split theo paragraph (\n\n) trước, rồi mới ghép đến khi đủ size.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []

    units: List[str] = []
    for paragraph in paragraphs:
        units.extend(_split_long_paragraph(paragraph, max_chars=chunk_chars))

    chunks: List[Dict[str, Any]] = []
    current_units: List[str] = []
    current_len = 0

    for unit in units:
        unit_len = len(unit) + 2

        if current_units and current_len + unit_len > chunk_chars:
            chunks.append(
                {
                    "text": "\n\n".join(current_units).strip(),
                    "metadata": {**base_metadata, "section": section},
                }
            )

            if overlap_chars > 0:
                overlap_units: List[str] = []
                overlap_len = 0
                for prev in reversed(current_units):
                    prev_len = len(prev) + 2
                    if overlap_units and overlap_len + prev_len > overlap_chars:
                        break
                    overlap_units.insert(0, prev)
                    overlap_len += prev_len
                current_units = overlap_units
                current_len = sum(len(p) + 2 for p in current_units)
            else:
                current_units = []
                current_len = 0

        current_units.append(unit)
        current_len += unit_len

    if current_units:
        chunks.append(
            {
                "text": "\n\n".join(current_units).strip(),
                "metadata": {**base_metadata, "section": section},
            }
        )

    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================


def _get_openai_client():
    """Khởi tạo OpenAI client một lần để giảm overhead."""
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Thiếu OPENAI_API_KEY. Hãy thêm key vào file .env")
        _OPENAI_CLIENT = OpenAI(api_key=api_key)
    return _OPENAI_CLIENT


def _batched(items: List[Any], batch_size: int) -> Iterable[List[Any]]:
    """Chia list thành các batch cố định."""
    if batch_size <= 0:
        raise ValueError("batch_size phải > 0")

    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Tạo embeddings theo batch để index nhanh hơn gọi từng chunk."""
    if not texts:
        return []

    client = _get_openai_client()
    response = client.embeddings.create(
        input=texts,
        model=EMBEDDING_MODEL,
    )
    return [item.embedding for item in response.data]


def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text.

    TODO Sprint 1:
    Chọn một trong hai:

    Option A — OpenAI Embeddings (cần OPENAI_API_KEY):
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    Option B — Sentence Transformers (chạy local, không cần API key):
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        return model.encode(text).tolist()
    """
    return get_embeddings([text])[0]


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

    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"}
    )

    total_chunks = 0
    doc_files = sorted(docs_dir.glob("*.txt"))

    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return

    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc)
        print(f"    → {len(chunks)} chunks")
        if not chunks:
            continue

        source_value = doc["metadata"].get("source", str(filepath))
        try:
            existing = collection.get(where={"source": source_value}, include=[])
            existing_ids = existing.get("ids", [])
            if existing_ids:
                collection.delete(ids=existing_ids)
        except Exception as e:
            print(f"      Cảnh báo: không xóa được chunk cũ ({e})")

        indexed_for_doc = 0
        for batch_idx, chunk_batch in enumerate(_batched(chunks, EMBEDDING_BATCH_SIZE)):
            batch_start = batch_idx * EMBEDDING_BATCH_SIZE
            batch_ids = [f"{filepath.stem}_{batch_start + i}" for i in range(len(chunk_batch))]
            batch_texts = [chunk["text"] for chunk in chunk_batch]
            batch_metas = [chunk["metadata"] for chunk in chunk_batch]

            try:
                batch_embeddings = get_embeddings(batch_texts)
                collection.upsert(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_texts,
                    metadatas=batch_metas,
                )
                indexed_for_doc += len(chunk_batch)
            except Exception as batch_error:
                print(f"      Lỗi batch {batch_idx + 1}, fallback từng chunk: {batch_error}")
                for i, chunk in enumerate(chunk_batch):
                    chunk_idx = batch_start + i
                    chunk_id = f"{filepath.stem}_{chunk_idx}"
                    try:
                        embedding = get_embedding(chunk["text"])
                        collection.upsert(
                            ids=[chunk_id],
                            embeddings=[embedding],
                            documents=[chunk["text"]],
                            metadatas=[chunk["metadata"]],
                        )
                        indexed_for_doc += 1
                    except Exception as chunk_error:
                        print(f"      Lỗi embedding chunk {chunk_idx}: {chunk_error}")

        total_chunks += indexed_for_doc
        print(f"    ✓ Indexed: {indexed_for_doc}/{len(chunks)} chunks")

    print(f"\nHoàn thành! Tổng số chunks: {total_chunks}")
    print("Đã lưu embedding và metadata vào ChromaDB.")


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
    list_chunks()
    inspect_metadata_coverage()

    print("\nSprint 1 đã hoàn thành!")