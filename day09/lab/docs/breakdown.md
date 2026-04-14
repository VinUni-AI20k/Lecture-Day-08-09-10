# Pipeline Algorithm Breakdown

A technical reference for the algorithms and data flows in the Day 09 multi-agent pipeline.

---

## Part 1 — Build Index (`scripts/build_index.py`)

**Run result:** 29 chunks indexed, 0 missing metadata

### Step 1 — Preprocess each document

Each `.txt` file in `data/docs/` starts with a small header block:

```
SLA TICKET - QUY ĐỊNH XỬ LÝ SỰ CỐ
Source: support/sla-p1-2026.pdf
Department: IT
Effective Date: 2026-01-15
Access: internal
```

The script reads these lines before the first `=== ... ===` section heading and extracts them as **metadata** (`source`, `department`, `effective_date`, `access`). Everything after the first heading becomes the document body. Blank lines and all-uppercase title lines are dropped.

Result: a clean `{text, metadata}` dict per file.

---

### Step 2 — Chunk by section

The body is split on `=== Section Name ===` headings using a regex. Each section becomes its own chunk, preserving natural policy boundaries (e.g. "Điều kiện hoàn tiền", "Escalation P1", "Level 3 Access").

If a section is longer than ~1600 characters (`CHUNK_SIZE=400 tokens × 4`), it is further split on paragraph boundaries (`\n\n`), with an **80-token overlap** — the last paragraph of the previous chunk is prepended to the next one to preserve cross-paragraph context.

In practice, all 29 sections in these 5 docs fit within the 1600-char limit, so no secondary splitting was triggered.

---

### Step 3 — Embed with Vertex AI

Each chunk's text is sent to **Vertex AI `text-multilingual-embedding-002`** (project `vinai053`, region `us-central1`) which returns a high-dimensional float vector. This model handles Vietnamese text natively.

Credentials: `vinai053-37cad4a3b18c.json` (service account), path resolved relative to lab root from `GOOGLE_APPLICATION_CREDENTIALS` in `.env`.

Fallback: if Vertex AI is unavailable, the script falls back to OpenAI `text-embedding-3-small`.

---

### Step 4 — Upsert into ChromaDB

All chunks for a file are batch-upserted into the `day09_docs` collection in a local ChromaDB `PersistentClient` at `./chroma_db/`. The collection uses **cosine similarity** (`hnsw:space: cosine`).

Each record stored:
- `id`: `{filename_stem}_{index}` (e.g. `sla_p1_2026_002`)
- `embedding`: Vertex AI float vector
- `document`: raw chunk text
- `metadata`: `{source, section, department, effective_date, access}`

The collection is dropped and recreated on each run to avoid stale data.

---

## Result

| Source file | Logical source | Chunks |
|-------------|----------------|--------|
| `sla_p1_2026.txt` | `support/sla-p1-2026.pdf` | 5 |
| `access_control_sop.txt` | `it/access-control-sop.md` | 7 |
| `policy_refund_v4.txt` | `policy/refund-v4.pdf` | 6 |
| `it_helpdesk_faq.txt` | `support/helpdesk-faq.md` | 6 |
| `hr_leave_policy.txt` | `hr/leave-policy-2026.pdf` | 5 |
| **Total** | | **29** |

- Missing `effective_date`: 0
- Embedding provider used: Vertex AI `text-multilingual-embedding-002`
- Collection: `day09_docs` (cosine similarity)

---

## Why this chunking strategy

Section-based splitting was chosen over fixed-size sliding window because these documents are **structured policy texts** — each section (`=== Điều kiện ===`, `=== Ngoại lệ ===`) is semantically self-contained. Cutting across section boundaries would mix unrelated rules into a single chunk, hurting retrieval precision for multi-hop questions like gq09.

---

## Part 2 — Retrieval Worker (`workers/retrieval.py`)

**Status:** Running, hybrid mode active.

The retrieval worker exposes three retrieval modes and defaults to hybrid.

### Dense retrieval

1. Embed the query using Vertex AI `text-multilingual-embedding-002` (same model as indexing — vector space is consistent).
2. Query ChromaDB with the query vector, `n_results=top_k`, cosine similarity.
3. Convert distance → similarity: `score = 1 - cosine_distance`.

