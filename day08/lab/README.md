# Lab Day 08 — Full RAG Pipeline: Indexing Completed

This repository contains a high-performance RAG (Retrieval-Augmented Generation) indexing pipeline built for an internal CS & IT Helpdesk assistant.

## Implementation Status

| Sprint | Goal | Status | Key Features |
| :--- | :--- | :--- | :--- |
| **Sprint 1** | **Indexing & Metadata** | **DONE** | Specialized chunking, full metadata schema, ChromaDB + Sentence Transformers. |
| Sprint 2 | Baseline Retrieval | *Pending* | - |
| Sprint 3 | Tuning | *Pending* | - |
| Sprint 4 | Evaluation | *Pending* | - |

---

## Sprint 1: Indexing Strategy

I have implemented a robust indexing pipeline in `index.py` that handles diverse document types with specialized logic.

### 1. Document-Specific Chunking
| Document | Strategy | Why? |
| :--- | :--- | :--- |
| **SLA P1 2026** | Priority Grouping | Combines Definitions and SLAs for each P-level into single chunks for full context. |
| **Refund Policy v4** | Article-based | Ensures rules for "Exceptions" (Article 3) are isolated to prevent dilution. |
| **Access Control SOP** | Section-based | Standard split with an injected **Alias Chunk** ("Approval Matrix") for historical queries. |
| **IT Helpdesk FAQ** | Q&A Pair | Each question is an independent chunk to maximize retrieval precision for micro-queries. |
| **HR Leave Policy** | Section-based | Isolates "Remote Work Policy" (Part 4) for specific eligibility questions. |

### 2. Full Metadata Schema
Every chunk is enriched with a comprehensive metadata dictionary to support advanced retrieval:
- `doc_id`: Unique identifier for the source document.
- `chunk_id`: Hierarchical ID (e.g., `sla_p1_2026_c01`).
- `section_title`: Human-readable section name.
- `department`: IT, HR, CS, etc.
- `effective_date`: Versioning control.
- `prev_chunk_id` / `next_chunk_id`: Enables **Sliding Window Retrieval** or context expanding.
- `aliases`: For historical or alternative names (e.g., `Approval Matrix`).
- `char_count`: Optimization tracking.

### 3.Embedding & Storage
- **Model**:
 + `"text-embedding-3-small"`: OpenAI API (if not, fall back to local)
 + `paraphrase-multilingual-MiniLM-L12-v2` via `SentenceTransformers` (local, no API cost).
- **Store**: **ChromaDB** with Cosine similarity (`hnsw:space: cosine`).
- **Batching**: Optimized upsert logic with `tqdm` progress bars.

---

## How to Run

### Setup Environment
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. (Optional) Configure `.env` if using OpenAI/Gemini later. Sprint 1 is fully local.

### Execute Indexing
Run the pipeline to preprocess, chunk, and index all documents:
```bash
python index.py
```

### Verify Index
The script will automatically run verification steps at the end:
- `list_chunks()`: Displays the top records in the DB to check format and metadata.
- `inspect_metadata_coverage()`: Shows the distribution of chunks across departments and identifies missing fields.

---

## Progress Summary
- **Total Documents**: 5
- **Total Chunks**: 35
- **Performance**: Normalized metadata extraction ensures no `UnicodeEncodeError` in the terminal output.
