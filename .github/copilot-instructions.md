## Quick context for AI coding assistants

This repo contains lecture materials and a Day-08 lab (RAG pipeline) used in a short class project. The lab artifact is the canonical runnable demo: an indexing script, a retrieval/answer script, and an evaluator. When editing code, prefer small, testable changes and preserve the grading/run contracts.

Key locations:
- `day08/lab/index.py` — build index (chunk → embed → upsert)
- `day08/lab/rag_answer.py` — retrieval + grounded answer function
- `day08/lab/eval.py` — scorecard / grading harness and example logging
- `day08/lab/data/docs/` — canonical documents used for indexing
- `day08/lab/data/test_questions.json` — test questions used by eval
- `day08/lab/SCORING.md` — authoritative rules (deadlines, required metadata, log format)

Contract and conventions (do not break):
- Chunk metadata: every chunk MUST include at least `source`, `section`, and `effective_date`.
- `rag_answer()` outputs a dict with keys similar to: `answer` (string), `sources` (list), `chunks_used` (list), `config` (dict). Several scripts depend on these fields for logging and grading.
- Abstain rule: if evidence is not present in indexed docs, return a clear abstain like "NO_EVIDENCE_FOUND" rather than hallucinating facts.

Common workflows and commands (examples):
1. Install deps for the lab:
   pip install -r day08/lab/requirements.txt
2. Populate env and run a quick index preview:
   cp day08/lab/.env.example day08/lab/.env
   python day08/lab/index.py    # preview chunking + index build
3. Run retrieval / sample answer:
   python day08/lab/rag_answer.py --sample    # behaves as demo; returns dict including sources
4. Run evaluation (grading/logging):
   python day08/lab/eval.py    # produces scorecard and suggested logs (see SCORING.md)

Patterns to follow (repo-specific):
- Single-responsibility workers: retrieval vs rerank vs synthesis are separated in lab code; keep new code modular and testable.
- Variants are explicit: hybrid / dense / rerank options are implemented as separate functions; to add a variant, add a function and wire it via the config object — avoid in-place mutation of global config.
- Logging format: grading logs must follow `logs/grading_run.json` format in `SCORING.md`. Example entry:
  {
    "id": "gq01",
    "question": "...",
    "answer": "...",
    "sources": ["support/sla-p1-2026.pdf"],
    "chunks_retrieved": 3,
    "retrieval_mode": "hybrid",
    "timestamp": "2026-04-12T17:23:45"
  }

What Copilot / AI agents should prioritize:
- Preserve the indexing metadata and abstain behavior. Many grading checks and downstream scripts rely on these exact fields.
- When changing retrieval defaults (top_k, rerank), add an entry to `docs/tuning-log.md` and produce a small A/B comparison via `eval.py`.
- Keep CLI behavior stable for `index.py`, `rag_answer.py`, and `eval.py` so instructors can run grading scripts without modifications.

Quick debugging hints (from lab README):
- If answers are wrong: check `list_chunks()` output in `index.py` first (indexing), then retrieval (try hybrid vs dense), then prompt/template in `rag_answer.py` (generation).
- If pipeline crashes during grading, produce `logs/grading_run.json` entries with `"answer": "PIPELINE_ERROR: <error>"` so graders can see failure modes.

If anything here looks incomplete or you want more examples (e.g., exact function signatures to reference), tell me which file to expand and I will add targeted snippets or tests.

---
Please review and tell me any sections to expand or clarify (specific file-level examples or function signatures are easy to add).
