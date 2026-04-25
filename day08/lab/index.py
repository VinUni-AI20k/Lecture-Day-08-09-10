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
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        chunk_text = text[start:end]

        # TODO: Tìm ranh giới tự nhiên gần nhất (dấu xuống dòng, dấu chấm)
        # thay vì cắt giữa câu

        chunks.append({
            "text": chunk_text,
            "metadata": {**base_metadata, "section": section},
        })
        # Overlap: lùi lại overlap_chars để chunk sau có ngữ cảnh từ chunk trước
        start = end - overlap_chars

    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

# Cache model để tránh load lại mỗi lần gọi
_sentence_model = None


def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text.
    Tự động chọn provider dựa theo biến EMBEDDING_PROVIDER trong .env:
      - "openai"  → OpenAI text-embedding-3-small (cần OPENAI_API_KEY)
      - "gemini"  → Google Generative AI embedding (cần GOOGLE_API_KEY)
      - "local"   → Sentence Transformers (chạy hoàn toàn offline)
    Mặc định fallback về "local" nếu không xác định được provider.
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "local").lower()

    # ------------------------------------------------------------------ #
    # Option A — OpenAI Embeddings                                         #
    # ------------------------------------------------------------------ #
    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small",
        )
        return response.data[0].embedding

    # ------------------------------------------------------------------ #
    # Option B — Google Gemini Embeddings                                  #
    # ------------------------------------------------------------------ #
    elif provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]

    # ------------------------------------------------------------------ #
    # Option C — Sentence Transformers (local, không cần API key)          #
    # ------------------------------------------------------------------ #
    else:  # "local" hoặc fallback
        global _sentence_model
        if _sentence_model is None:
            from sentence_transformers import SentenceTransformer
            model_name = os.getenv(
                "LOCAL_EMBEDDING_MODEL",
                "paraphrase-multilingual-MiniLM-L12-v2",
            )
            print(f"  [Embedding] Loading local model: {model_name}")
            _sentence_model = SentenceTransformer(model_name)
        return _sentence_model.encode(text).tolist()


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → store.

    Step 3 — Đã implement:
    1. Khởi tạo ChromaDB PersistentClient
    2. Tạo/lấy collection "rag_lab" với cosine similarity
    3. Với mỗi file .txt trong docs_dir:
       a. Đọc nội dung
       b. Preprocess (extract metadata, clean text)
       c. Chunk theo section + size
       d. Embed từng chunk và upsert vào ChromaDB
    4. In tổng số chunk đã index
    """
    import chromadb
    from tqdm import tqdm

    print(f"[build_index] Đang build index từ: {docs_dir}")
    print(f"[build_index] Lưu ChromaDB tại: {db_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    # --- Khởi tạo ChromaDB ---
    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"},
    )
    print(f"[build_index] Collection 'rag_lab' sẵn sàng (hiện có {collection.count()} chunks)")

    total_chunks = 0
    doc_files = list(docs_dir.glob("*.txt"))

    if not doc_files:
        print(f"[build_index] Không tìm thấy file .txt trong {docs_dir}")
        return

    for filepath in tqdm(doc_files, desc="Indexing documents"):
        raw_text = filepath.read_text(encoding="utf-8")

        # Preprocess: extract metadata + clean text
        doc = preprocess_document(raw_text, str(filepath))

        # Chunk theo section/size
        chunks = chunk_document(doc)

        # Embed và upsert từng chunk vào ChromaDB
        ids, embeddings, documents, metadatas = [], [], [], []
        for i, chunk in enumerate(tqdm(chunks, desc=f"  Embedding {filepath.name}", leave=False)):
            chunk_id = f"{filepath.stem}_{i}"
            embedding = get_embedding(chunk["text"])
            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk["text"])
            metadatas.append(chunk["metadata"])

        # Batch upsert (hiệu quả hơn upsert từng cái)
        if ids:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

        total_chunks += len(chunks)
        print(f"  ✓ {filepath.name}: {len(chunks)} chunks đã index")

    print(f"\n[build_index] Hoàn thành! Tổng chunks đã index: {total_chunks}")
    print(f"[build_index] Collection hiện có: {collection.count()} chunks")


# =============================================================================
# STEP 4: INSPECT / KIỂM TRA
# Dùng để debug và kiểm tra chất lượng index
# =============================================================================

def list_chunks(db_dir: Path = CHROMA_DB_DIR, n: int = 5) -> None:
    """
    In ra n chunk đầu tiên trong ChromaDB để kiểm tra chất lượng index.
    Checklist:
    - Tự động thông báo [OK] / [MISSING] cho từng metadata field
    - Cảnh báo nếu chunk bị cắt giữa câu (ký tự cuối không phải dấu chấm / xuống dòng)
    - Kiểm tra effective_date có đúng không
    """
    REQUIRED_FIELDS = ["source", "section", "department", "effective_date", "access"]

    def _tag(value: Any, field: str) -> str:
        """Trả về [OK] nếu field hợp lệ, [MISSING] nếu thiếu."""
        if value in (None, "", "unknown"):
            return f"\033[91m[MISSING]\033[0m {value!r}"
        return f"\033[92m[OK]\033[0m {value}"

    def _check_cut(text: str) -> str:
        """Kiểm tra chunk có bị cắt giữa câu không."""
        last_char = text.rstrip()[-1] if text.strip() else ""
        if last_char not in (".", "!", "?", ":", "\n", "—", "-"):
            return f"\033[93m[WARN] Có thể bị cắt giữa câu (kỳ tự cuối: {last_char!r})\033[0m"
        return "\033[92m[OK] Kết thúc tự nhiên\033[0m"

    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(limit=n, include=["documents", "metadatas"])

        print(f"\n=== Top {n} chunks trong index ===\n")
        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"[Chunk {i+1}]")
            for field in REQUIRED_FIELDS:
                print(f"  {field:<15}: {_tag(meta.get(field), field)}")
            print(f"  {'cut_check':<15}: {_check_cut(doc)}")
            print(f"  {'text_preview':<15}: {doc[:150]}...")
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
    - Có bao nhiêu chunk từ mỗi source file?
    - Có bao nhiêu chunk theo access level?
    - Chunk nào thiếu effective_date?
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(include=["documents", "metadatas"])

        total = len(results["metadatas"])
        print(f"\n=== Metadata Coverage Report ===")
        print(f"Tổng chunks: {total}")

        departments: Dict[str, int] = {}
        access_levels: Dict[str, int] = {}
        sources: Dict[str, int] = {}
        missing_date = 0
        missing_source = 0
        cut_warnings = 0

        for doc, meta in zip(results["documents"], results["metadatas"]):
            # Đếm theo department
            dept = meta.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1

            # Đếm theo access level
            access = meta.get("access", "unknown")
            access_levels[access] = access_levels.get(access, 0) + 1

            # Đếm theo source file
            src = meta.get("source", "unknown")
            src_key = Path(src).name if src not in ("", None, "unknown") else "unknown"
            sources[src_key] = sources.get(src_key, 0) + 1

            # Kiểm tra missing fields
            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1
            if meta.get("source") in ("", None):
                missing_source += 1

            # Kiểm tra cắt giữa câu
            last_char = doc.rstrip()[-1] if doc.strip() else ""
            if last_char not in (".", "!", "?", ":", "\n", "—", "-"):
                cut_warnings += 1

        print("\nPhân bố theo department:")
        for dept, count in sorted(departments.items()):
            print(f"  {dept}: {count} chunks ({count/total*100:.1f}%)")

        print("\nPhân bố theo source file:")
        for src, count in sorted(sources.items()):
            print(f"  {src}: {count} chunks ({count/total*100:.1f}%)")

        print("\nPhân bố theo access level:")
        for level, count in sorted(access_levels.items()):
            print(f"  {level}: {count} chunks ({count/total*100:.1f}%)")

        print(f"\nChunks thiếu effective_date : {missing_date}/{total}")
        print(f"Chunks thiếu source         : {missing_source}/{total}")
        print(f"Chunks có thể bị cắt câu  : {cut_warnings}/{total}")
        if cut_warnings > 0:
            print("  → Gợi ý: cải thiện _split_by_size() để cắt tại ranh giới tự nhiên.")

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
    print("\n--- Build Full Index (Step 3) ---")
    build_index()

    # Bước 4: Kiểm tra index
    print("\n--- Kiểm tra Index (Step 4) ---")
    list_chunks(n=5)
    inspect_metadata_coverage()

    print("\n✅ Sprint 1 hoàn thành!")
