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
    content_lines = []
    header_done = False

    for idx, line in enumerate(lines):
        if idx == 0 and line.strip():
            doc_title = line.strip()

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

    full_text_for_contact = "\n".join(lines)
    metadata["doc_title"] = doc_title
    metadata["channels"] = _extract_channels(full_text_for_contact)
    metadata["emails"] = _extract_emails(full_text_for_contact)
    metadata["hotlines"] = _extract_hotlines(full_text_for_contact)
    metadata["availability_hours"] = _extract_availability_hours(full_text_for_contact)

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

    def _split_faq_pairs(section_text: str) -> List[str]:
        """Split FAQ section into Q/A units, preserving question with answer."""
        lines = [ln.rstrip() for ln in section_text.splitlines()]
        qa_blocks = []
        current = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Q:"):
                if current:
                    qa_blocks.append("\n".join(current).strip())
                    current = []
                current.append(stripped)
            elif stripped:
                if current:
                    current.append(stripped)

        if current:
            qa_blocks.append("\n".join(current).strip())

        return qa_blocks

    def _is_contact_section(section_name: str, section_text: str) -> bool:
        """Detect contact/communication sections that should not be chunked."""
        name = section_name.lower()
        content = section_text.lower()

        name_signals = [
            "liên hệ",
            "lien he",
            "kênh liên lạc",
            "kenh lien lac",
            "công cụ",
            "cong cu",
            "hỗ trợ",
            "ho tro",
        ]
        if any(sig in name for sig in name_signals):
            return True

        # Fallback signal: contact-heavy block (metadata already captures these).
        contact_hits = 0
        if "@" in content or "email" in content:
            contact_hits += 1
        if re.search(r"\bhotline\b|\bext\.?\s*\d+\b", content):
            contact_hits += 1
        if "slack" in content:
            contact_hits += 1
        if "jira" in content or "portal" in content:
            contact_hits += 1
        return contact_hits >= 3

    # TODO: Implement chunking theo section heading
    # Bước 1: Split theo heading pattern "=== ... ==="
    sections = re.split(r"(===.*?===)", text)

    current_section = "General"
    current_section_text = ""

    for part in sections:
        if re.match(r"===.*?===", part):
            # Lưu section trước (nếu có nội dung)
            if current_section_text.strip():
                section_text = current_section_text.strip()

                if _is_contact_section(current_section, section_text):
                    section_chunks = []
                    chunks.extend(section_chunks)
                    current_section = part.strip("= ").strip()
                    current_section_text = ""
                    continue

                # FAQ docs/sections: ưu tiên 1 chunk cho mỗi cặp Q/A.
                is_faq_section = (
                    "faq" in current_section.lower()
                    or re.search(r"(?m)^\s*Q:\s*", section_text) is not None
                )

                if is_faq_section:
                    qa_blocks = _split_faq_pairs(section_text)
                    if qa_blocks:
                        section_chunks = []
                        for qa in qa_blocks:
                            section_chunks.extend(
                                _split_by_size(
                                    qa,
                                    base_metadata=base_metadata,
                                    section=current_section,
                                )
                            )
                    else:
                        section_chunks = _split_by_size(
                            section_text,
                            base_metadata=base_metadata,
                            section=current_section,
                        )
                else:
                    section_chunks = _split_by_size(
                        section_text,
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
        section_text = current_section_text.strip()
        if _is_contact_section(current_section, section_text):
            return chunks

        is_faq_section = (
            "faq" in current_section.lower()
            or re.search(r"(?m)^\s*Q:\s*", section_text) is not None
        )

        if is_faq_section:
            qa_blocks = _split_faq_pairs(section_text)
            if qa_blocks:
                section_chunks = []
                for qa in qa_blocks:
                    section_chunks.extend(
                        _split_by_size(
                            qa,
                            base_metadata=base_metadata,
                            section=current_section,
                        )
                    )
            else:
                section_chunks = _split_by_size(
                    section_text,
                    base_metadata=base_metadata,
                    section=current_section,
                )
        else:
            section_chunks = _split_by_size(
                section_text,
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

    # TODO: Implement split theo paragraph với overlap
    # Gợi ý:
    # paragraphs = text.split("\n\n")
    # Ghép paragraphs lại cho đến khi gần đủ chunk_chars
    # Lấy overlap từ đoạn cuối chunk trước
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []

    current_parts: List[str] = []
    current_len = 0

    def _join_parts(parts: List[str]) -> str:
        return "\n\n".join(parts).strip()

    def _tail_overlap(chunk_text: str) -> str:
        if overlap_chars <= 0:
            return ""
        tail = chunk_text[-overlap_chars:]
        # Cố gắng bắt đầu overlap tại ranh giới tự nhiên gần nhất.
        cut = max(tail.rfind("\n"), tail.rfind(". "), tail.rfind(": "), tail.rfind("; "))
        if cut > 0:
            tail = tail[cut + 1:]
        return tail.strip()

    for para in paragraphs:
        para_len = len(para)

        # Nếu paragraph đơn lẻ đã quá dài, cắt mềm theo sentence/newline boundaries.
        if para_len > chunk_chars:
            if current_parts:
                chunk_text = _join_parts(current_parts)
                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {**base_metadata, "section": section},
                    })
                overlap_text = _tail_overlap(chunk_text)
                current_parts = [overlap_text] if overlap_text else []
                current_len = len(overlap_text)

            start = 0
            while start < para_len:
                end = min(start + chunk_chars, para_len)
                window = para[start:end]

                if end < para_len:
                    natural_cut = max(
                        window.rfind("\n"),
                        window.rfind(". "),
                        window.rfind(": "),
                        window.rfind("; "),
                    )
                    if natural_cut > 100:
                        end = start + natural_cut + 1
                        window = para[start:end]

                piece = window.strip()
                if piece:
                    chunks.append({
                        "text": piece,
                        "metadata": {**base_metadata, "section": section},
                    })

                if end >= para_len:
                    break

                next_start = max(end - overlap_chars, start + 1)
                start = next_start

            current_parts = []
            current_len = 0
            continue

        projected = current_len + (2 if current_parts else 0) + para_len
        if projected <= chunk_chars:
            current_parts.append(para)
            current_len = projected
            continue

        chunk_text = _join_parts(current_parts)
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "metadata": {**base_metadata, "section": section},
            })

        overlap_text = _tail_overlap(chunk_text)
        current_parts = [overlap_text, para] if overlap_text else [para]
        current_len = sum(len(p) for p in current_parts) + (2 if len(current_parts) > 1 else 0)

    tail_chunk = _join_parts(current_parts)
    if tail_chunk:
        chunks.append({
            "text": tail_chunk,
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
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return model.encode(text).tolist()


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

    # TODO: Khởi tạo ChromaDB
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

        # TODO: Gọi preprocess_document
        doc = preprocess_document(raw_text, str(filepath))

        # TODO: Gọi chunk_document
        chunks = chunk_document(doc)

        # TODO: Embed và lưu từng chunk vào ChromaDB
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"
            embedding = get_embedding(chunk["text"])
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk["text"]],
                metadatas=[chunk["metadata"]],
            )
        total_chunks += len(chunks)

        # Placeholder để code không lỗi khi chưa implement
        # doc = preprocess_document(raw_text, str(filepath))
        # chunks = chunk_document(doc)
        # print(f"    → {len(chunks)} chunks (embedding chưa implement)")
        # total_chunks += len(chunks)

    print(f"\nHoàn thành! Tổng số chunks: {total_chunks}")
    # print("Lưu ý: Embedding chưa được implement. Xem TODO trong get_embedding() và build_index().")


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
    print("Lưu ý: Cần implement get_embedding() trước khi chạy bước này!")
    # Uncomment dòng dưới sau khi implement get_embedding():
    # build_index()

    # Bước 4: Kiểm tra index
    # Uncomment sau khi build_index() thành công:
    # list_chunks()
    # inspect_metadata_coverage()

    print("\nSprint 1 setup hoàn thành!")
    print("Việc cần làm:")
    print("  1. Implement get_embedding() - chọn OpenAI hoặc Sentence Transformers")
    print("  2. Implement phần TODO trong build_index()")
    print("  3. Chạy build_index() và kiểm tra với list_chunks()")
    print("  4. Nếu chunking chưa tốt: cải thiện _split_by_size() để split theo paragraph")
