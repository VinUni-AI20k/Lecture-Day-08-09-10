from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class ChromaConfig:
    db_path: str
    collection_name: str
    model_name: str

    @classmethod
    def from_env(cls, root: Path) -> "ChromaConfig":
        return cls(
            db_path=os.environ.get("CHROMA_DB_PATH", str(root / "chroma_db")),
            collection_name=os.environ.get("CHROMA_COLLECTION", "day10_kb"),
            model_name=os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        )


def _row_content_hash(row: Dict[str, Any]) -> str:
    payload = "|".join(
        [
            str(row.get("doc_id", "")),
            str(row.get("effective_date", "")),
            str(row.get("chunk_text", "")),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def connect_collection(root: Path):
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError as exc:
        raise RuntimeError("chromadb chưa cài. pip install -r requirements.txt") from exc

    cfg = ChromaConfig.from_env(root)
    client = chromadb.PersistentClient(path=cfg.db_path)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=cfg.model_name)
    collection = client.get_or_create_collection(name=cfg.collection_name, embedding_function=embedding_fn)
    return cfg, client, collection


def sync_cleaned_rows(collection, rows: List[Dict[str, Any]], *, run_id: str) -> Dict[str, Any]:
    content_hashes = [_row_content_hash(r) for r in rows]
    ids = content_hashes
    unique_ids = set(ids)
    duplicate_ids_in_batch = len(ids) - len(unique_ids)
    content_hashes = [_row_content_hash(r) for r in rows]

    current = collection.get(include=[])
    existing_ids = list(current.get("ids") or [])
    existing_id_set = set(existing_ids)
    prune_ids = sorted(existing_id_set - unique_ids)
    if prune_ids:
        collection.delete(ids=prune_ids)

    documents = [str(r.get("chunk_text", "")) for r in rows]
    metadatas = []
    for row, content_hash in zip(rows, content_hashes):
        metadatas.append(
            {
                "doc_id": str(row.get("doc_id", "")),
                "effective_date": str(row.get("effective_date", "")),
                "content_hash": content_hash,
                "run_id": run_id,
            }
        )

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    refreshed = collection.get(include=["metadatas"])
    refreshed_ids = list(refreshed.get("ids") or [])
    refreshed_metadatas = list(refreshed.get("metadatas") or [])
    stored_hashes = {
        str(meta.get("content_hash", ""))
        for meta in refreshed_metadatas
        if isinstance(meta, dict) and meta.get("content_hash")
    }

    return {
        "collection_count_before": len(existing_ids),
        "collection_count_after": len(refreshed_ids),
        "embed_upsert_count": len(ids),
        "embed_prune_removed": len(prune_ids),
        "embed_duplicate_ids_in_batch": duplicate_ids_in_batch,
        "embed_unique_content_hashes": len(set(content_hashes)),
        "embed_collection_unique_ids": len(set(refreshed_ids)),
        "embed_collection_unique_hashes": len(stored_hashes),
        "embed_duplicate_ratio_pct": 0.0
        if not refreshed_ids
        else round((1 - (len(set(refreshed_ids)) / len(refreshed_ids))) * 100, 2),
        "embed_pruned_ids": prune_ids,
    }
