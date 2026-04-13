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
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv, dotenv_values

BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = BASE_DIR / "data" / "docs"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"

# TODO Sprint 1: Điều chỉnh chunk size và overlap theo quyết định của nhóm
# Gợi ý từ slide: chunk 300-500 tokens, overlap 50-80 tokens
CHUNK_SIZE = 400       # tokens (ước lượng bằng số ký tự / 4)
CHUNK_OVERLAP = 80     # tokens overlap giữa các chunk
CHUNK_DUMP_PATH = BASE_DIR / "docs" / "chunks" / "indexed_chunks.jsonl"


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
        "source": Path(filepath).name,  # keep source compact
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }

    # Map header keys -> metadata keys (case-insensitive)
    header_key_map = {
        "source": "source",
        "department": "department",
        "effective date": "effective_date",
        "access": "access",
    }

    content_start = 0
    for i, raw_line in enumerate(lines):
        line = raw_line.strip()

        # Skip empty/title lines in header area
        if not line or line.isupper():
            continue

        # Section marker means header ended
        if re.match(r"^===.*===$", line):
            content_start = i
            break

        # Parse "Key: Value"
        m = re.match(r"^([A-Za-z ]+)\s*:\s*(.+)$", line)
        if m:
            key = m.group(1).strip().lower()
            value = m.group(2).strip()
            if key in header_key_map and value:
                metadata[header_key_map[key]] = value
            content_start = i + 1
            continue

        # Any non-header line: body starts here
        content_start = i
        break
    else:
        # all lines consumed (rare)
        content_start = len(lines)

    content_lines = lines[content_start:]
    cleaned_text = "\n".join(content_lines)

    # Normalize whitespace/noise
    cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)      # collapse spaces/tabs
    cleaned_text = re.sub(r"\n[ \t]+", "\n", cleaned_text)   # trim indentation artifacts
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)   # max 2 blank lines
    cleaned_text = cleaned_text.strip()

    return {"text": cleaned_text, "metadata": metadata}


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
    text = doc["text"].strip()
    base_metadata = doc["metadata"].copy()
    chunks: List[Dict[str, Any]] = []

    if not text:
        return chunks

    heading_re = re.compile(r"^===\s*(.*?)\s*===$", re.MULTILINE)
    matches = list(heading_re.finditer(text))

    if not matches:
        return _split_by_size(
            text,
            base_metadata=base_metadata,
            section="General",
        )

    # Nội dung trước heading đầu tiên (nếu có)
    preface = text[:matches[0].start()].strip()
    if preface:
        chunks.extend(
            _split_by_size(
                preface,
                base_metadata=base_metadata,
                section="General",
            )
        )

    # Tách từng section theo heading
    for i, match in enumerate(matches):
        section_name = match.group(1).strip() or "General"
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()

        if not section_text:
            continue

        chunks.extend(
            _split_by_size(
                section_text,
                base_metadata=base_metadata,
                section=section_name,
            )
        )

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
    clean_text = text.strip()
    if not clean_text:
        return []

    if len(clean_text) <= chunk_chars:
        return [{
            "text": clean_text,
            "metadata": {**base_metadata, "section": section},
        }]

    overlap_chars = min(overlap_chars, max(chunk_chars // 2, 1))

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", clean_text) if p.strip()]
    if not paragraphs:
        paragraphs = [clean_text]

    chunks: List[Dict[str, Any]] = []
    current = ""

    def flush_current() -> None:
        nonlocal current
        chunk_text = current.strip()
        if not chunk_text:
            return
        chunks.append({
            "text": chunk_text,
            "metadata": {**base_metadata, "section": section},
        })
        current = ""

    for para in paragraphs:
        if len(para) > chunk_chars:
            flush_current()

            start = 0
            while start < len(para):
                end = min(start + chunk_chars, len(para))
                window = para[start:end]

                # Ưu tiên cắt ở ranh giới tự nhiên nếu có
                if end < len(para):
                    candidates = [window.rfind("\n"), window.rfind(". "), window.rfind("; "), window.rfind(", ")]
                    cut_at = max(candidates)
                    if cut_at >= int(chunk_chars * 0.6):
                        end = start + cut_at + 1
                        window = para[start:end]

                chunk_text = window.strip()
                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {**base_metadata, "section": section},
                    })

                if end >= len(para):
                    break

                next_start = end - overlap_chars
                start = next_start if next_start > start else end
            continue

        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= chunk_chars:
            current = candidate
            continue

        flush_current()
        current = para

    flush_current()

    # Thêm overlap giữa các chunk ngắn để giữ ngữ cảnh
    if len(chunks) <= 1 or overlap_chars <= 0:
        return chunks

    overlapped: List[Dict[str, Any]] = []
    for i, item in enumerate(chunks):
        if i == 0:
            overlapped.append(item)
            continue

        prev_tail = chunks[i - 1]["text"][-overlap_chars:].strip()
        curr_text = item["text"]
        merged_text = f"{prev_tail}\n{curr_text}" if prev_tail else curr_text
        if len(merged_text) > chunk_chars + overlap_chars:
            merged_text = merged_text[-(chunk_chars + overlap_chars):]

        overlapped.append({
            "text": merged_text,
            "metadata": item["metadata"],
        })

    return overlapped


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text.

    TODO Sprint 1:
    Chọn một trong hai:

    Option A — OpenAI-compatible Embeddings (cần CUSTOM_API_KEY):

        client = OpenAI(
            api_key=os.getenv("CUSTOM_API_KEY"),
            base_url="https://api.shopaikey.com/v1",
            default_headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
        )
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
    from openai import OpenAI

    api_key = os.getenv("CUSTOM_API_KEY")
    if not api_key and ENV_PATH.exists():
        # Fallback: đọc trực tiếp từ .env khi biến môi trường chưa được inject vào process.
        api_key = dotenv_values(ENV_PATH).get("CUSTOM_API_KEY")

    if isinstance(api_key, str):
        api_key = api_key.strip().strip('"').strip("'")

    if not api_key:
        raise ValueError(
            "Thiếu CUSTOM_API_KEY trong .env để tạo embedding"
        )

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.shopaikey.com/v1",
        default_headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        },
    )
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding


