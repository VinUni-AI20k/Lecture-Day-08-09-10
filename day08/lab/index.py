from openai import OpenAI
import os
import re
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

# OPTIMIZED: Larger chunks capture more complete context for complex questions
# Better chunk overlap preserves context boundaries for multi-detail extraction
CHUNK_SIZE = 600  # Increased from 400 to get fuller sections in single chunk
CHUNK_OVERLAP = 150  # Increased from 80 to reduce context loss at boundaries


# =============================================================================
# PREPROCESS
# =============================================================================

def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    metadata = {
        "source": filepath,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }

    patterns = {
        "source": r"Source:\s*(.*)",
        "department": r"Department:\s*(.*)",
        "effective_date": r"Effective Date:\s*(.*)",
        "access": r"Access:\s*(.*)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            metadata[key] = match.group(1).strip()

    # remove metadata khỏi content
    text = re.sub(
        r"(Source:.*|Department:.*|Effective Date:.*|Access:.*)",
        "",
        raw_text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return {"text": text, "metadata": metadata}


# =============================================================================
# CHUNK
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []

    sections = re.split(r"(===.*?===)", text)

    current_section = base_metadata.get("source", "General")
    current_text = ""

    for part in sections:
        if re.match(r"===.*?===", part):
            if current_text.strip():
                chunks.extend(
                    _split_by_size(current_text.strip(),
                                   base_metadata, current_section)
                )

            current_section = part.strip("= ").strip()
            current_text = ""
        else:
            current_text += part

    if current_text.strip():
        chunks.extend(
            _split_by_size(current_text.strip(),
                           base_metadata, current_section)
        )

    return chunks


def _split_by_size(
    text: str,
    base_metadata: Dict,
    section: str,
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:

    # 🔥 Ưu tiên split FAQ theo câu hỏi
    if "?" in text:
        paragraphs = re.split(r"\n(?=\w.*\?)", text)
    else:
        paragraphs = text.split("\n\n")

    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_chars:
            if current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "metadata": {**base_metadata, "section": section},
                })

                overlap = current_chunk[-overlap_chars:]
                current_chunk = overlap + "\n\n" + para
            else:
                current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append({
            "text": current_chunk.strip(),
            "metadata": {**base_metadata, "section": section},
        })

    return chunks


# =============================================================================
# EMBEDDING (OpenAI)
# =============================================================================


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embedding(text: str) -> List[float]:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


# =============================================================================
# BUILD INDEX
# =============================================================================

def build_index():
    import chromadb

    print("=== BUILD INDEX ===")

    db_dir = CHROMA_DB_DIR
    db_dir.mkdir(parents=True, exist_ok=True)

    client_db = chromadb.PersistentClient(path=str(db_dir))
    collection = client_db.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0

    for filepath in DOCS_DIR.glob("*.txt"):
        print(f"Processing: {filepath.name}")

        raw_text = filepath.read_text(encoding="utf-8")

        doc = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"

            embedding = get_embedding(chunk["text"])

            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk["text"]],
                metadatas=[chunk["metadata"]],
            )

        print(f" → {len(chunks)} chunks")
        total_chunks += len(chunks)

    print(f"\nDONE. Total chunks: {total_chunks}")


# =============================================================================
# INSPECT
# =============================================================================

def list_chunks(n=5):
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    results = collection.get(limit=n, include=["documents", "metadatas"])

    print("\n=== SAMPLE CHUNKS ===\n")

    for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
        print(f"[Chunk {i+1}]")
        print(f"Source: {meta.get('source')}")
        print(f"Section: {meta.get('section')}")
        print(f"Effective Date: {meta.get('effective_date')}")
        print(f"Text: {doc[:150]}...\n")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    build_index()
    list_chunks()
