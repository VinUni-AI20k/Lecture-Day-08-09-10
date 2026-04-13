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

# [RO] Sprint 1: Chunk size và overlap — quyết định chunking của Retrieval Owner
# Slide gợi ý: 300–500 tokens, overlap 50–80 tokens
# Với corpus policy (văn bản ngắn, nhiều điều khoản riêng biệt) dùng 400/80 là hợp lý
CHUNK_SIZE = 400       # tokens (ước lượng: 1 token ≈ 4 ký tự tiếng Việt)
CHUNK_OVERLAP = 80     # tokens overlap để chunk sau có ngữ cảnh từ chunk trước

# [RO] Sprint 1: Global embedding model (tránh load model nhiều lần)
_embedding_model = None


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
            elif line.strip() == "":
                # Dòng trống trong header → bỏ qua
                continue
            elif not any(line.startswith(k) for k in ("Source:", "Department:", "Effective Date:", "Access:")):
                # [TL] Fix: line.isupper() fails for Vietnamese diacritics ("CHÍNH SÁCH..." → False)
                # Bất kỳ dòng nào trong header mà không phải Key: Value → là tiêu đề tài liệu, bỏ qua
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
    [RO] Sprint 1: Split text dài thành chunks theo paragraph với overlap.

    Cải tiến so với code gốc:
    - Cắt tại ranh giới paragraph (\\n\\n) thay vì cắt cứng theo ký tự
    - Thêm overlap: đoạn cuối chunk trước được đưa vào đầu chunk tiếp theo
    - Kết quả: chunk không bao giờ bị cắt giữa câu quan trọng
    """
    # Nếu toàn bộ section vừa một chunk → trả về nguyên
    if len(text) <= chunk_chars:
        return [{
            "text": text,
            "metadata": {**base_metadata, "section": section},
        }]

    # Split theo paragraph (ranh giới tự nhiên)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_parts: List[str] = []
    current_len = 0
    last_overlap_text = ""

    for para in paragraphs:
        para_len = len(para) + 2  # +2 cho "\n\n" khi join

        if current_len + para_len <= chunk_chars:
            # Paragraph này vẫn vừa → ghép vào chunk hiện tại
            current_parts.append(para)
            current_len += para_len
        else:
            # Flush chunk hiện tại (nếu có)
            if current_parts:
                chunk_text = (last_overlap_text + "\n\n" if last_overlap_text else "") \
                             + "\n\n".join(current_parts)
                chunks.append({
                    "text": chunk_text.strip(),
                    "metadata": {**base_metadata, "section": section},
                })
                # Lấy đoạn cuối làm overlap cho chunk tiếp theo
                joined = "\n\n".join(current_parts)
                last_overlap_text = joined[-overlap_chars:] if len(joined) > overlap_chars else joined

            # Bắt đầu chunk mới với paragraph này
            current_parts = [para]
            current_len = len(para)

    # Flush chunk cuối cùng
    if current_parts:
        chunk_text = (last_overlap_text + "\n\n" if last_overlap_text else "") \
                     + "\n\n".join(current_parts)
        chunks.append({
            "text": chunk_text.strip(),
            "metadata": {**base_metadata, "section": section},
        })

    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """
    [RO] Sprint 1: Tạo embedding vector bằng OpenAI text-embedding-3-small.

    Dùng OpenAI vì:
    - Chất lượng cao hơn local model cho tiếng Việt
    - OPENAI_API_KEY đã có sẵn trong .env
    - Dimension 1536 — đủ để phân biệt các điều khoản policy

    Lưu ý: Phải dùng cùng model này trong rag_answer.py khi retrieve.
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    [RO] Sprint 1: Pipeline hoàn chỉnh — đọc docs → preprocess → chunk → embed → store.

    Flow:
      data/docs/*.txt → preprocess_document() → chunk_document() → get_embedding() → ChromaDB

    ChromaDB lưu 3 thứ cho mỗi chunk:
      - embedding: vector số học để tìm kiếm theo cosine similarity
      - document: nội dung text gốc
      - metadata: source, section, effective_date, department, access
    """
    import chromadb

    print(f"Đang build index từ: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    # Khởi tạo ChromaDB PersistentClient — lưu xuống disk, tồn tại sau khi script tắt
    client = chromadb.PersistentClient(path=str(db_dir))

    # Xóa collection cũ nếu có (để re-index sạch)
    try:
        client.delete_collection("rag_lab")
        print("  Đã xóa index cũ — re-indexing...")
    except Exception:
        pass  # Lần đầu chạy, chưa có collection → bỏ qua

    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"}  # cosine similarity cho text embedding
    )

    total_chunks = 0
    doc_files = sorted(docs_dir.glob("*.txt"))  # sorted để output nhất quán

    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return

    for filepath in doc_files:
        print(f"\n  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")

        # Bước 1: Preprocess — extract metadata, làm sạch text
        doc = preprocess_document(raw_text, str(filepath))
        print(f"    Metadata: source={doc['metadata']['source']}, "
              f"dept={doc['metadata']['department']}, "
              f"date={doc['metadata']['effective_date']}")

        # Bước 2: Chunk — chia theo section + paragraph
        chunks = chunk_document(doc)
        print(f"    Chunks: {len(chunks)}")

        # Bước 3: Embed và lưu từng chunk vào ChromaDB
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"  # ID duy nhất: "policy_refund_v4_0"
            embedding = get_embedding(chunk["text"])
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk["text"]],
                metadatas=[chunk["metadata"]],
            )

        total_chunks += len(chunks)
        print(f"    ✓ Indexed {len(chunks)} chunks")

    print(f"\n{'='*50}")
    print(f"Hoàn thành! Tổng số chunks đã index: {total_chunks}")
    print(f"Database lưu tại: {db_dir}")
    print(f"{'='*50}")


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

    # -----------------------------------------------------------------------
    # PHASE 1: Kiểm tra docs và preview chunking (không cần API key)
    # -----------------------------------------------------------------------
    doc_files = sorted(DOCS_DIR.glob("*.txt"))
    print(f"\n[1] Tìm thấy {len(doc_files)} tài liệu:")
    for f in doc_files:
        print(f"  - {f.name}")

    print("\n[2] Preview preprocess + chunking cho TẤT CẢ docs:")
    print("-" * 50)
    for filepath in doc_files:
        raw = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw, str(filepath))
        chunks = chunk_document(doc)
        print(f"\nFile: {filepath.name}")
        print(f"  source       = {doc['metadata']['source']}")
        print(f"  department   = {doc['metadata']['department']}")
        print(f"  effective_date = {doc['metadata']['effective_date']}")
        print(f"  Số chunks    = {len(chunks)}")
        for i, chunk in enumerate(chunks[:2]):  # Xem 2 chunk đầu mỗi file
            print(f"  [Chunk {i}] section='{chunk['metadata']['section']}'")
            print(f"            len={len(chunk['text'])} chars")
            print(f"            preview: '{chunk['text'][:80].strip()}...'")

    # -----------------------------------------------------------------------
    # PHASE 2: Build full index (yêu cầu OPENAI_API_KEY)
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("[3] Build Full Index...")
    print("=" * 60)
    build_index()

    # -----------------------------------------------------------------------
    # PHASE 3: Kiểm tra index sau khi build
    # -----------------------------------------------------------------------
    print("\n[4] Kiểm tra chất lượng index:")
    print("-" * 50)
    list_chunks(n=5)

    print("\n[5] Kiểm tra metadata coverage:")
    print("-" * 50)
    inspect_metadata_coverage()

    print("\n" + "=" * 60)
    print("Sprint 1 hoàn thành!")
    print("Bước tiếp theo: Tech Lead implement retrieve_dense() trong rag_answer.py")
    print("=" * 60)
