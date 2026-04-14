"""
build_index.py — Build ChromaDB index from data/docs/
Chạy 1 lần để index 5 tài liệu nội bộ vào ChromaDB.

Usage:
    python build_index.py
"""

import os
import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = "./data/docs"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "day09_docs"
CHUNK_SIZE = 500  # characters per chunk
CHUNK_OVERLAP = 100


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


def build_index():
    print("=" * 50)
    print("Building ChromaDB Index")
    print("=" * 50)

    # Load embedding model
    print("\n[*] Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Create ChromaDB client
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Delete old collection if exists
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"[*] Deleted old collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # Index documents
    all_ids = []
    all_docs = []
    all_embeddings = []
    all_metadatas = []

    doc_files = sorted(os.listdir(DOCS_DIR))
    print(f"\n[*] Found {len(doc_files)} documents in {DOCS_DIR}")

    for fname in doc_files:
        if not fname.endswith(".txt"):
            continue
        filepath = os.path.join(DOCS_DIR, fname)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        chunks = chunk_text(content)
        print(f"  - {fname}: {len(content)} chars -> {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            doc_id = f"{fname}__chunk_{i:03d}"
            embedding = model.encode(chunk).tolist()

            all_ids.append(doc_id)
            all_docs.append(chunk)
            all_embeddings.append(embedding)
            all_metadatas.append({
                "source": fname,
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

    # Add to collection
    collection.add(
        ids=all_ids,
        documents=all_docs,
        embeddings=all_embeddings,
        metadatas=all_metadatas,
    )

    print(f"\n[OK] Indexed {len(all_ids)} chunks into '{COLLECTION_NAME}'")
    print(f"     ChromaDB path: {CHROMA_PATH}")

    # Verify
    print(f"\n[*] Verification: collection has {collection.count()} documents")
    test_query = "SLA ticket P1"
    test_emb = model.encode(test_query).tolist()
    results = collection.query(query_embeddings=[test_emb], n_results=2)
    print(f"    Test query: '{test_query}'")
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        print(f"    [{1-dist:.3f}] {meta['source']}: {doc[:80].encode('ascii', 'replace').decode()}...")


if __name__ == "__main__":
    build_index()
