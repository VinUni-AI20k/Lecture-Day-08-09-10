# Individual Report — Lab Day 10: Data Pipeline & Observability

**Name:** Hoang Dinh Duy Anh

**Role:** Ingestion Owner + Cleaning & Quality Owner

**Date:** 2026-04-15

**Word count:** ~620 words

---

## 1. My responsibilities

**Files and modules:**

- `transform/cleaning_rules.py` — added Rule 7 (strip BOM and control characters), Rule 8 (quarantine chunks too short
  after strip), Rule 9 (normalise YYYY/MM/DD date format). Modified `_normalize_effective_date()` and `clean_rows()`.
- `quality/expectations.py` — added E7 (`chunk_max_length_2000`, severity=warn) and E8 (`all_doc_ids_in_allowlist`,
  severity=halt).
- `contracts/data_contract.yaml` — filled `owner_team: cs-it-helpdesk-data` and `alert_channel: #data-alerts`.
- `docs/data_contract.md` — wrote all 4 sections: source map, cleaned schema, quarantine policy covering all 6 reason
  codes, and canonical source table.
- `docs/quality_report.md` — wrote all 5 sections from real run data across sprint1, sprint2, inject-bad, and the clean
  run.

**Connection to teammates:**

The artifacts I produced (manifests, cleaned CSVs, quarantine CSVs, eval CSVs, grading JSONL) are direct inputs for the
Monitoring/Docs Owner to write `docs/runbook.md` and `reports/group_report.md`. The grading JSONL (
`artifacts/eval/grading_run.jsonl`) is the final grading evidence submitted to the instructor.

**Commit evidence:**

- `7624d98` — feat(ingest): sprint1 baseline pipeline run with manifest and artifacts
- `291fdbb` — feat(cleaning): add rules 7-9 for BOM strip, short chunk quarantine, YYYY/MM/DD date
- `e4a25d2` — feat(quality): add expectations E7 (chunk max length warn) and E8 (allowlist halt)
- `10bec5d` — feat(quality): sprint3 inject and clean run artifacts with eval evidence
- `d3b9ffa` — docs(quality): quality_report.md with sprint3 before/after evidence
- `255df24` — feat(grading): grading_run.jsonl — all 3 gq_d10 checks pass at Merit

---

## 2. One technical decision

**Decision: setting Rule 8 minimum chunk length at 8 characters instead of 20.**

When implementing Rule 8, I had two threshold options: 20 chars (initial draft) and 8 chars (aligned with E4
`chunk_min_length_8` already in the expectation suite).

Using 20 chars would quarantine valid short chunks such as policy codes or short clause headings, causing false
positives and reducing `cleaned_records` incorrectly. More importantly, it would create a contract inconsistency: Rule 8
quarantining at 20 chars while E4 only warns at 8 chars — two conflicting thresholds enforcing the same field.

Using 8 chars keeps Rule 8 and E4 consistent with `contracts/data_contract.yaml` (`chunk_text.min_length: 8`). Rows that
actually reach quarantine via Rule 8 are those whose content collapsed below 8 chars after stripping BOM and control
characters — for example, a row containing only a BOM prefix followed by 2-3 broken Unicode characters.

**Evidence:** `transform/cleaning_rules.py` — `MIN_CHUNK_TEXT_STRIPPED_LEN = 8` is declared as a module-level constant
to stay in sync with the contract rather than being hardcoded inline in the logic.

---

## 3. One anomaly identified and resolved

**Symptom:** After running the inject-bad scenario (`run_id=inject-bad`), eval showed `q_refund_window` with
`hits_forbidden=yes` while `contains_expected=yes` — both conflicting versions appeared in top-3 context simultaneously.

**Detection:** The log flagged it immediately:

```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate
embed_prune_removed=1
```

E3 reported `violations=1` — the stale "14 ngay lam viec" chunk passed through because `--no-refund-fix` disabled Rule
6. `embed_prune_removed=1` confirmed the clean chunk from sprint2 was replaced by the stale one.

**Eval result from `artifacts/eval/after_inject_bad.csv`:**

```
q_refund_window, contains_expected=yes, hits_forbidden=yes, top_k_used=3
top1_preview: "Yeu cau duoc gui trong vong 7 ngay lam viec..."
```

Top-1 was still the correct chunk ("7 ngay"), but the stale chunk ("14 ngay lam viec") was also present in top-3 — both
contradictory versions delivered to the LLM in the same context window.

**Fix:** rerun `etl_pipeline.py run` without flags, Rule 6 re-enabled:

```
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
embed_prune_removed=1
```

`embed_prune_removed=1` confirmed the stale vector id was deleted and the fixed chunk was upserted.

---

## 4. Before / after evidence

**run_id=inject-bad** (Rule 6 disabled, stale chunk in collection):

```
q_refund_window, contains_expected=yes, hits_forbidden=yes, top_k_used=3
```

**run_id=2026-04-15T09-45Z** (clean run, Rule 6 enabled):

```
q_refund_window, contains_expected=yes, hits_forbidden=no, top_k_used=3
```

`hits_forbidden` flipped from `yes` to `no` — the stale "14 ngay lam viec" chunk was fully pruned from the collection.
This is consistent with `embed_prune_removed=1` in both run logs: inject-bad (clean replaced by stale) and clean run (
stale replaced by fixed).

**Merit — q_leave_version (both runs):**

```
q_leave_version, contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes
```

The stale HR row (effective_date=2025-01-01, "10 ngay phep nam") was quarantined by Rule 3 in sprint1 and never entered
the vector store in either scenario.

**Grading JSONL (`artifacts/eval/grading_run.jsonl`):**

```
gq_d10_01: contains_expected=true, hits_forbidden=false
gq_d10_02: contains_expected=true, hits_forbidden=false
gq_d10_03: contains_expected=true, hits_forbidden=false, top1_doc_matches=true
```

All 3 questions pass at Merit tier. Verified by `instructor_quick_check.py`:

```
MERIT_CHECK[gq_d10_01] OK :: refund window + khong forbidden trong top-k
MERIT_CHECK[gq_d10_02] OK :: P1 resolution SLA
MERIT_CHECK[gq_d10_03] OK :: HR 12 ngay + top1 doc_id + khong 10 ngay stale trong top-k
```

---

## 5. Next improvement

If given 2 more hours, I would implement dual-boundary freshness monitoring. Currently `freshness_check.py` only
measures at the `publish` boundary using `run_timestamp` from the manifest. In production, the critical gap is between
`exported_at` (when data left the source system) and `published_at` (when the chunk reached the vector store) — these
two can differ by hours if the pipeline has queues or retries. The concrete change: add an `ingest_started_at` field to
the manifest and compute both the ingest lag (`ingest_started_at - exported_at`) and the publish lag (
`run_timestamp - ingest_started_at`) separately, rather than reporting a single total age. This would make the freshness
SLI actionable — you could tell whether the delay is in the source export or in the pipeline itself.
