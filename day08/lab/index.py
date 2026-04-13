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
CHROMA_DB_DIR = Path(os.getenv("CHROMA_DB_DIR", str(Path(os.getenv("TEMP", str(Path(__file__).parent))) / "day08_lab_chroma_db")))

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
            metadata_match = re.match(
                r"^(Source|Department|Effective Date|Access)\s*:\s*(.+?)\s*$",
                line.strip(),
            )
            if metadata_match:
                key, value = metadata_match.groups()
                key_map = {
                    "Source": "source",
                    "Department": "department",
                    "Effective Date": "effective_date",
                    "Access": "access",
                }
                metadata[key_map[key]] = value.strip()
                continue
            if line.startswith("==="):
                # Gặp section heading đầu tiên → kết thúc header
                header_done = True
                content_lines.append(line)
            elif line.strip() == "" or line.isupper():
                # Dòng tên tài liệu (toàn chữ hoa) hoặc dòng trống
                continue
            else:
                header_done = True
                content_lines.append(line.strip())
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)

    # TODO: Thêm bước normalize text nếu cần
    # Gợi ý: bỏ ký tự đặc biệt thừa, chuẩn hóa dấu câu
    cleaned_text = cleaned_text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)
    cleaned_text = re.sub(r" *\n *", "\n", cleaned_text)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()  # max 2 dòng trống liên tiếp

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
    sections = re.split(r"(?m)^(===.*?===)\s*$", text)

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
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        chunk_text = text[start:end]

        # TODO: Tìm ranh giới tự nhiên gần nhất (dấu xuống dòng, dấu chấm)
        # thay vì cắt giữa câu
        break

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    prepared_parts = []

    for paragraph in paragraphs:
        remaining = paragraph
        while len(remaining) > chunk_chars:
            split_at = max(
                remaining.rfind("\n", 0, chunk_chars),
                remaining.rfind(". ", 0, chunk_chars),
                remaining.rfind("! ", 0, chunk_chars),
                remaining.rfind("? ", 0, chunk_chars),
                remaining.rfind("; ", 0, chunk_chars),
                remaining.rfind(": ", 0, chunk_chars),
                remaining.rfind(" ", 0, chunk_chars),
            )
            if split_at <= chunk_chars // 3:
                split_at = chunk_chars
            prepared_parts.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        if remaining:
            prepared_parts.append(remaining)

    chunks = []
    current_text = ""

    for part in prepared_parts:
        candidate = f"{current_text}\n\n{part}".strip() if current_text else part
        if current_text and len(candidate) > chunk_chars:
            chunk_text = current_text.strip()
            chunks.append({
                "text": chunk_text,
                "metadata": {**base_metadata, "section": section},
            })

            overlap_text = chunk_text[-overlap_chars:].strip()
            if overlap_text and " " in overlap_text:
                overlap_text = overlap_text.split(" ", 1)[1]
            candidate = f"{overlap_text}\n\n{part}".strip() if overlap_text else part
            current_text = candidate if len(candidate) <= chunk_chars else part
        else:
            current_text = candidate

    if current_text.strip():
        chunks.append({
            "text": current_text.strip(),
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
    normalized_text = re.sub(r"\s+", " ", text).strip() or " "
    provider = os.getenv("EMBEDDING_PROVIDER", "local").strip().lower()

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            client = getattr(get_embedding, "_openai_client", None)
            if client is None:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                get_embedding._openai_client = client

            response = client.embeddings.create(
                input=normalized_text,
                model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            )
            return response.data[0].embedding
        except Exception as exc:
            if not getattr(get_embedding, "_warned_openai", False):
                print(f"[Embedding] OpenAI không sẵn sàng, fallback local/hash: {exc}")
                get_embedding._warned_openai = True

    try:
        model = getattr(get_embedding, "_local_model", None)
        if model is None:
            from sentence_transformers import SentenceTransformer
            model_name = os.getenv(
                "LOCAL_EMBEDDING_MODEL",
                "paraphrase-multilingual-MiniLM-L12-v2",
            )
            try:
                model = SentenceTransformer(model_name, local_files_only=True)
            except TypeError:
                model = SentenceTransformer(model_name)
            get_embedding._local_model = model
        return model.encode(normalized_text).tolist()
    except Exception as exc:
        if not getattr(get_embedding, "_warned_hash", False):
            print(f"[Embedding] Không load được sentence-transformers, dùng fallback offline: {exc}")
            get_embedding._warned_hash = True

        dim = 384
        vector = [0.0] * dim
        tokens = re.findall(r"\w+|\S", normalized_text.lower())
        for idx, token in enumerate(tokens):
            bucket = sum(ord(char) for char in token) % dim
            vector[bucket] += 1.0 + (idx % 11) * 0.01

        norm = sum(value * value for value in vector) ** 0.5 or 1.0
        return [value / norm for value in vector]
    raise NotImplementedError(
        "TODO: Implement get_embedding().\n"
        "Chọn Option A (OpenAI) hoặc Option B (Sentence Transformers) trong TODO comment."
    )


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
    try:
        client = chromadb.PersistentClient(path=str(db_dir))
    except Exception as exc:
        import shutil

        print(f"[ChromaDB] Không mở được DB cũ, đang reset thư mục index: {exc}")
        shutil.rmtree(db_dir, ignore_errors=True)
        db_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(db_dir))
    try:
        client.delete_collection("rag_lab")
    except Exception:
        pass
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
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"
            embedding = get_embedding(chunk["text"])
            metadata = {}
            for key, value in chunk["metadata"].items():
                if value is None:
                    continue
                if isinstance(value, (str, int, float, bool)):
                    metadata[key] = value
                else:
                    metadata[key] = json.dumps(value, ensure_ascii=False)
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk["text"]],
                metadatas=[metadata],
            )
        print(f"    → {len(chunks)} chunks đã index")
        total_chunks += len(chunks)

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
        missing_source = 0
        source_counts = {}
        for meta in results["metadatas"]:
            dept = meta.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1
            source = meta.get("source", "")
            if source in ("", None):
                missing_source += 1
            else:
                source_counts[source] = source_counts.get(source, 0) + 1
            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1

        print("Phân bố theo department:")
        for dept, count in departments.items():
            print(f"  {dept}: {count} chunks")
        print("Phân bố theo source:")
        for source, count in source_counts.items():
            print(f"  {source}: {count} chunks")
        print(f"Chunks thiếu source: {missing_source}")
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
    build_index()

    # Bước 4: Kiểm tra index
    # Uncomment sau khi build_index() thành công:
    list_chunks()
    inspect_metadata_coverage()

    print("\nSprint 1 setup hoàn thành!")
    print("Việc cần làm:")
    print("  1. Implement get_embedding() - chọn OpenAI hoặc Sentence Transformers")
    print("  2. Implement phần TODO trong build_index()")
    print("  3. Chạy build_index() và kiểm tra với list_chunks()")
    print("  4. Nếu chunking chưa tốt: cải thiện _split_by_size() để split theo paragraph")
