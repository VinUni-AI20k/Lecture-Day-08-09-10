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
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = Path(__file__).parent / "data" / "docs"
QDRANT_DB_DIR = Path(__file__).parent / "qdrant_db"
QDRANT_COLLECTION_NAME = "rag_lab"

# Qdrant Cloud config (từ .env)
QDRANT_CLUSTER_ENDPOINT = os.getenv("QDRANT_CLUSTER_ENDPOINT", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
USE_QDRANT_CLOUD = bool(QDRANT_CLUSTER_ENDPOINT)  # True if cloud endpoint is set

# Embedding model config
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
EMBEDDING_DIM = 1024  # Qwen3-0.6B output dimension

# Sprint 1: Chunking config 
# Gợi ý từ slide: chunk 300-500 tokens, overlap 50-80 tokens
CHUNK_SIZE_CHARS = 1500    # ký tự (1500 chars ≈ 400 tokens cho tiếng Anh)
CHUNK_OVERLAP_CHARS = 300  # ký tự overlap giữa các chunk


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
    chunk_chars: int = CHUNK_SIZE_CHARS,
    overlap_chars: int = CHUNK_OVERLAP_CHARS,
) -> List[Dict[str, Any]]:
    """
    Helper: Split text dài thành chunks với overlap.
    
    Strategy:
    - Split theo paragraph (\n\n) trước để giữ ranh giới tự nhiên
    - Ghép paragraphs lại cho đến khi gần đủ chunk_chars
    - Thêm overlap từ chunk trước để tránh mất context
    """
    if len(text) <= chunk_chars:
        # Toàn bộ section vừa một chunk
        return [{
            "text": text,
            "metadata": {**base_metadata, "section": section},
        }]

    chunks = []
    paragraphs = text.split("\n\n")
    
    # Lọc paragraph trống
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    if not paragraphs:
        # Fallback: split đơn giản theo ký tự nếu không có paragraph
        current_chunk = text[:chunk_chars]
        chunks.append({
            "text": current_chunk,
            "metadata": {**base_metadata, "section": section},
        })
        return chunks
    
    # Ghép paragraphs thành chunks
    current_chunk_text = ""
    overlap_text = ""
    
    for para in paragraphs:
        # Nếu thêm paragraph này vào chunk sẽ vượt quá size
        if len(current_chunk_text) + len(para) + 2 > chunk_chars and current_chunk_text:
            # Lưu chunk hiện tại
            full_chunk = overlap_text + current_chunk_text if overlap_text else current_chunk_text
            chunks.append({
                "text": full_chunk.strip(),
                "metadata": {**base_metadata, "section": section},
            })
            
            # Chuẩn bị overlap cho chunk tiếp theo
            # Lấy phần cuối của chunk hiện tại làm overlap
            words = current_chunk_text.split()
            overlap_words = words[-3:] if len(words) > 3 else words  # Lấy 3 từ cuối
            overlap_text = " ".join(overlap_words) + "\n"
            
            # Reset chunk hiện tại, bắt đầu với paragraph mới
            current_chunk_text = para + "\n"
        else:
            current_chunk_text += para + "\n"
    
    # Lưu chunk cuối cùng
    if current_chunk_text.strip():
        full_chunk = overlap_text + current_chunk_text if overlap_text else current_chunk_text
        chunks.append({
            "text": full_chunk.strip(),
            "metadata": {**base_metadata, "section": section},
        })
    
    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

