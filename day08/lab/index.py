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
import math
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"
EMBED_MODEL_NAME = "Alibaba-NLP/gte-multilingual-base"

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
    metadata_key_map = {
        "source": "source",
        "department": "department",
        "effective date": "effective_date",
        "access": "access",
    }

    for line in lines:
        stripped = line.strip()

        if not header_done:
            # Parse metadata từ header "Key: Value"
            header_match = re.match(r"^([A-Za-z ]+):\s*(.+)$", stripped)
            if header_match:
                key, value = header_match.groups()
                mapped_key = metadata_key_map.get(key.lower().strip())
                if mapped_key:
                    metadata[mapped_key] = value.strip()
                    continue

            if re.match(r"^===.*?===\s*$", stripped):
                # Gặp section heading đầu tiên → kết thúc header
                header_done = True
                content_lines.append(stripped)
            elif stripped == "" or stripped.isupper():
                # Dòng tên tài liệu (toàn chữ hoa) hoặc dòng trống
                continue
            else:
                # Không còn header nữa, bắt đầu nội dung
                header_done = True
                content_lines.append(stripped)
        else:
            content_lines.append(line.rstrip())

    cleaned_text = "\n".join(content_lines)

    # Normalize khoảng trắng / dòng trống
    cleaned_text = re.sub(r"[ \t]+\n", "\n", cleaned_text)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)  # max 2 dòng trống liên tiếp
    cleaned_text = cleaned_text.strip()

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

    # Bước 1: Split theo heading pattern "=== ... ==="
    sections = re.split(r"(?m)(^===.*?===\s*$)", text)

    current_section = "General"
    current_section_parts: List[str] = []

    for part in sections:
        stripped = part.strip()
        if not stripped:
            continue

        if re.match(r"^===.*?===$", stripped):
            # Lưu section trước (nếu có nội dung)
            current_section_text = "\n".join(current_section_parts).strip()
            if current_section_text:
                section_chunks = _split_by_size(
                    current_section_text,
                    base_metadata=base_metadata,
                    section=current_section,
                )
                chunks.extend(section_chunks)

            # Bắt đầu section mới
            current_section = stripped.strip("= ").strip()
            current_section_parts = []
        else:
            current_section_parts.append(stripped)

    # Lưu section cuối cùng
    current_section_text = "\n".join(current_section_parts).strip()
    if current_section_text:
        section_chunks = _split_by_size(
            current_section_text,
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
    Helper: Split text dài thành chunks với overlap.

    TODO Sprint 1:
    Hiện tại dùng split đơn giản theo ký tự.
    Cải thiện: split theo paragraph (\n\n) trước, rồi mới ghép đến khi đủ size.
    """
    if len(text) <= chunk_chars:
        # Toàn bộ section vừa một chunk
        return [{
            "text": text,
            "metadata": {**base_metadata, "section": section},
        }]

    # Tránh overlap lớn hơn chunk size gây lặp vô hạn
    overlap_chars = min(overlap_chars, max(0, chunk_chars // 2))

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    raw_chunks: List[str] = []
    current_chunk = ""

    for para in paragraphs:
        candidate = para if not current_chunk else f"{current_chunk}\n\n{para}"

        if len(candidate) <= chunk_chars:
            current_chunk = candidate
            continue

        if current_chunk:
            raw_chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk = para

        # Nếu một paragraph quá dài thì tách tiếp theo ranh giới tự nhiên
        while len(current_chunk) > chunk_chars:
            split_at = _find_natural_split(current_chunk, chunk_chars)
            if split_at <= 0 or split_at >= len(current_chunk):
                split_at = chunk_chars

            piece = current_chunk[:split_at].strip()
            if piece:
                raw_chunks.append(piece)

            next_start = max(0, split_at - overlap_chars)
            next_chunk = current_chunk[next_start:].strip()

            # Guard tránh vòng lặp không tiến triển
            if next_chunk == current_chunk:
                next_chunk = current_chunk[split_at:].strip()

            current_chunk = next_chunk

    if current_chunk.strip():
        raw_chunks.append(current_chunk.strip())

    chunks: List[Dict[str, Any]] = []
    for i, chunk_text in enumerate(raw_chunks):
        if i > 0 and overlap_chars > 0:
            overlap_text = _extract_overlap_tail(raw_chunks[i - 1], overlap_chars)
            if overlap_text and not chunk_text.startswith(overlap_text):
                chunk_text = f"{overlap_text}\n{chunk_text}"

        chunks.append({
            "text": chunk_text,
            "metadata": {**base_metadata, "section": section},
        })

    return chunks


def _find_natural_split(text: str, target: int) -> int:
    """Tìm điểm cắt gần target nhưng ưu tiên ranh giới tự nhiên."""
    min_acceptable = int(target * 0.6)
    for separator in ("\n\n", "\n", ". ", "; ", ", ", " "):
        idx = text.rfind(separator, 0, target)
        if idx >= min_acceptable:
            return idx + len(separator)
    return target


def _extract_overlap_tail(text: str, overlap_chars: int) -> str:
    """Lấy phần tail của chunk trước để làm overlap cho chunk sau."""
    if overlap_chars <= 0:
        return ""
    if len(text) <= overlap_chars:
        return text.strip()

    tail = text[-overlap_chars:].strip()
    # Cố gắng bắt đầu overlap ở ranh giới dễ đọc hơn
    for separator in ("\n", ". ", "; ", ", ", " "):
        pos = tail.find(separator)
        if 0 <= pos < max(1, overlap_chars // 3):
            tail = tail[pos + len(separator):].strip()
            break

    return tail


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text.

    TODO Sprint 1:
    Mặc định dùng Sentence Transformers local với model:
        Alibaba-NLP/gte-multilingual-base

    Nếu model local chưa khả dụng, dùng fallback hash embedding để Sprint 1
    vẫn chạy được mà không cần API key.
    """
    text = text.strip()
    if not text:
        raise ValueError("Không thể tạo embedding cho text rỗng.")

    # Sentence Transformers (local) là mặc định.
    # Cache model để không load lại mỗi chunk.
    global _SENTENCE_TRANSFORMER_MODEL
    if "_SENTENCE_TRANSFORMER_MODEL" not in globals():
        _SENTENCE_TRANSFORMER_MODEL = None

    if _SENTENCE_TRANSFORMER_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[reportMissingImports]
            _SENTENCE_TRANSFORMER_MODEL = SentenceTransformer(EMBED_MODEL_NAME)
        except Exception:
            # Fallback nhẹ để Sprint 1 vẫn chạy được khi chưa có model local
            return _hash_embedding(text)

    vector = _SENTENCE_TRANSFORMER_MODEL.encode(text, normalize_embeddings=True)
    return vector.tolist() if hasattr(vector, "tolist") else list(vector)


def _hash_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Fallback embedding deterministic (không cần model ngoài).
    Dùng hashing trick trên token để tạo vector dense đã chuẩn hóa.
    """
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return [0.0] * dim

    vec = [0.0] * dim
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        # Mỗi token cập nhật nhiều chiều để tăng ổn định
        for i in range(0, 16, 2):
            idx = int.from_bytes(digest[i:i+2], "little") % dim
            sign = 1.0 if digest[16 + i] % 2 == 0 else -1.0
            weight = 1.0 + (digest[17 + i] / 255.0)
            vec[idx] += sign * weight

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]

    return vec


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

    # Khởi tạo ChromaDB persistent collection
    client = chromadb.PersistentClient(path=str(db_dir))
    try:
        client.delete_collection("rag_lab")
    except Exception:
        # Collection chưa tồn tại -> bỏ qua
        pass

    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"},
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

        # Bỏ chunk rỗng (nếu có)
        chunks = [c for c in chunks if c.get("text", "").strip()]
        if not chunks:
            print("    → 0 chunks (bỏ qua vì rỗng)")
            continue

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i:04d}"
            embedding = get_embedding(chunk["text"])

            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk["text"])
            metadatas.append(chunk["metadata"])

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        print(f"    → {len(chunks)} chunks indexed")
        total_chunks += len(chunks)

    print(f"\nHoàn thành! Tổng số chunks: {total_chunks}")
    print(f"Collection 'rag_lab' hiện có {collection.count()} chunks.")


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
        documents = results.get("documents") or []
        metadatas = results.get("metadatas") or []

        print(f"\n=== Top {n} chunks trong index ===\n")
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
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
        metadatas = results.get("metadatas") or []

        print(f"\nTổng chunks: {len(metadatas)}")

        # TODO: Phân tích metadata
        # Đếm theo department, kiểm tra effective_date missing, v.v.
        departments = {}
        missing_date = 0
        for meta in metadatas:
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
    list_chunks()
    inspect_metadata_coverage()

    print("\nSprint 1 setup hoàn thành!")
    print("Đã hoàn thành các mục chính:")
    print("  1. get_embedding() (OpenAI nếu có key, fallback Sentence Transformers)")
    print("  2. build_index() (embed + upsert vào ChromaDB)")
    print("  3. list_chunks() và inspect_metadata_coverage() để kiểm tra chất lượng index")
