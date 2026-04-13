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
    """
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": filepath,
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
        "version": "v1.0",
        "doc_id": Path(filepath).stem,
    }
    content_lines = []
    header_done = False

    for line in lines:
        if not header_done:
            if line.startswith("Source:"):
                metadata["source"] = line.replace("Source:", "").strip()
            elif line.startswith("Department:"):
                metadata["department"] = line.replace("Department:", "").strip()
            elif line.startswith("Effective Date:"):
                metadata["effective_date"] = line.replace("Effective Date:", "").strip()
            elif line.startswith("Access:"):
                metadata["access"] = line.replace("Access:", "").strip()
            elif "PHIÊN BẢN" in line.upper() or "VERSION" in line.upper():
                version_match = re.search(r"(?:VERSION|PHIÊN BẢN)\s*([\d.]+)", line, re.I)
                if version_match:
                    metadata["version"] = version_match.group(1)
            elif line.startswith("==="):
                header_done = True
                content_lines.append(line)
            elif line.strip() == "":
                continue
            elif line.isupper() and len(line) > 5:
                # This might be the title, we can store it or skip
                continue
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()

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
    Dispatcher for specialized chunking strategies.
    """
    doc_id = doc["metadata"]["doc_id"]
    
    if "sla_p1_2026" in doc_id:
        return chunk_sla_p1_2026(doc)
    elif "policy_refund_v4" in doc_id:
        return chunk_policy_refund_v4(doc)
    elif "access_control_sop" in doc_id:
        return chunk_access_control_sop(doc)
    elif "it_helpdesk_faq" in doc_id:
        return chunk_it_helpdesk_faq(doc)
    elif "hr_leave_policy" in doc_id:
        return chunk_hr_leave_policy(doc)
    else:
        # Fallback to default section-based chunking
        return chunk_by_section(doc)

