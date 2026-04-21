"""
scripts/build_index.py — Build ChromaDB index for Day 09
=========================================================
Ported from Day 08's index.py (section-based chunking + metadata extraction).
Changes vs Day 08:
  - Embeddings: OpenAI text-embedding-3-small (or sentence-transformers fallback)
  - Collection name: day09_docs (not rag_lab)
  - No Vertex AI dependency

Run:
    uv run python scripts/build_index.py
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any

import chromadb
import vertexai
from vertexai.language_models import TextEmbeddingModel
from dotenv import load_dotenv

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────

DOCS_DIR = Path(__file__).parent.parent / "data" / "docs"
CHROMA_DB_DIR = Path(os.getenv("CHROMA_DB_PATH", "./chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "day09_docs")

VERTEX_PROJECT = os.getenv("VERTEX_PROJECT", "vinai053")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_EMBEDDING_MODEL = os.getenv("VERTEX_EMBEDDING_MODEL", "text-multilingual-embedding-002")

CHUNK_SIZE = 400  # tokens (≈ chars / 4)
CHUNK_OVERLAP = 80  # tokens overlap


# ─── Step 1: Preprocess ───────────────────────────────────────────────────────

def preprocess_document(raw_text: str, filename: str) -> Dict[str, Any]:
    """
    Extract header metadata and clean body text.
    Header lines: Source, Department, Effective Date, Access (before first === heading).
    """
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": filename,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
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
            elif line.startswith("==="):
                header_done = True
                content_lines.append(line)
            elif line.strip() == "" or line.isupper():
                continue
        else:
            content_lines.append(line)

    cleaned = "\n".join(content_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return {"text": cleaned, "metadata": metadata}


# ─── Step 2: Chunk ────────────────────────────────────────────────────────────

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Split on === Section === headings first; overflow sections split by paragraph.
    """
    text = doc["text"]
    base_meta = doc["metadata"].copy()
    chunks = []

    sections = re.split(r"(===.*?===)", text)
    current_section = "General"
    current_text = ""

    for part in sections:
        if re.match(r"===.*?===", part):
            if current_text.strip():
                chunks.extend(_split_by_size(current_text.strip(), base_meta, current_section))
            current_section = part.strip("= ").strip()
            current_text = ""
        else:
            current_text += part

    if current_text.strip():
        chunks.extend(_split_by_size(current_text.strip(), base_meta, current_section))

    return chunks


def _split_by_size(
        text: str,
        base_meta: Dict,
        section: str,
        chunk_chars: int = CHUNK_SIZE * 4,
        overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:
    if len(text) <= chunk_chars:
        return [{"text": text, "metadata": {**base_meta, "section": section}}]

    # Split on paragraph boundaries
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > chunk_chars and current:
            chunks.append({"text": current.strip(), "metadata": {**base_meta, "section": section}})
            # Overlap: keep last paragraph as context for next chunk
            overlap_text = current.split("\n\n")[-1] if "\n\n" in current else current[-overlap_chars:]
            current = overlap_text + "\n\n" + para
        else:
            current = (current + "\n\n" + para).strip() if current else para

    if current.strip():
        chunks.append({"text": current.strip(), "metadata": {**base_meta, "section": section}})

    return chunks


# ─── Step 3: Embed ────────────────────────────────────────────────────────────

def _get_embed_fn():
    """
    Returns an embed function using Vertex AI text-multilingual-embedding-002.
    Falls back to OpenAI if GOOGLE_APPLICATION_CREDENTIALS is not set.
    """
    creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds_file:
        # Resolve relative path from the lab root (parent of scripts/)
        creds_path = Path(__file__).parent.parent / creds_file
        if creds_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)

    try:
        vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
        model = TextEmbeddingModel.from_pretrained(VERTEX_EMBEDDING_MODEL)

        def embed_vertex(text: str) -> List[float]:
            return model.get_embeddings([text])[0].values

        print(f"  Using: Vertex AI {VERTEX_EMBEDDING_MODEL}")
        return embed_vertex
    except Exception as e:
        print(f"  Vertex AI unavailable ({e}), falling back to OpenAI...")

    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and not api_key.startswith("sk-..."):
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        def embed_openai(text: str) -> List[float]:
            resp = client.embeddings.create(input=text, model="text-embedding-3-small")
            return resp.data[0].embedding

        print("  Using: OpenAI text-embedding-3-small")
        return embed_openai

    raise RuntimeError(
        "No embedding provider available. "
        "Set GOOGLE_APPLICATION_CREDENTIALS in .env (Vertex AI) or OPENAI_API_KEY."
    )


# ─── Step 4: Build index ──────────────────────────────────────────────────────

def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> int:
    """
    Full pipeline: read docs → preprocess → chunk → embed → upsert into ChromaDB.
    Returns total chunk count.
    """
    print(f"Building index from: {docs_dir}")
    print(f"ChromaDB path: {db_dir}  |  Collection: {COLLECTION_NAME}\n")

    db_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_dir))

    # Drop and recreate to avoid stale data on re-runs
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Dropped existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    embed = _get_embed_fn()

    doc_files = sorted(DOCS_DIR.glob("*.txt"))
    if not doc_files:
        raise FileNotFoundError(f"No .txt files found in {DOCS_DIR}")

    total = 0
    for filepath in doc_files:
        raw = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw, filepath.name)
        chunks = chunk_document(doc)

        ids, embeddings, documents, metadatas = [], [], [], []
        for i, chunk in enumerate(chunks):
            ids.append(f"{filepath.stem}_{i:03d}")
            embeddings.append(embed(chunk["text"]))
            documents.append(chunk["text"])
            metadatas.append(chunk["metadata"])

        collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        total += len(chunks)
        print(f"  [{filepath.name}] {len(chunks)} chunks indexed")

    print(f"\nDone. Total chunks: {total}")
    return total


# ─── Inspect ──────────────────────────────────────────────────────────────────

def inspect(db_dir: Path = CHROMA_DB_DIR, n: int = 5) -> None:
    client = chromadb.PersistentClient(path=str(db_dir))
    col = client.get_collection(COLLECTION_NAME)
    results = col.get(limit=n, include=["documents", "metadatas"])
    print(f"\n=== Sample chunks from '{COLLECTION_NAME}' ===")
    for doc, meta in zip(results["documents"], results["metadatas"]):
        print(f"\n  source={meta.get('source')}  section={meta.get('section')}")
        print(f"  dept={meta.get('department')}  date={meta.get('effective_date')}")
        print(f"  text: {doc[:120]}...")

    # Metadata coverage
    all_meta = col.get(include=["metadatas"])["metadatas"]
    total = len(all_meta)
    missing_date = sum(1 for m in all_meta if m.get("effective_date") in ("unknown", "", None))
    sources = {}
    for m in all_meta:
        s = m.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1

    print(f"\n=== Metadata coverage ({total} chunks) ===")
    for src, count in sorted(sources.items()):
        print(f"  {src}: {count} chunks")
    print(f"  Missing effective_date: {missing_date}/{total}")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Day 09 — Build ChromaDB Index")
    print("=" * 60)
    build_index()
    inspect()
    print("\nIndex ready. Run: uv run python graph.py")
