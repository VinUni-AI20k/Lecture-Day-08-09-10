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

# Gợi ý từ slide: chunk 300-500 tokens, overlap 50-80 tokens
# Ở đây ta dùng character count ước lượng: 1 token ~ 4 ký tự.
CHUNK_SIZE_CHARS = 1600       # ~400 tokens
CHUNK_OVERLAP_CHARS = 320    # ~80 tokens


# =============================================================================
# STEP 1: PREPROCESS
# Làm sạch text trước khi chunk và embed
# =============================================================================

def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    """
    Preprocess một tài liệu: extract metadata từ header và làm sạch nội dung.
    """
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": Path(filepath).name,
        "section": "General",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }
    
    content_lines = []
    header_done = False

    for line in lines:
        clean_line = line.strip()
        if not header_done:
            # Parse metadata từ các dòng "Key: Value" ở đầu file
            if ":" in clean_line:
                key, val = [part.strip() for part in clean_line.split(":", 1)]
                key_lower = key.lower()
                if "source" in key_lower:
                    metadata["source"] = val
                elif "department" in key_lower:
                    metadata["department"] = val
                elif "effective date" in key_lower:
                    metadata["effective_date"] = val
                elif "access" in key_lower:
                    metadata["access"] = val
                
                # Nếu không phải metadata key chuẩn, có thể là bắt đầu nội dung hoặc title
                elif clean_line.startswith("==="):
                    header_done = True
                    content_lines.append(line)
                else:
                    # Coi như là dòng mô tả hoặc title
                    continue
            elif clean_line.startswith("==="):
                header_done = True
                content_lines.append(line)
            elif not clean_line or clean_line.isupper():
                # Dòng trống hoặc Tiêu đề tài liệu (toàn chữ hoa) ở đầu
                continue
            else:
                # Nếu gặp text bình thường mà chưa thấy ===, kết thúc header
                header_done = True
                content_lines.append(line)
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)
    # Normalize khoảng trắng
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

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
    Chunk một tài liệu đã preprocess theo cấu trúc: Section -> (Structural Items / Paragraphs)
    """
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []

    # BƯỚC 1: Split theo Section Heading: "=== Section ... ===" hoặc "=== Phần ... ===" hoặc "=== Điều ... ==="
    section_pattern = r"(===\s*(?:Section|Phần|Điều)\s*.*?\s*===)"
    parts = re.split(section_pattern, text)

    current_section = "General"
    
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue
            
        if re.match(section_pattern, part):
            current_section = part.strip("= ").strip()
            i += 1
            if i < len(parts):
                section_content = parts[i].strip()
                if section_content:
                    section_chunks = _split_structurally(
                        section_content,
                        base_metadata=base_metadata,
                        section=current_section
                    )
                    chunks.extend(section_chunks)
                i += 1
        else:
            # Nội dung trước section đầu tiên (nếu có)
            section_chunks = _split_structurally(
                part,
                base_metadata=base_metadata,
                section=current_section
            )
            chunks.extend(section_chunks)
            i += 1

    return chunks


def _split_structurally(
    text: str,
    base_metadata: Dict,
    section: str
) -> List[Dict[str, Any]]:
    """
    Chiến lược "Structural Chunking":
    Ưu tiên giữ nguyên các block có cấu trúc như FAQ (Q/A), List items (Step, Level, Ticket), 
    hoặc Paragraphs. Chỉ ghép chúng lại cho đến khi đạt CHUNK_SIZE_CHARS.
    """
    # Split theo paragraph trước
    raw_blocks = text.split("\n\n")
    atomic_blocks = []
    
    current_atomic = ""
    for rb in raw_blocks:
        rb = rb.strip()
        if not rb: continue
        
        # Nếu block bắt đầu bằng "Q:" hoặc các pattern đặc biệt
        if rb.startswith("Q:") or re.match(r"^(Level\s+\d+|Ticket\s+P\d+|Bước\s+\d+|Điều\s+\d+|\d+\.\d+)", rb):
            if current_atomic: atomic_blocks.append(current_atomic.strip())
            current_atomic = rb
        else:
            if current_atomic:
                current_atomic += "\n\n" + rb
            else:
                current_atomic = rb
    
    if current_atomic: atomic_blocks.append(current_atomic.strip())

    # Ghép các atomic blocks vào chunks
    chunks = []
    current_chunk_text = ""
    
    for block in atomic_blocks:
        if not current_chunk_text:
            current_chunk_text = block
        elif len(current_chunk_text) + len(block) < CHUNK_SIZE_CHARS:
            current_chunk_text += "\n\n" + block
        else:
            chunks.append({
                "text": current_chunk_text,
                "metadata": {**base_metadata, "section": section}
            })
            current_chunk_text = block

    if current_chunk_text:
        chunks.append({
            "text": current_chunk_text,
            "metadata": {**base_metadata, "section": section}
        })

    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector bằng OpenAI.
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
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → store.
    """
    import chromadb

    print(f"Đang build index từ: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(db_dir))
    
    # Xóa collection cũ để build lại từ đầu trong Lab
    try:
        client.delete_collection("rag_lab")
        print("  Đã xóa index cũ.")
    except:
        pass

    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"}
    )

    doc_files = list(docs_dir.glob("*.txt"))
    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return

    total_chunks = 0
    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")

        doc_data = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc_data)

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"
            try:
                embedding = get_embedding(chunk["text"])
                ids.append(chunk_id)
                embeddings.append(embedding)
                documents.append(chunk["text"])
                metadatas.append(chunk["metadata"])
            except Exception as e:
                print(f"    Error embedding chunk {i}: {e}")

        if ids:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            total_chunks += len(chunks)
            print(f"    → {len(chunks)} chunks indexed.")

    print(f"\nHoàn thành! Tổng số chunks: {total_chunks}")


# =============================================================================
# STEP 4: INSPECT / KIỂM TRA
# Dùng để debug và kiểm tra chất lượng index
# =============================================================================

def list_chunks(db_dir: Path = CHROMA_DB_DIR, n: int = 5) -> None:
    """
    In ra n chunk đầu tiên trong ChromaDB để kiểm tra chất lượng index.
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(limit=n, include=["documents", "metadatas"])

        if not results["ids"]:
            print("\nIndex trống.")
            return

        print(f"\n=== Top {n} chunks trong index ===\n")
        for i in range(len(results["ids"])):
            doc = results["documents"][i]
            meta = results["metadatas"][i]
            print(f"[Chunk {i+1}]")
            print(f"  Source: {meta.get('source', 'N/A')}")
            print(f"  Section: {meta.get('section', 'N/A')}")
            print(f"  Effective Date: {meta.get('effective_date', 'N/A')}")
            print(f"  Text preview: {doc[:150].replace('\n', ' ')}...")
            print()
    except Exception as e:
        print(f"Lỗi khi đọc index: {e}")


def inspect_metadata_coverage(db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Kiểm tra phân phối metadata trong toàn bộ index.
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(include=["metadatas"])

        print(f"\nTổng chunks: {len(results['metadatas'])}")

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
        print(f"Lỗi: {e}")


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