def build_index(
    docs_dir: Path = DOCS_DIR,
    db_dir: Path = CHROMA_DB_DIR,
    chunk_dump_path: Optional[Path] = CHUNK_DUMP_PATH,
) -> None:
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
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0
    doc_files = list(docs_dir.glob("*.txt"))
    chunk_dump_lines: List[str] = []

    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return

    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc)
        print(f"    Tong chunks tao ra: {len(chunks)}")
        ids: List[str] = []
        documents: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict[str, Any]] = []

        for i, chunk in enumerate(chunks):
            chunk_text = chunk["text"].strip()
            if not chunk_text:
                continue

            chunk_id = f"{filepath.stem}_{i}"

            # In ro tung chunk de de kiem tra truoc khi embed.
            print("    " + "=" * 68)
            print(f"    Chunk {i + 1}/{len(chunks)}")
            print(f"    ID: {chunk_id}")
            print(f"    Section: {chunk['metadata'].get('section', '')}")
            print(f"    Metadata: {chunk['metadata']}")
            print("    Text:")
            print(chunk_text)
            print("    " + "=" * 68)

            chunk_record = {
                "source_file": filepath.name,
                "chunk_id": chunk_id,
                "section": chunk["metadata"].get("section", ""),
                "metadata": chunk["metadata"],
                "text": chunk_text,
            }
            chunk_dump_lines.append(json.dumps(chunk_record, ensure_ascii=False))

            embedding = get_embedding(chunk_text)

            ids.append(chunk_id)
            documents.append(chunk_text)
            embeddings.append(embedding)
            metadatas.append(chunk["metadata"])

        if ids:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

        print(f"    → {len(ids)} chunks indexed")
        total_chunks += len(ids)

    print(f"\nHoàn thành! Tổng số chunks: {total_chunks}")
    print(f"Vector DB lưu tại: {db_dir}")

    if chunk_dump_path is not None:
        chunk_dump_path.parent.mkdir(parents=True, exist_ok=True)
        chunk_dump_path.write_text("\n".join(chunk_dump_lines) + "\n", encoding="utf-8")
        print(f"Chunks JSONL đã lưu tại: {chunk_dump_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RAG index from policy docs")
    parser.add_argument(
        "--docs-dir",
        default=str(DOCS_DIR),
        help="Directory containing .txt docs to index",
    )
    parser.add_argument(
        "--db-dir",
        default=str(CHROMA_DB_DIR),
        help="Directory for persistent ChromaDB storage",
    )
    parser.add_argument(
        "--chunk-dump",
        default=str(CHUNK_DUMP_PATH),
        help="Output .jsonl file to save full chunk contents and metadata",
    )
    return parser.parse_args()


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
    args = parse_args()
    docs_dir = Path(args.docs_dir)
    db_dir = Path(args.db_dir)
    chunk_dump_path = Path(args.chunk_dump)

    print("=" * 60)
    print("Sprint 1: Build RAG Index")
    print("=" * 60)
    print(f"Docs dir: {docs_dir}")
    print(f"DB dir: {db_dir}")
    print(f"Chunk dump: {chunk_dump_path}")

    # Bước 1: Kiểm tra docs
    doc_files = list(docs_dir.glob("*.txt"))
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
    build_index(docs_dir=docs_dir, db_dir=db_dir, chunk_dump_path=chunk_dump_path)

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
