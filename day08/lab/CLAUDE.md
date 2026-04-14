# CLAUDE.md — Lab Day 08: Full RAG Pipeline

## Project Overview
Vietnamese IT Helpdesk RAG assistant. Answers questions about company policies, SLA tickets, access control, and HR. Built with ChromaDB + OpenAI.

## Tech Stack
- **Embeddings:** OpenAI `text-embedding-3-small`
- **LLM:** OpenAI `gpt-4o-mini` (temperature=0)
- **Vector Store:** ChromaDB PersistentClient
- **Sparse Search:** BM25 (rank-bm25)
- **Sprint 3 Variant:** Hybrid retrieval (Dense + BM25 via RRF)

## Implementation Status

### Sprint 1 — index.py ✓ DONE
- [x] `get_embedding()` — OpenAI text-embedding-3-small
- [x] `build_index()` — preprocess → chunk → embed → ChromaDB upsert
- [x] `_split_by_size()` — skipped improvement, all sections fit within 1600 chars
- Result: 29 chunks indexed (HR:5, IT:11, IT Security:7, CS:6), 0 missing metadata

### Sprint 2 — rag_answer.py
- [x] `retrieve_dense()` — ChromaDB cosine search
- [ ] `call_llm()` — OpenAI gpt-4o-mini (Tech Lead)

### Sprint 3 — rag_answer.py
- [x] `retrieve_sparse()` — BM25 keyword search
- [x] `retrieve_hybrid()` — Dense + BM25 via Reciprocal Rank Fusion (RRF, 1-based ranks, exposes per-source debug scores)
- Chosen variant: **Hybrid** — corpus has natural language (policy) + exact terms (P1, ERR-403, Level 3)

### Sprint 4 — eval.py
- [ ] `score_faithfulness()` — LLM-as-Judge
- [ ] `score_answer_relevance()` — LLM-as-Judge
- [ ] `score_completeness()` — LLM-as-Judge
- [x] `score_context_recall()` — already implemented (partial path match)
- [ ] Uncomment variant + A/B comparison in main

## Running Order
```bash
uv run python index.py    # Build ChromaDB index
uv run python rag_answer.py  # Test retrieval + answer
uv run python eval.py     # Run scorecard + A/B comparison
```

## Key Files
- `data/docs/` — 5 source documents (txt)
- `data/test_questions.json` — 10 test questions with expected answers
- `chroma_db/` — ChromaDB vector store (generated)
- `results/` — scorecard outputs (generated)
- `logs/` — grading run log (generated)

## Notes
- OPENAI_API_KEY is in .env
- All scoring uses LLM-as-Judge (bonus points)
- grading_questions.json released at 17:00 — use best config (hybrid, use_rerank=False)
- Abstain behavior: prompt forces "do not know" when context insufficient
