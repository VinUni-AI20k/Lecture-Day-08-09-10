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

Chunking Strategy: Structural Chunking (Section-based + Paragraph-aware)
  - Cấp 1: Cắt theo section heading "=== ... ==="
  - Cấp 2: Trong mỗi section, cắt theo paragraph nếu quá dài
  - Overlap: Lấy paragraph cuối của chunk trước ghép vào đầu chunk sau
  - Lý do: Tài liệu có cấu trúc rõ ràng (FAQ Q&A, Policy điều khoản, SOP bước)
    → giữ nguyên ranh giới ngữ nghĩa tự nhiên thay vì cắt cứng theo ký tự
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

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

# Chunk size 400 tokens ≈ 1600 chars tiếng Việt
# Overlap 80 tokens ≈ 320 chars — đủ để giữ ngữ cảnh giữa các chunk
CHUNK_SIZE = 400       # tokens (ước lượng bằng số ký tự / 4)
CHUNK_OVERLAP = 80     # tokens overlap giữa các chunk

# Embedding model — multilingual để hỗ trợ tiếng Việt
EMBEDDING_MODEL_NAME = os.getenv("LOCAL_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
_embedding_model = None  # Lazy-load singleton


# =============================================================================
# EMBEDDING MODEL — Lazy-load singleton
# =============================================================================

def _get_embedding_model():
    """Lazy-load SentenceTransformer model (chỉ tải 1 lần)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        print(f"  Loading embedding model: {EMBEDDING_MODEL_NAME}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


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
          - "title": tiêu đề tài liệu (dòng đầu tiên viết hoa)
    """
    lines = raw_text.strip().split("\n")

    def _extract_channels(text: str) -> List[str]:
        lowered = text.lower()
        channels = []
        channel_patterns = {
            "email": r"\bemail\b|@",
            "hotline": r"\bhotline\b|\bext\.\s*\d+\b",
            "slack": r"\bslack\b|#\w+",
            "jira": r"\bjira\b|\bproject\s+[A-Z]+-[A-Z]+\b",
            "portal": r"\bportal\b|https?://",
            "vpn": r"\bvpn\b",
        }

        for channel, pattern in channel_patterns.items():
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                channels.append(channel)

        return sorted(set(channels))

    def _extract_emails(text: str) -> List[str]:
        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        return sorted(set(emails))

    def _extract_hotlines(text: str) -> List[str]:
        # Captures formats like: ext. 9000, ext.9999, ext 1234
        hotline_matches = re.findall(r"\bext\.?\s*\d+\b", text, flags=re.IGNORECASE)
        return sorted(set(hotline_matches))

    def _extract_availability_hours(text: str) -> Optional[str]:
        # Prioritize explicit ranges with weekday hints found in these policy/faq docs.
        match = re.search(
            r"(Thứ\s*\d\s*-\s*Thứ\s*\d[^\n]*\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        # Fallback for common 24/7 notation.
        if re.search(r"\b24\s*/\s*7\b", text, flags=re.IGNORECASE):
            return "24/7"

        return None

    doc_title = ""
    metadata = {
        "doc_title": "",
        "source": filepath,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
        "channels": [],
        "emails": [],
        "hotlines": [],
        "availability_hours": None,
    }
    title = ""
    content_lines = []
    header_done = False
    notes_lines = []  # Ghi chú nằm giữa header và section đầu tiên

    for line in lines:
        stripped = line.strip()
        if not header_done:
            # Parse metadata từ các dòng "Key: Value"
            if stripped.startswith("Source:"):
                metadata["source"] = stripped.replace("Source:", "").strip()
            elif stripped.startswith("Department:"):
                metadata["department"] = stripped.replace("Department:", "").strip()
            elif stripped.startswith("Effective Date:"):
                metadata["effective_date"] = stripped.replace("Effective Date:", "").strip()
            elif stripped.startswith("Access:"):
                metadata["access"] = stripped.replace("Access:", "").strip()
            elif stripped.startswith("Ghi chú:") or stripped.startswith("Note:"):
                # Ghi chú quan trọng (ví dụ: tên cũ của tài liệu)
                notes_lines.append(stripped)
            elif stripped.startswith("==="):
                # Gặp section heading đầu tiên → kết thúc header
                header_done = True
                # Ghép notes vào đầu nội dung (quan trọng cho retrieval)
                if notes_lines:
                    content_lines.extend(notes_lines)
                    content_lines.append("")
                content_lines.append(line)
            elif stripped == "":
                continue
            elif stripped.isupper() or (len(stripped) > 10 and stripped == stripped.upper().replace("—", "—")):
                # Dòng tiêu đề tài liệu (toàn chữ hoa)
                title = stripped
                continue
            else:
                # Dòng khác trong header (có thể là ghi chú)
                notes_lines.append(stripped)
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)

    # Normalize: max 2 dòng trống liên tiếp, bỏ khoảng trắng thừa cuối dòng
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    cleaned_text = re.sub(r"[ \t]+$", "", cleaned_text, flags=re.MULTILINE)

    # Sprint 1: Thực hiện extraction và cleaning metadata
    # Gọi các helper đã định nghĩa ở trên
    metadata["channels"] = ", ".join(_extract_channels(cleaned_text))
    metadata["emails"] = ", ".join(_extract_emails(cleaned_text))
    metadata["hotlines"] = ", ".join(_extract_hotlines(cleaned_text))
    metadata["availability_hours"] = _extract_availability_hours(cleaned_text) or "unknown"
    metadata["doc_title"] = title

    # Đảm bảo metadata không chứa list rỗng hoặc None (ChromaDB 0.5+ validation)
    final_metadata = {}
    for k, v in metadata.items():
        if isinstance(v, list):
            # Nếu là list thì join lại thành string
            final_metadata[k] = ", ".join(map(str, v)) if v else ""
        elif v is None:
            final_metadata[k] = "unknown"
        else:
            final_metadata[k] = v

    return {
        "text": cleaned_text,
        "metadata": final_metadata,
        "title": title,
    }


# =============================================================================
# STEP 2: CHUNK
# Chia tài liệu thành các đoạn nhỏ theo cấu trúc tự nhiên
# Chiến lược: Section-based → Paragraph-aware splitting → Overlap
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Chunk một tài liệu đã preprocess thành danh sách các chunk nhỏ.

    Chiến lược Structural Chunking 2 cấp:
      Cấp 1: Split theo heading "=== ... ==="
      Cấp 2: Nếu section quá dài, split tiếp theo paragraph (\n\n)
      Overlap: Paragraph cuối chunk trước → đầu chunk sau

    Tại sao chọn chiến lược này:
      - Tài liệu FAQ có cặp Q/A → giữ nguyên trong 1 chunk
      - Policy có điều khoản + ngoại lệ → cùng section = cùng chunk
      - SOP có các bước → mỗi bước nằm trong 1 paragraph
      → Cắt theo cấu trúc tự nhiên giữ ngữ nghĩa tốt hơn cắt cứng theo ký tự
    """
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    title = doc.get("title", "")
    chunks = []

    # Bước 1: Split theo heading pattern "=== ... ==="
    sections = re.split(r"(===.*?===)", text)

    current_section = "General"
    current_section_text = ""

    for part in sections:
        if re.match(r"===.*?===", part):
            # Lưu section trước (nếu có nội dung)
            if current_section_text.strip():
                section_chunks = _split_by_paragraph(
                    current_section_text.strip(),
                    base_metadata=base_metadata,
                    section=current_section,
                    doc_title=title,
                )
                chunks.extend(section_chunks)
            # Bắt đầu section mới
            current_section = part.strip("= \r\n").strip()
            current_section_text = ""
        else:
            current_section_text += part

    # Lưu section cuối cùng
    if current_section_text.strip():
        section_chunks = _split_by_paragraph(
            current_section_text.strip(),
            base_metadata=base_metadata,
            section=current_section,
            doc_title=title,
        )
        chunks.extend(section_chunks)

    return chunks


def _split_by_paragraph(
    text: str,
    base_metadata: Dict,
    section: str,
    doc_title: str = "",
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_paragraphs: int = 1,
) -> List[Dict[str, Any]]:
    """
    Split text theo paragraph với overlap.

    Cải tiến so với cắt ký tự:
      1. Ưu tiên cắt tại ranh giới paragraph (\n\n)
      2. Overlap bằng số paragraph (không phải ký tự) → tự nhiên hơn
      3. Nếu 1 paragraph quá dài, fallback cắt tại dấu chấm câu
    """
    # Nếu toàn bộ section vừa 1 chunk → trả luôn
    if len(text) <= chunk_chars:
        chunk_text = text
        # Thêm doc_title vào đầu chunk để tăng context cho embedding
        if doc_title:
            chunk_text = f"[{doc_title}]\n{chunk_text}"
        return [{
            "text": chunk_text,
            "metadata": {**base_metadata, "section": section},
        }]

    # Split thành paragraphs
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    # Nếu chỉ có 1 paragraph dài → fallback cắt theo câu
    if len(paragraphs) <= 1:
        return _split_by_sentence(text, base_metadata, section, doc_title, chunk_chars)

    # Ghép paragraphs thành chunks
    chunks = []
    current_paras = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)

        # Nếu thêm paragraph này vượt quá chunk_chars → tạo chunk mới
        if current_len + para_len > chunk_chars and current_paras:
            chunk_text = "\n\n".join(current_paras)
            if doc_title:
                chunk_text = f"[{doc_title}]\n{chunk_text}"
            chunks.append({
                "text": chunk_text,
                "metadata": {**base_metadata, "section": section},
            })

            # Overlap: giữ lại N paragraph cuối
            if overlap_paragraphs > 0 and len(current_paras) > overlap_paragraphs:
                current_paras = current_paras[-overlap_paragraphs:]
                current_len = sum(len(p) for p in current_paras)
            else:
                current_paras = []
                current_len = 0

        current_paras.append(para)
        current_len += para_len

    # Chunk cuối cùng
    if current_paras:
        chunk_text = "\n\n".join(current_paras)
        if doc_title:
            chunk_text = f"[{doc_title}]\n{chunk_text}"
        chunks.append({
            "text": chunk_text,
            "metadata": {**base_metadata, "section": section},
        })

    return chunks


def _split_by_sentence(
    text: str,
    base_metadata: Dict,
    section: str,
    doc_title: str = "",
    chunk_chars: int = CHUNK_SIZE * 4,
) -> List[Dict[str, Any]]:
    """
    Fallback: Cắt text dài tại ranh giới câu (dấu chấm, dấu xuống dòng).
    Dùng khi 1 paragraph quá dài và không thể cắt theo paragraph.
    """
    # Split theo câu (dấu chấm + khoảng trắng hoặc xuống dòng)
    sentences = re.split(r'(?<=[.!?])\s+|(?<=\n)', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current_text = ""

    for sentence in sentences:
        if len(current_text) + len(sentence) > chunk_chars and current_text:
            chunk_text = current_text.strip()
            if doc_title:
                chunk_text = f"[{doc_title}]\n{chunk_text}"
            chunks.append({
                "text": chunk_text,
                "metadata": {**base_metadata, "section": section},
            })
            # Overlap: giữ lại câu cuối
            last_sentences = current_text.strip().split("\n")
            current_text = last_sentences[-1] + "\n" if last_sentences else ""

        current_text += sentence + "\n"

    if current_text.strip():
        chunk_text = current_text.strip()
        if doc_title:
            chunk_text = f"[{doc_title}]\n{chunk_text}"
        chunks.append({
            "text": chunk_text,
            "metadata": {**base_metadata, "section": section},
        })

    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text.
    Sử dụng Sentence Transformers local — model multilingual hỗ trợ tiếng Việt.
    """
    model = _get_embedding_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Batch embedding — nhanh hơn gọi từng cái một.
    SentenceTransformer tự xử lý batching nội bộ.
    """
    model = _get_embedding_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=True).tolist()


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → store.
    Sử dụng batch embedding để tối ưu tốc độ.
    """
    import chromadb
    from tqdm import tqdm

    print(f"Đang build index từ: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    # Khởi tạo ChromaDB với cosine similarity
    client = chromadb.PersistentClient(path=str(db_dir))

    # Xóa collection cũ nếu tồn tại (re-index sạch)
    try:
        client.delete_collection("rag_lab")
        print("  Đã xóa index cũ")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"}
    )

    total_chunks = 0
    doc_files = list(docs_dir.glob("*.txt"))

    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return

    # Thu thập tất cả chunks trước, rồi batch embed
    all_chunk_ids = []
    all_chunk_texts = []
    all_chunk_metadatas = []

    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")

        doc = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"
            all_chunk_ids.append(chunk_id)
            all_chunk_texts.append(chunk["text"])
            all_chunk_metadatas.append(chunk["metadata"])

        print(f"    → {len(chunks)} chunks")
        total_chunks += len(chunks)

    # Batch embed tất cả chunks (nhanh hơn nhiều so với embed từng cái)
    print(f"\n  Đang embed {total_chunks} chunks...")
    all_embeddings = get_embeddings_batch(all_chunk_texts)

    # Upsert vào ChromaDB (batch tối đa 5000)
    print(f"  Đang lưu vào ChromaDB...")
    batch_size = 500
    for start in tqdm(range(0, len(all_chunk_ids), batch_size), desc="  Indexing"):
        end = min(start + batch_size, len(all_chunk_ids))
        collection.upsert(
            ids=all_chunk_ids[start:end],
            embeddings=all_embeddings[start:end],
            documents=all_chunk_texts[start:end],
            metadatas=all_chunk_metadatas[start:end],
        )

    print(f"\n✓ Hoàn thành! Tổng số chunks đã index: {total_chunks}")
    print(f"  ChromaDB path: {db_dir}")
    print(f"  Collection: rag_lab ({collection.count()} vectors)")


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
    import sys

    print("=" * 60)
    print("Sprint 1: Build RAG Index")
    print("=" * 60)

    # Bước 1: Kiểm tra docs
    doc_files = list(DOCS_DIR.glob("*.txt"))
    print(f"\nTìm thấy {len(doc_files)} tài liệu:")
    for f in doc_files:
        print(f"  - {f.name} ({f.stat().st_size} bytes)")

    # Bước 2: Test preprocess và chunking
    print("\n--- Test preprocess + chunking ---")
    for filepath in doc_files:
        raw = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw, str(filepath))
        chunks = chunk_document(doc)
        print(f"\nFile: {filepath.name}")
        print(f"  Title: {doc.get('title', 'N/A')}")
        print(f"  Metadata: {doc['metadata']}")
        print(f"  Số chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks[:2]):
            print(f"  [Chunk {i+1}] Section: {chunk['metadata']['section']}")
            print(f"    Text preview: {chunk['text'][:120]}...")

    # Bước 3: Build full index
    print("\n--- Build Full Index ---")
    build_index()

    # Bước 4: Kiểm tra index
    print("\n--- Kiểm tra chất lượng index ---")
    list_chunks(n=5)
    inspect_metadata_coverage()

    print("\n✓ Sprint 1 hoàn thành!")