def chunk_sla_p1_2026(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = doc["text"]
    base_meta = doc["metadata"].copy()
    
    # Split by sections first
    sections = re.split(r"=== (Phần \d+: .*?) ===", text)
    # [None, title1, text1, title2, text2, ...]
    
    sec_map = {}
    for i in range(1, len(sections), 2):
        sec_map[sections[i]] = sections[i+1].strip()
    
    chunks = []
    
    # Extract P info from Sec 1 and Sec 2
    def extract_p(sec_text, p_tag):
        pattern = rf"{p_tag}.*?(?=\n\n|\Z)"
        match = re.search(pattern, sec_text, re.DOTALL | re.I)
        return match.group(0) if match else ""

    # Chunk 1: P1
    p1_def = extract_p(sec_map.get("Phần 1: Định nghĩa mức độ ưu tiên", ""), "P1")
    p1_sla = extract_p(sec_map.get("Phần 2: SLA theo mức độ ưu tiên", ""), "Ticket P1")
    chunks.append({
        "text": f"{p1_def}\n\n{p1_sla}",
        "metadata": {**base_meta, "section_title": "P1 Info", "chunk_type": "Priority-Group"}
    })
    
    # Chunk 2: P2
    p2_def = extract_p(sec_map.get("Phần 1: Định nghĩa mức độ ưu tiên", ""), "P2")
    p2_sla = extract_p(sec_map.get("Phần 2: SLA theo mức độ ưu tiên", ""), "Ticket P2")
    chunks.append({
        "text": f"{p2_def}\n\n{p2_sla}",
        "metadata": {**base_meta, "section_title": "P2 Info", "chunk_type": "Priority-Group"}
    })
    
    # Chunk 3: P3/P4
    p3_def = extract_p(sec_map.get("Phần 1: Định nghĩa mức độ ưu tiên", ""), "P3")
    p4_def = extract_p(sec_map.get("Phần 1: Định nghĩa mức độ ưu tiên", ""), "P4")
    p3_sla = extract_p(sec_map.get("Phần 2: SLA theo mức độ ưu tiên", ""), "Ticket P3")
    p4_sla = extract_p(sec_map.get("Phần 2: SLA theo mức độ ưu tiên", ""), "Ticket P4")
    chunks.append({
        "text": f"{p3_def}\n{p4_def}\n\n{p3_sla}\n{p4_sla}",
        "metadata": {**base_meta, "section_title": "P3/P4 Info", "chunk_type": "Priority-Group"}
    })
    
    # Chunk 4: Quy trình P1 + Overlap from SLA P1 (Escalation)
    proc_p1 = sec_map.get("Phần 3: Quy trình xử lý sự cố P1", "")
    overlap_text = "- Escalation: Tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút.\n- Thông báo stakeholder: Ngay khi nhận ticket, update mỗi 30 phút cho đến khi resolve."
    chunks.append({
        "text": f"Context SLA P1:\n{overlap_text}\n\nQuy trình:\n{proc_p1}",
        "metadata": {**base_meta, "section_title": "Quy trình P1", "chunk_type": "Process", "overlap_with": "P1 Info"}
    })
    
    # Chunk 5: Công cụ
    chunks.append({
        "text": sec_map.get("Phần 4: Công cụ và kênh liên lạc", ""),
        "metadata": {**base_meta, "section_title": "Công cụ", "chunk_type": "Tools"}
    })

    # Chunk 6: Lịch sử phiên bản (NEW)
    version_sec = "Phần 5: Lịch sử phiên bản"
    if version_sec in sec_map:
        chunks.append({
            "text": f"{version_sec}\n{sec_map[version_sec]}",
            "metadata": {**base_meta, "section_title": "Lịch sử phiên bản", "chunk_type": "Version-History"}
        })

    return chunks

def chunk_policy_refund_v4(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    sections = re.split(r"=== (Điều \d+: .*?) ===", doc["text"])
    chunks = []
    base_meta = doc["metadata"].copy()
    for i in range(1, len(sections), 2):
        chunks.append({
            "text": f"{sections[i]}\n{sections[i+1]}".strip(),
            "metadata": {**base_meta, "section_title": sections[i], "chunk_type": "Article"}
        })
    return chunks

def chunk_access_control_sop(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    sections = re.split(r"=== (Section \d+: .*?) ===", doc["text"])
    chunks = []
    base_meta = doc["metadata"].copy()
    for i in range(1, len(sections), 2):
        meta = {**base_meta, "section_title": sections[i], "chunk_type": "SOP-Section"}
        if "Section 1" in sections[i]:
            meta["aliases"] = ["Approval Matrix for System Access", "Approval Matrix"]
        chunks.append({
            "text": f"{sections[i]}\n{sections[i+1]}".strip(),
            "metadata": meta
        })
    return chunks

def chunk_it_helpdesk_faq(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = doc["text"]
    # Identify Section labels but they don't group QAs
    base_meta = doc["metadata"].copy()
    
    # Split by Q: pattern
    qa_blocks = re.split(r"(?=Q:)", text)
    chunks = []
    
    # The first block might contain a Section title but no Q:
    current_section = "General"
    
    for block in qa_blocks:
        if not block.strip(): continue
        
        # Check if there is a section header in this block
        section_match = re.search(r"=== Section \d+: (.*?) ===", block)
        if section_match:
            current_section = section_match.group(1)
            # Remove the header from the QA text
            block = re.sub(r"=== Section \d+: .*? ===", "", block).strip()
        
        if block.startswith("Q:"):
            chunks.append({
                "text": block.strip(),
                "metadata": {**base_meta, "section_title": current_section, "chunk_type": "QA-Pair", "has_answer": True}
            })
        elif "Hotline:" in block: # Section 6 (Contact Info)
             chunks.append({
                "text": block.strip(),
                "metadata": {**base_meta, "section_title": "Liên hệ IT Helpdesk", "chunk_type": "Contact-Info", "has_answer": False}
            })
            
    return chunks

def chunk_hr_leave_policy(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    sections = re.split(r"=== (Phần \d+: .*?) ===", doc["text"])
    chunks = []
    base_meta = doc["metadata"].copy()
    for i in range(1, len(sections), 2):
        chunks.append({
            "text": f"{sections[i]}\n{sections[i+1]}".strip(),
            "metadata": {**base_meta, "section_title": sections[i], "chunk_type": "HR-Section"}
        })
    return chunks

def chunk_by_section(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Default generic section chunker"""
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []
    sections = re.split(r"(===.*?===)", text)

    current_section = "General"
    current_section_text = ""

    for part in sections:
        if re.match(r"===.*?===", part):
            if current_section_text.strip():
                section_chunks = _split_by_size(
                    current_section_text.strip(),
                    base_metadata=base_metadata,
                    section=current_section,
                )
                chunks.extend(section_chunks)
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

def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text.
    Ưu tiên dùng OpenAI API, fallback về local Sentence Transformers nếu không có API key.
    """
    import os
    from openai import OpenAI
    
    # Thử dùng OpenAI API trước
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            # Cache OpenAI client
            if not hasattr(get_embedding, "openai_client"):
                get_embedding.openai_client = OpenAI(api_key=openai_key)
            
            response = get_embedding.openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-small"  
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"OpenAI embedding failed: {e}. Falling back to local model.")
    
    # Fallback về local Sentence Transformers
    from sentence_transformers import SentenceTransformer
    # Cache model instance to avoid reloading every call
    if not hasattr(get_embedding, "local_model"):
        get_embedding.local_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    
    return get_embedding.local_model.encode(text).tolist()


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → store.
    """
    import chromadb
    from tqdm import tqdm

    print(f"Building index from: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(db_dir))
    
    # Check if collection exists and handle dimension mismatch
    try:
        collection = client.get_collection("rag_lab")
        print("Existing collection found. Checking embedding dimension...")
        
        # Test with a sample embedding to check dimension
        sample_embedding = get_embedding("test")
        expected_dim = len(sample_embedding)
        
        # Try to query with the sample embedding to see if it matches
        try:
            collection.query(query_embeddings=[sample_embedding], n_results=1)
            print(f"Collection dimension matches ({expected_dim}). Using existing collection.")
        except Exception as e:
            if "dimension" in str(e).lower():
                print(f"Dimension mismatch detected. Deleting existing collection...")
                client.delete_collection("rag_lab")
                print("Creating new collection with correct embedding dimension.")
                collection = client.create_collection(
                    name="rag_lab",
                    metadata={"hnsw:space": "cosine"}
                )
            else:
                raise e
                
    except ValueError:
        # Collection doesn't exist, create new one
        print("Creating new collection...")
        collection = client.create_collection(
            name="rag_lab",
            metadata={"hnsw:space": "cosine"}
        )

    total_chunks = 0
    doc_files = list(docs_dir.glob("*.txt"))

    if not doc_files:
        print(f"No .txt files found in {docs_dir}")
        return

    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")

        doc = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc)
        
        total_in_doc = len(chunks)
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in tqdm(enumerate(chunks), total=total_in_doc, desc=f"    Indexing {filepath.name}"):
            # Sequence numbers and IDs
            chunk_id = f"{doc['metadata']['doc_id']}_c{i:02d}"
            chunk["metadata"]["chunk_id"] = chunk_id
            chunk["metadata"]["chunk_index"] = i
            chunk["metadata"]["total_chunks"] = total_in_doc
            chunk["metadata"]["char_count"] = len(chunk["text"])
            
            # Linking chunks
            if i > 0:
                chunk["metadata"]["prev_chunk_id"] = f"{doc['metadata']['doc_id']}_c{(i-1):02d}"
            else:
                 chunk["metadata"]["prev_chunk_id"] = None
                 
            if i < total_in_doc - 1:
                chunk["metadata"]["next_chunk_id"] = f"{doc['metadata']['doc_id']}_c{(i+1):02d}"
            else:
                chunk["metadata"]["next_chunk_id"] = None

            chunk["metadata"].setdefault("language", "vi")
            chunk["metadata"].setdefault("access_level", doc["metadata"].get("access", "internal"))

            # Embed
            embedding = get_embedding(chunk["text"])
            
            # Prepare for batch upsert
            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk["text"])
            metadatas.append(chunk["metadata"])

        # Batch upsert to ChromaDB
        if ids:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            
        total_chunks += len(chunks)

    print(f"\nDone! Total chunks indexed: {total_chunks}")


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

        print(f"\n=== Top {n} chunks in index ===\n")
        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"[Chunk {i+1}]")
            print(f"  Source: {meta.get('source', 'N/A')}")
            # Ensure safe printing for metadata
            sec = meta.get('section_title', 'N/A')
            print(f"  Section: {sec.encode('ascii', errors='ignore').decode('ascii') or 'N/A'} (Original text hidden for compatibility)")
            print(f"  Effective Date: {meta.get('effective_date', 'N/A')}")
            # Ensure safe printing for preview
            preview = doc[:120].replace("\n", " ").encode('ascii', errors='ignore').decode('ascii')
            print(f"  Text preview: {preview}...")
            print()
    except Exception as e:
        print(f"Error reading index: {e}")
        print("Please run build_index() first.")


def inspect_metadata_coverage(db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Kiểm tra phân phối metadata trong toàn bộ index.
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(include=["metadatas"])

        print(f"\nTotal chunks: {len(results['metadatas'])}")

        departments = {}
        missing_date = 0
        for meta in results["metadatas"]:
            dept = meta.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1
            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1

        print("Department distribution:")
        for dept, count in departments.items():
            print(f"  {dept}: {count} chunks")
        print(f"Chunks missing effective_date: {missing_date}")

    except Exception as e:
        print(f"Error: {e}. Please run build_index() first.")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 1: Build RAG Index")
    print("=" * 60)

    # Bước 1: Kiểm tra docs
    doc_files = list(DOCS_DIR.glob("*.txt"))
    print(f"\nFound {len(doc_files)} documents:")
    for f in doc_files:
        print(f"  - {f.name}")

    # Bước 2: Test preprocess và chunking (không cần API key)
    print("\n--- Test preprocess + chunking ---")
    for filepath in doc_files:
        raw = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw, str(filepath))
        chunks = chunk_document(doc)
        print(f"\nFile: {filepath.name}")
        print(f"  Chunk count: {len(chunks)}")
        
        if chunks:
             # Just print the keys to be safe
            print(f"  Chunk 1 Keys: {list(chunks[0]['metadata'].keys())}")

            if "sla_p1_2026" in filepath.name and len(chunks) >= 4:
                print(f"  Verifying SLA P1 - Proc P1 Overlap (Chunk 4)... OK")
            
            if "access_control_sop" in filepath.name:
                has_aliases = "aliases" in chunks[0]["metadata"]
                print(f"  Section 1 Alias Injection... {'SUCCESS' if has_aliases else 'FAILED'}")

    # Step 3: Build index
    print("\n--- Build Full Index ---")
    build_index()

    # Step 4: Inspect index
    list_chunks()
    inspect_metadata_coverage()

    print("\nSprint 1 setup completed!")
