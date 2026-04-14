"""
build_index.py — Build ChromaDB collection `day09_docs` for Day 09 lab.

Uses the same chunking style as Day 08 (section headings + size split) and
`sentence-transformers` embeddings (all-MiniLM-L6-v2) to match workers/retrieval.py.

Usage (from day09/lab):
    python build_index.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List

import chromadb

# Match workers/retrieval.py default embedding model
EMBED_MODEL = os.getenv("DAY09_EMBED_MODEL", "all-MiniLM-L6-v2")

LAB_ROOT = Path(__file__).resolve().parent
DOCS_DIR = LAB_ROOT / "data" / "docs"
CHROMA_DIR = LAB_ROOT / "chroma_db"
COLLECTION = "day09_docs"

CHUNK_SIZE = 400  # ~tokens, as in Day 08
CHUNK_OVERLAP = 80
CHUNK_CHARS = CHUNK_SIZE * 4
OVERLAP_CHARS = CHUNK_OVERLAP * 4


def preprocess_document(raw_text: str, filepath: Path) -> Dict[str, Any]:
    lines = raw_text.strip().split("\n")
    metadata: Dict[str, Any] = {
        "source": filepath.name,
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }
    content_lines: List[str] = []
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
            elif line.strip() == "" or (line.isupper() and len(line) < 80):
                continue
        else:
            content_lines.append(line)
    cleaned = "\n".join(content_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # Citation-friendly source id = filename
    metadata["source_file"] = filepath.name
    return {"text": cleaned, "metadata": metadata}


def _soft_break_end(text: str, start: int, end: int) -> int:
    window = text[start:end]
    min_end = start + max(80, (end - start) // 2)
    for sep in ("\n\n", "\n", ". ", ": ", "; ", " "):
        pos = window.rfind(sep)
        if pos != -1:
            cand = start + pos + len(sep)
            if cand >= min_end:
                return cand
    return end


def _split_by_size(
    text: str,
    base_metadata: Dict[str, Any],
    section: str,
) -> List[Dict[str, Any]]:
    text = text.strip()
    if not text:
        return []
    meta = {**base_metadata, "section": section}
    if len(text) <= CHUNK_CHARS:
        return [{"text": text, "metadata": meta}]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text]
    out: List[Dict[str, Any]] = []
    buf: List[str] = []

    def buf_len() -> int:
        if not buf:
            return 0
        return sum(len(x) + 2 for x in buf) - 2

    def flush_buf() -> None:
        if not buf:
            return
        out.append({"text": "\n\n".join(buf), "metadata": {**meta}})
        buf.clear()

    i = 0
    while i < len(paragraphs):
        p = paragraphs[i]
        if len(p) > CHUNK_CHARS:
            flush_buf()
            s = 0
            while s < len(p):
                e = min(s + CHUNK_CHARS, len(p))
                if e < len(p):
                    e = _soft_break_end(p, s, e)
                piece = p[s:e].strip()
                if piece:
                    out.append({"text": piece, "metadata": {**meta}})
                if e >= len(p):
                    break
                s = max(s + 1, e - OVERLAP_CHARS)
            i += 1
            continue
        extra = len(p) + (2 if buf else 0)
        if buf and buf_len() + extra > CHUNK_CHARS:
            flush_buf()
            if out:
                tail = out[-1]["text"]
                ov = tail[-OVERLAP_CHARS:] if len(tail) > OVERLAP_CHARS else tail
                buf = [ov, p] if ov.strip() else [p]
            else:
                buf = [p]
        else:
            buf.append(p)
        i += 1
    flush_buf()
    return out


def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = doc.get("text") or ""
    base_metadata = doc["metadata"].copy()
    if not text.strip():
        return []
    sections = re.split(r"(===.*?===)", text)
    current_section = "General"
    current_section_text = ""
    chunks: List[Dict[str, Any]] = []
    for part in sections:
        if re.match(r"===.*?===", part):
            if current_section_text.strip():
                chunks.extend(
                    _split_by_size(current_section_text.strip(), base_metadata, current_section)
                )
            current_section = part.strip("= ").strip()
            current_section_text = ""
        else:
            current_section_text += part
    if current_section_text.strip():
        chunks.extend(
            _split_by_size(current_section_text.strip(), base_metadata, current_section)
        )
    return chunks


def _metadata_for_chroma(meta: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in meta.items():
        if v is None:
            out[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def build_index() -> None:
    from sentence_transformers import SentenceTransformer

    print(f"Docs: {DOCS_DIR}")
    print(f"Chroma: {CHROMA_DIR}  collection={COLLECTION}")

    doc_files = sorted(DOCS_DIR.glob("*.txt"))
    if not doc_files:
        raise SystemExit(f"No .txt files in {DOCS_DIR}")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    model = SentenceTransformer(EMBED_MODEL)
    global_idx = 0
    for filepath in doc_files:
        print(f"  {filepath.name} ...")
        raw = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw, filepath)
        chunks = chunk_document(doc)
        print(f"    -> {len(chunks)} chunks")
        for ch in chunks:
            emb = model.encode(ch["text"], normalize_embeddings=True).tolist()
            cid = f"{filepath.stem}_{global_idx}"
            global_idx += 1
            meta = _metadata_for_chroma(ch["metadata"])
            meta["source"] = filepath.name
            collection.upsert(
                ids=[cid],
                embeddings=[emb],
                documents=[ch["text"]],
                metadatas=[meta],
            )
    print(f"Done. Total chunks: {global_idx}")


if __name__ == "__main__":
    build_index()