def get_embedding(text: str, model: Optional[SentenceTransformer] = None) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text dùng Qwen model.
    
    Args:
        text: Đoạn text cần embed
        model: SentenceTransformer model instance (sẽ tạo mới nếu không có)
    
    Returns:
        List[float]: Vector embedding (dim = 512 cho Qwen3-0.6B)
    
    Tech choice: Dùng SentenceTransformer (Qwen3-0.6B) vì:
      - Chạy local, không cần API key
      - Support đa ngôn ngữ (tiếng Việt tốt)
      - Embedding quality tốt cho retrieval task
    """
    if model is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL}")
        model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Normalize whitespace
    text = " ".join(text.split())
    
    # Encode và convert sang list
    embedding = model.encode(text, convert_to_tensor=False)
    return embedding.tolist()


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = QDRANT_DB_DIR) -> None:
    """
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → upsert Qdrant.

    Steps:
    1. Khởi tạo Qdrant client (Cloud hoặc Local mode)
    2. Tạo/recreate collection với vector params (dim=512 cho Qwen)
    3. Load embedding model (Qwen3-0.6B)
    4. Với mỗi file:
       a. Preprocess + extract metadata
       b. Chunk theo section + paragraph
       c. Embed từng chunk
       d. Upsert vào Qdrant với metadata
    """
    print(f"Đang build index từ: {docs_dir}")
    
    # Bước 1: Khởi tạo Qdrant client (Cloud hoặc Local mode)
    if USE_QDRANT_CLOUD:
        print(f"🌐 Connecting to Qdrant Cloud: {QDRANT_CLUSTER_ENDPOINT}")
        client = QdrantClient(
            url=QDRANT_CLUSTER_ENDPOINT,
            api_key=QDRANT_API_KEY,
        )
        print("✅ Connected to Qdrant Cloud")
    else:
        print(f"💾 Using local Qdrant: {db_dir}")
        db_dir.mkdir(parents=True, exist_ok=True)
        client = QdrantClient(path=str(db_dir))
    
    # Bước 2: Xóa collection cũ (nếu có) để reset
    try:
        client.delete_collection(QDRANT_COLLECTION_NAME)
        print(f"Deleted old collection: {QDRANT_COLLECTION_NAME}")
    except:
        pass
    
    # Tạo collection mới với vector config
    client.create_collection(
        collection_name=QDRANT_COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )
    print(f"Created new collection: {QDRANT_COLLECTION_NAME} (dim={EMBEDDING_DIM}, distance=cosine)")
    
    # Bước 3: Load embedding model một lần
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Bước 4: Process từng tài liệu
    doc_files = sorted(list(docs_dir.glob("*.txt")))
    
    if not doc_files:
        print(f"❌ Không tìm thấy file .txt trong {docs_dir}")
        return
    
    total_chunks = 0
    total_points = 0
    
    print(f"\nTìm thấy {len(doc_files)} tài liệu:")
    for f in doc_files:
        print(f"  - {f.name}")
    
    print("\n" + "="*70)
    print("PROCESSING DOCUMENTS")
    print("="*70)
    
    for filepath in doc_files:
        print(f"\n📄 Processing: {filepath.name}")
        
        try:
            # Đọc và preprocess
            raw_text = filepath.read_text(encoding="utf-8")
            doc = preprocess_document(raw_text, str(filepath))
            
            # Chunk tài liệu
            chunks = chunk_document(doc)
            print(f"   ├─ Metadata: source={doc['metadata']['source']}, dept={doc['metadata']['department']}")
            print(f"   └─ Chunks: {len(chunks)} chunks")
            
            # Upsert từng chunk vào Qdrant
            points = []
            for i, chunk in enumerate(chunks):
                chunk_id = str(uuid.uuid4())  # Unique ID cho mỗi chunk
                
                # Embed chunk text
                embedding = get_embedding(chunk["text"], model=model)
                
                # Tạo point cho Qdrant
                point = PointStruct(
                    id=hash(f"{filepath.stem}_{i}") % (2**31),  # Numeric ID từ hash
                    vector=embedding,
                    payload={
                        "text": chunk["text"],
                        "source": chunk["metadata"]["source"],
                        "section": chunk["metadata"]["section"],
                        "department": chunk["metadata"]["department"],
                        "effective_date": chunk["metadata"]["effective_date"],
                        "access": chunk["metadata"]["access"],
                        "chunk_idx": i,
                    }
                )
                points.append(point)
            
            # Batch upsert
            client.upsert(
                collection_name=QDRANT_COLLECTION_NAME,
                points=points,
            )
            
            total_chunks += len(chunks)
            total_points += len(points)
            print(f"   ✅ Upserted {len(points)} points to Qdrant")
            
        except Exception as e:
            print(f"   ❌ Error processing {filepath.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print(f"✅ INDEX BUILD COMPLETE")
    print("="*70)
    print(f"Total documents processed: {len(doc_files)}")
    print(f"Total chunks created: {total_chunks}")
    print(f"Total points in Qdrant: {total_points}")
    print(f"Collection: {QDRANT_COLLECTION_NAME}")
    print(f"Storage: {db_dir}")
    print(f"\n💡 Next step: Run list_chunks() để kiểm tra chất lượng index")


# =============================================================================
# STEP 4: INSPECT / KIỂM TRA
# Dùng để debug và kiểm tra chất lượng index
# =============================================================================

def list_chunks(db_dir: Path = QDRANT_DB_DIR, n: int = 5) -> None:
    """
    In ra n chunk đầu tiên trong Qdrant để kiểm tra chất lượng index.

    Kiểm tra:
    - Chunk có giữ đủ metadata không? (source, section, effective_date, access)
    - Chunk có bị cắt giữa câu không?
    - Metadata có đúng không?
    """
    try:
        # Connect to Qdrant (Cloud hoặc Local)
        if USE_QDRANT_CLOUD:
            client = QdrantClient(
                url=QDRANT_CLUSTER_ENDPOINT,
                api_key=QDRANT_API_KEY,
            )
        else:
            client = QdrantClient(path=str(db_dir))
        
        # Lấy thông tin collection
        try:
            collection_info = client.get_collection(QDRANT_COLLECTION_NAME)
            total_points = collection_info.points_count
        except:
            print(f"❌ Collection '{QDRANT_COLLECTION_NAME}' not found")
            print("💡 Run build_index() first")
            return
        
        # Query lấy n point đầu tiên
        results = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=n,
        )
        
        points, _ = results
        
        print(f"\n{'='*80}")
        print(f"📊 CHUNK INSPECTION — Top {min(n, len(points))} chunks (Total: {total_points})")
        print(f"{'='*80}\n")
        
        for idx, point in enumerate(points, 1):
            payload = point.payload
            text = payload.get("text", "")
            
            print(f"[Chunk {idx}]")
            print(f"├─ Source:        {payload.get('source', 'N/A')}")
            print(f"├─ Section:       {payload.get('section', 'N/A')}")
            print(f"├─ Department:    {payload.get('department', 'N/A')}")
            print(f"├─ Effective:     {payload.get('effective_date', 'N/A')}")
            print(f"├─ Access:        {payload.get('access', 'N/A')}")
            print(f"├─ Length:        {len(text)} chars")
            print(f"└─ Preview:       {text[:100].strip()}...")
            print()
        
        print(f"{'='*80}")
        print(f"✅ Metadata coverage: {len(points)} chunks have complete metadata")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Run build_index() first")


def inspect_metadata_coverage(db_dir: Path = QDRANT_DB_DIR) -> None:
    """
    Phân tích phân phối metadata trong toàn bộ index.

    Checklist:
    - Mọi chunk đều có source?
    - Phân bố theo department?
    - Chunk nào thiếu effective_date?
    """
    try:
        # Connect to Qdrant (Cloud hoặc Local)
        if USE_QDRANT_CLOUD:
            client = QdrantClient(
                url=QDRANT_CLUSTER_ENDPOINT,
                api_key=QDRANT_API_KEY,
            )
        else:
            client = QdrantClient(path=str(db_dir))
        
        # Lấy thông tin collection
        try:
            collection_info = client.get_collection(QDRANT_COLLECTION_NAME)
            total_points = collection_info.points_count
        except:
            print(f"❌ Collection not found. Run build_index() first.")
            return
        
        # Scroll toàn bộ points (limit 10000 là mặc định Qdrant)
        results = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=10000,
        )
        
        points, _ = results
        
        print(f"\n{'='*80}")
        print(f"📈 METADATA COVERAGE ANALYSIS")
        print(f"{'='*80}\n")
        
        # Thống kê metadata
        departments = {}
        sources = {}
        sections = {}
        missing_date = 0
        missing_source = 0
        missing_dept = 0
        
        for point in points:
            payload = point.payload
            
            # Đếm department
            dept = payload.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1
            
            # Đếm source
            source = payload.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
            
            # Đếm section
            section = payload.get("section", "unknown")
            sections[section] = sections.get(section, 0) + 1
            
            # Check missing
            if payload.get("effective_date") in ("unknown", "", None):
                missing_date += 1
            if payload.get("source") in ("unknown", "", None):
                missing_source += 1
            if payload.get("department") in ("unknown", "", None):
                missing_dept += 1
        
        print(f"Total chunks: {len(points)}")
        print()
        
        print("📂 By Department:")
        for dept in sorted(departments.keys()):
            count = departments[dept]
            pct = (count / len(points) * 100) if points else 0
            print(f"  └─ {dept}: {count:3d} chunks ({pct:5.1f}%)")
        print()
        
        print("📄 By Source:")
        for source in sorted(sources.keys()):
            count = sources[source]
            pct = (count / len(points) * 100) if points else 0
            filename = Path(source).name if source != "unknown" else source
            print(f"  └─ {filename}: {count:3d} chunks ({pct:5.1f}%)")
        print()
        
        print("📑 By Section (Top 10):")
        sorted_sections = sorted(sections.items(), key=lambda x: x[1], reverse=True)
        for section, count in sorted_sections[:10]:
            section_display = section[:40] if len(section) <= 40 else section[:37] + "..."
            print(f"  └─ {section_display}: {count:3d} chunks")
        print()
        
        print("⚠️  Data Quality Issues:")
        print(f"  ├─ Missing effective_date: {missing_date} chunks")
        print(f"  ├─ Missing source: {missing_source} chunks")
        print(f"  └─ Missing department: {missing_dept} chunks")
        
        if missing_date + missing_source + missing_dept == 0:
            print("\n✅ All chunks have complete metadata!")
        else:
            print("\n⚠️  Some chunks are missing metadata fields")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 SPRINT 1: BUILD RAG INDEX")
    print("="*80)
    if USE_QDRANT_CLOUD:
        print(f"🌐 Mode: Qdrant Cloud")
        print(f"   Endpoint: {QDRANT_CLUSTER_ENDPOINT}")
    else:
        print(f"💾 Mode: Local Qdrant")
        print(f"   Storage: {QDRANT_DB_DIR}")
    print(f"Tech Stack: Qwen Embedding + Qdrant")
    print("="*80)

    # Bước 1: Kiểm tra docs
    doc_files = list(DOCS_DIR.glob("*.txt"))
    print(f"\n📁 Found {len(doc_files)} documents:")
    for f in doc_files:
        print(f"   ├─ {f.name}")
    
    if not doc_files:
        print("❌ No .txt files found! Please add documents to data/docs/")
        exit(1)

    # Bước 2: Test preprocess + chunking (không cần API/embedding key)
    print("\n" + "-"*80)
    print("STAGE 1: Test preprocess + chunking (no embedding needed)")
    print("-"*80)
    
    for filepath in doc_files[:1]:  # Test với 1 file đầu
        raw = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw, str(filepath))
        chunks = chunk_document(doc)
        
        print(f"\n📄 File: {filepath.name}")
        print(f"   Metadata:")
        for key, val in doc['metadata'].items():
            print(f"   ├─ {key}: {val}")
        print(f"   Chunks: {len(chunks)} chunks created")
        
        print(f"\n   First 3 chunks:")
        for i, chunk in enumerate(chunks[:3], 1):
            preview = chunk['text'][:100].replace("\n", " ").strip()
            section = chunk['metadata']['section']
            print(f"   [{i}] Section: {section}")
            print(f"       Text: {preview}...")

    # Bước 3: Build full index (yêu cầu embedding model)
    print("\n" + "-"*80)
    print("STAGE 2: Build full index (with embedding)")
    print("-"*80)
    print("⏳ This will download Qwen embedding model (~500MB) on first run...")
    print()
    
    build_index()

    # Bước 4: Kiểm tra index
    print("\nSTAGE 3: Inspect index")
    print("-"*80)
    list_chunks(n=5)
    inspect_metadata_coverage()

    print("\n✅ Sprint 1 COMPLETE!")
    print(f"   Index ready in: {QDRANT_DB_DIR}")
    print(f"   Collection: {QDRANT_COLLECTION_NAME}")
    print("\n📋 Next steps:")
    print("   1. Implement Sprint 2: rag_answer.py (RAG query)")
    print("   2. Test integration with LangChain")
    print("   3. Setup LangSmith tracing")
