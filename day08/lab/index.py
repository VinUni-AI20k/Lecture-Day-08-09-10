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
    current_chunk = []
    current_length = 0
    for para in paragraphs:
        para_len = len(para)
        if current_length + para_len > chunk_chars and current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "metadata": {**base_metadata, "section": section},
            })
            # TODO: Tìm ranh giới tự nhiên gần nhất (dấu xuống dòng, dấu chấm)
            # thay vì cắt giữa câu
            overlap = []
            overlap_len = 0
            for p in reversed(current_chunk):
                overlap.insert(0, p)
                overlap_len += len(p)
                if overlap_len >= overlap_chars:
                    break
            current_chunk = overlap
            current_length = overlap_len
        current_chunk.append(para)
        current_length += para_len
    if current_chunk:
        chunks.append({
            "text": "\n\n".join(current_chunk),
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
    model = SentenceTransformer("AITeamVN/Vietnamese_Embedding")
    return model.encode(text).tolist()
    # raise NotImplementedError(
    #     "TODO: Implement get_embedding().\n"
    #     "Chọn Option A (OpenAI) hoặc Option B (Sentence Transformers) trong TODO comment."
    # )


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
    # client = chromadb.PersistentClient(path=str(db_dir))
    # collection = client.get_or_create_collection(...)

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
        # doc = preprocess_document(raw_text, str(filepath))
        doc = preprocess_document(raw_text, str(filepath))
        # TODO: Gọi chunk_document
        # chunks = chunk_document(doc)
        chunks = chunk_document(doc)
        # TODO: Embed và lưu từng chunk vào ChromaDB
        # for i, chunk in enumerate(chunks):
        #     chunk_id = f"{filepath.stem}_{i}"
        #     embedding = get_embedding(chunk["text"])
        #     collection.upsert(
        #         ids=[chunk_id],
        #         embeddings=[embedding],
        #         documents=[chunk["text"]],
        #         metadatas=[chunk["metadata"]],
        #     )
        # total_chunks += len(chunks)
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"

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
    print("Lưu ý: Embedding đã được implement. Xem TODO trong get_embedding() và build_index().")


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
        metadatas = results["metadatas"]
        total = len(metadatas)

        print(f"\nTổng chunks: {total}")

        # TODO: Phân tích metadata
        # Đếm theo department, kiểm tra effective_date missing, v.v.
        departments = {}
        missing_date = 0
        missing_source = 0
        for meta in results["metadatas"]:
            if not meta.get("source"):
                missing_source += 1
            dept = meta.get("department", "unknown")
            dept = dept.strip().lower() if isinstance(dept, str) else "unknown"
            departments[dept] = departments.get(dept, 0) + 1
            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1

        print("Phân bố theo department:")
        for dept, count in departments.items():
            percent = count / total * 100
            print(f"  {dept}: {count} chunks ({percent:.2f}%)")
        print(f"Chunks thiếu effective_date: {missing_date} ({missing_date/total:.2%})")
        print(f"Chunks thiếu source: {missing_source} ({missing_source/total:.2%})")
        print("\n Department có ít dữ liệu (outliers):")
        for dept, count in departments.items():
            if count < 3:
                print(f"  {dept}: chỉ {count} chunks")
    except Exception as e:
        print(f"Lỗi: {e}. Hãy chạy build_index() trước.")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 1: Build RAG Index (Validation Mode)")
    print("=" * 60)

    # =========================
    # 1. CHECK INPUT DOCS
    # =========================
    doc_files = list(DOCS_DIR.glob("*.txt"))
    print(f"\n Tìm thấy {len(doc_files)} tài liệu")

    assert len(doc_files) > 0, "Không có file .txt nào!"

    for f in doc_files:
        print(f"  - {f.name}")

    # =========================
    # 2. TEST PREPROCESS
    # =========================
    print("\n Test preprocess_document()")

    filepath = doc_files[0]
    raw = filepath.read_text(encoding="utf-8")

    doc = preprocess_document(raw, str(filepath))

    # ✅ Check metadata
    assert "text" in doc, " Missing text"
    assert "metadata" in doc, " Missing metadata"

    metadata = doc["metadata"]
    required_fields = ["source", "department", "effective_date"]

    for field in required_fields:
        assert field in metadata, f" Missing metadata field: {field}"

    print("   Metadata OK")
    print(f"  → {metadata}")

    # =========================
    # 3. TEST CHUNKING
    # =========================
    print("\n Test chunk_document()")

    chunks = chunk_document(doc)

    assert len(chunks) > 0, " Không tạo được chunk!"

    print(f"  → Số chunks: {len(chunks)}")

    # ✅ Check từng chunk
    for i, chunk in enumerate(chunks):
        assert "text" in chunk, f" Chunk {i} missing text"
        assert "metadata" in chunk, f" Chunk {i} missing metadata"

        # Metadata phải giữ nguyên
        for field in required_fields:
            assert field in chunk["metadata"], f" Chunk {i} thiếu metadata {field}"

        # Không chunk quá dài
        assert len(chunk["text"]) <= CHUNK_SIZE * 4 + 200, " Chunk quá dài"

    print("  ✅ Chunk structure OK")

    # =========================
    # 4. CHECK CHUNK QUALITY
    # =========================
    print("\n Kiểm tra chất lượng chunk")

    bad_chunks = 0

    for chunk in chunks:
        text = chunk["text"].strip()

        # check cắt giữa câu
        if not text.endswith((".", "!", "?", ":")):
            bad_chunks += 1

    print(f" Chunk có thể bị cắt giữa câu: {bad_chunks}/{len(chunks)}")

    # =========================
    # 5. SAVE DEBUG FILE
    # =========================
    with open("debug_chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print("  💾 Đã lưu debug_chunks.json")

    # =========================
    # 6. TEST EMBEDDING
    # =========================
    print("\n Test get_embedding()")

    try:
        test_embedding = get_embedding(chunks[0]["text"])

        assert isinstance(test_embedding, list), " Embedding không phải list"
        assert len(test_embedding) > 0, " Embedding rỗng"

        print(f"  Embedding OK (dim = {len(test_embedding)})")

    except Exception as e:
        print(f"  Embedding chưa sẵn sàng: {e}")

    # =========================
    # 7. BUILD INDEX
    # =========================
    print("\n Build index")

    try:
        build_index()

        print("  Index build thành công")

        # =========================
        # 8. VERIFY INDEX
        # =========================
        print("\n Verify index")

        list_chunks(n=3)
        inspect_metadata_coverage()

        print("   Index verification OK")

    except Exception as e:
        print(f"  Lỗi build index: {e}")

    print("\n Sprint 1 validation hoàn thành!")
