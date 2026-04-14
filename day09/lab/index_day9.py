import os
import re
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIG
# =============================================================================

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80


# =============================================================================
# PREPROCESS
# =============================================================================

def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    lines = raw_text.strip().split("\n")

    metadata = {
        "source": os.path.basename(filepath),
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }

    content_lines = []
    header_done = False

    for line in lines:
        line = line.strip()

        if not header_done:
            if line.startswith("Source:"):
                metadata["source"] = line.replace("Source:", "").strip()
            elif line.startswith("Department:"):
                metadata["department"] = line.replace("Department:", "").strip()
            elif line.startswith("Effective Date:"):
                metadata["effective_date"] = line.replace("Effective Date:", "").strip()
            elif line.startswith("Access:"):
                metadata["access"] = line.replace("Access:", "").strip()
            elif line.startswith("==="):
                header_done = True
                content_lines.append(line)
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return {
        "text": cleaned_text,
        "metadata": metadata,
    }


# =============================================================================
# CHUNKING
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = doc["text"]
    base_metadata = doc["metadata"]

    sections = re.split(r"(===.*?===)", text)

    chunks = []
    current_section = "General"
    current_text = ""

    for part in sections:
        if re.match(r"===.*?===", part):
            if current_text.strip():
                chunks.extend(
                    _split_by_size(
                        current_text.strip(),
                        base_metadata,
                        current_section
                    )
                )
            current_section = part.strip("= ").strip()
            current_text = ""
        else:
            current_text += part

    if current_text.strip():
        chunks.extend(
            _split_by_size(
                current_text.strip(),
                base_metadata,
                current_section
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

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_parts = []
    current_len = 0
    overlap_tail = ""

    for para in paragraphs:
        para_len = len(para)

        if current_len + para_len > chunk_chars and current_parts:
            chunk_text = overlap_tail + "\n\n".join(current_parts)

            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **base_metadata,
                    "section": section
                }
            })

            tail = "\n\n".join(current_parts)
            overlap_tail = tail[-overlap_chars:] + "\n\n"

            current_parts = []
            current_len = 0

        current_parts.append(para)
        current_len += para_len + 2

    if current_parts:
        chunk_text = overlap_tail + "\n\n".join(current_parts)

        chunks.append({
            "text": chunk_text,
            "metadata": {
                **base_metadata,
                "section": section
            }
        })

    return chunks


# =============================================================================
# EMBEDDING
# =============================================================================

_model = None

def get_embedding(text: str) -> List[float]:
    global _model

    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")

    return _model.encode(text).tolist()


# =============================================================================
# BUILD INDEX
# =============================================================================

def build_index():
    import chromadb

    print("Building Day 9 Chroma index...")

    CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    try:
        client.delete_collection("day09_docs")
    except:
        pass

    collection = client.get_or_create_collection(
        name="day09_docs",
        metadata={"hnsw:space": "cosine"}
    )

    doc_files = list(DOCS_DIR.glob("*.txt"))

    if not doc_files:
        print("No .txt files found in data/docs/")
        return

    total_chunks = 0

    for filepath in doc_files:
        print(f"Processing: {filepath.name}")

        raw_text = filepath.read_text(encoding="utf-8")

        doc = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc)

        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"

            ids.append(chunk_id)
            documents.append(chunk["text"])
            embeddings.append(get_embedding(chunk["text"]))
            metadatas.append(chunk["metadata"])

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

        total_chunks += len(chunks)

        print(f"   Indexed {len(chunks)} chunks")

    print(f"\nDONE: Indexed {total_chunks} total chunks into day09_docs")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    build_index()