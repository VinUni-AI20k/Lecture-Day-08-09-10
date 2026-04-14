# Plan: Sprint 1 — Build RAG Index

## Context

Sprint 1 is about building the indexing pipeline: read 5 policy documents, chunk them by section, embed with OpenAI, and store in ChromaDB. The skeleton code in `index.py` already handles preprocessing and chunking — the two critical missing pieces are `get_embedding()` and the ChromaDB upsert block inside `build_index()`.

**Who starts first:** The **Retrieval Owner** is the natural lead for Sprint 1 — their responsibility is *chunking, metadata, and retrieval strategy*. The **Tech Lead** should pair with them to keep things wired end-to-end and unblock Sprint 2 quickly. The other two roles (Eval Owner, Documentation Owner) can review the 10 test questions and start reading the architecture template while Sprint 1 runs.

---

## Changes

### File: `index.py`

#### 1. Implement `get_embedding()` (line 223)
Replace the `raise NotImplementedError` with an OpenAI embedding call:
```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = client.embeddings.create(input=text, model="text-embedding-3-small")
return response.data[0].embedding
```

#### 2. Wire up `build_index()` (line 250)
Replace the placeholder block (lines 271–317) with the actual ChromaDB pipeline:
- Initialize `chromadb.PersistentClient` + `get_or_create_collection("rag_lab", metadata={"hnsw:space": "cosine"})`
- For each file: `preprocess_document()` → `chunk_document()` → for each chunk call `get_embedding()` and `collection.upsert()`
- Remove the old placeholder print statements

#### 3. (Optional) Improve `_split_by_size()` (line 173)
Currently splits by raw character offset. Improve to split by paragraph (`\n\n`) boundaries so chunks don't cut mid-sentence. This is nice-to-have — the current version is functional.

#### 4. Uncomment verification in `__main__` (line 397)
- Uncomment `build_index()`, `list_chunks()`, and `inspect_metadata_coverage()` calls so running `python index.py` does the full pipeline + verification.

---

## Verification

```bash
uv run python index.py
```

**Expected output:**
- "Processing: ..." for each of the 5 `.txt` files
- Total chunks count (expect ~15–25 chunks across 5 docs)
- `list_chunks()` prints top 5 chunks with `source`, `section`, `effective_date` all populated
- `inspect_metadata_coverage()` shows distribution by department (CS, IT, IT Security, HR)

**Definition of Done checks:**
- [x] Script runs without error
- [x] All 5 documents indexed (29 chunks: HR:5, IT:11, IT Security:7, CS:6)
- [x] Each chunk has at least 3 metadata fields: `source`, `section`, `effective_date`
- [x] `list_chunks()` shows chunks aren't cut mid-clause
- [x] `_split_by_size()` improvement skipped — all sections fit within 1600 chars, early return handles all cases

## Sprint 1 — DONE ✓

---

# Plan: Sprint 2 + 3 — Retrieval Owner

## Sprint 2 Status

### `retrieve_dense()` — DONE ✓
- Embeds query with `get_embedding()` (same model as index)
- Queries ChromaDB `"rag_lab"` collection
- Returns list of `{text, metadata, score}` dicts
- Score = `1 - distance` (ChromaDB cosine distance → similarity)

### `call_llm()` — Pending Tech Lead
Not retrieval owner's responsibility.

---

## Sprint 3 — Next Steps (Retrieval Owner)

### 1. Implement `retrieve_sparse()` (line 90)
- Install: `uv add rank-bm25`
- Load all chunks from ChromaDB
- Build `BM25Okapi` index over chunk texts
- Tokenize query, get scores, return top_k as `{text, metadata, score}` dicts

### 2. Implement `retrieve_hybrid()` (line 122)
- Call `retrieve_dense()` + `retrieve_sparse()`
- Merge with Reciprocal Rank Fusion (RRF):
  `score(doc) = 0.6 * 1/(60 + dense_rank) + 0.4 * 1/(60 + sparse_rank)`
- Sort by RRF score, return top_k

### 3. Uncomment comparison block in `__main__` (line 484)
```python
compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
compare_retrieval_strategies("ERR-403-AUTH")
```

## Sprint 3 — DONE ✓

### `retrieve_sparse()` — DONE ✓
- Loads all chunks from ChromaDB at query time
- Builds `BM25Okapi` index over tokenized chunk texts
- Returns top_k as `{text, metadata, score}` dicts (raw BM25 scores)

### `retrieve_hybrid()` — DONE ✓
- Calls `retrieve_dense()` + `retrieve_sparse()` in parallel
- RRF merge with 1-based ranks: `score = 0.6/(60+dense_rank) + 0.4/(60+sparse_rank)`
- Each result exposes `dense_score`, `sparse_score`, `dense_rrf_score`, `sparse_rrf_score` for debugging
- Copilot improvement: `enumerate(start=1)` for correct standard RRF formula