**Strength:** Captures semantic meaning, handles paraphrase and Vietnamese synonyms.  
**Weakness:** Misses exact terms that weren't seen during training (e.g. `ERR-403`, `Level 3`).

### Sparse retrieval (BM25)

1. On first call, load all 29 documents from ChromaDB and build a `BM25Okapi` index. Cached in-memory for subsequent calls.
2. Tokenise query with `.lower().split()`.
3. Score all documents with `bm25.get_scores(query_tokens)`.
4. Return top-k by score.

BM25 formula: `score(d,q) = Σ IDF(t) × (f(t,d) × (k1+1)) / (f(t,d) + k1×(1 - b + b×|d|/avgdl))`  
Default `k1=1.5, b=0.75` from `rank-bm25`.

**Strength:** Exact keyword match — critical for terms like `P1`, `Flash Sale`, `Level 3`, `contractor`.  
**Weakness:** No semantic understanding; misses paraphrase.

### Hybrid retrieval (RRF) — default

Combines both lists using **Reciprocal Rank Fusion** (k=60):

```
RRF_score(doc) = dense_weight × 1/(60 + dense_rank)
               + sparse_weight × 1/(60 + sparse_rank)
```

Default weights: `dense=0.6, sparse=0.4` (semantic slightly favoured; exact terms still influential).

Constant `k=60` is the standard RRF value — dampens the effect of top-ranked documents to prevent either list from dominating.

All unique documents from both lists are merged, scored, sorted descending, and top-k returned. Each result also exposes `dense_rrf_score` and `sparse_rrf_score` for trace inspection.

**Why hybrid is the default:** Day 08's evaluation showed hybrid reached faithfulness 5.00 (vs 4.60 for dense-only) by correctly handling edge cases with exact terms. Day 09 inherits this as the baseline config.

---

## Part 3 — Synthesis Worker (`workers/synthesis.py`)

**Status:** Running, OpenAI `gpt-4o-mini`, temperature=0.

### Context building

Retrieved chunks are numbered `[1]`, `[2]`, `[3]` with their source filename and relevance score. Policy exceptions from the policy worker are appended as a separate section. If no context is available, the context string is `"(Không có context)"`.

### LLM call

System prompt enforces three hard rules:
1. Answer **only** from provided context — no external knowledge.
2. If context is insufficient → say `"Không đủ thông tin trong tài liệu nội bộ"` (abstain).
3. Cite source at the end of each key statement using `[source_filename]`.

`temperature=0` ensures deterministic, grounded output.

### Confidence scoring (dynamic)

RRF scores are in the ~0.008–0.02 range (1/(60+rank) scale), not 0–1 cosine range. The confidence estimator normalises relative to the max score in the result set before averaging:

```
normalised_scores = [s / max_score for s in raw_scores]   # if max < 0.1
avg_score = mean(normalised_scores)
exception_penalty = 0.05 × len(exceptions_found)
confidence = clamp(avg_score - exception_penalty, 0.1, 0.95)
```

This produces meaningful confidence values (0.7–0.9 for well-retrieved answers, 0.3 for abstains, 0.1 for no-evidence) without hardcoding.

---

## Part 4 — Supervisor + Graph (`graph.py`)

### Routing logic

The supervisor reads the task string and applies keyword rules in priority order:

| Signal in task | Route | `needs_tool` | `risk_high` |
|----------------|-------|--------------|-------------|
| `hoàn tiền`, `refund`, `flash sale`, `license`, `cấp quyền`, `access`, `level 3` | `policy_tool_worker` | True | — |
| `emergency`, `khẩn cấp`, `2am`, `không rõ`, `err-` | any + `risk_high=True` | — | True |
| `err-` + `risk_high` | `human_review` | — | True |
| (default) | `retrieval_worker` | False | False |

After routing, `route_reason` is written to state — every answer in the grading log carries this field.

### Graph flow

```
Input
  └─▶ supervisor_node         (classify + set route)
        └─▶ route_decision     (conditional branch)
              ├─▶ retrieval_worker_node    → synthesis_worker_node → END
              ├─▶ policy_tool_worker_node  → (retrieval if no chunks) → synthesis_worker_node → END
              └─▶ human_review_node        → retrieval_worker_node  → synthesis_worker_node → END
```

State is a single `AgentState` TypedDict passed through every node. Workers append to `workers_called`, `history`, and `worker_io_logs` at each step — giving full trace lineage without any extra instrumentation.
