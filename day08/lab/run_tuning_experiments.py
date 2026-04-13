#!/usr/bin/env python3
"""
Automated experiment runner for Day08 lab tuning plan.

Pipeline:
- Baseline
- Phase 1: chunking search
- Phase 2: retrieval strategy search
- Phase 3: technical improvements (rerank/query transform)

Assumes eval.py scoring is already implemented (e.g., LLM-as-a-judge).
"""

import csv
import hashlib
import json
import os
import re
import time
import traceback
import importlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

eval_mod = None
index_mod = None
rag_mod = None


CHUNK_SIZES = [350, 500, 700]
CHUNK_OVERLAPS = [50, 80, 120]
PHASE1_FIXED_OVERLAP = 80

CHUNK_STRATEGIES = {
    "size": "_split_by_size",
    "paragraph_recursive": "_split_by_paragraph_recursive",
    "two_separators": "_split_by_recursive_two_separators",
}

RETRIEVAL_VARIANTS = [
    {"retrieval_mode": "dense", "label": "dense"},
    {"retrieval_mode": "sparse", "label": "sparse"},
    {
        "retrieval_mode": "hybrid",
        "hybrid_dense_weight": 0.5,
        "hybrid_sparse_weight": 0.5,
        "label": "hybrid_50_50",
    },
    {
        "retrieval_mode": "hybrid",
        "hybrid_dense_weight": 0.6,
        "hybrid_sparse_weight": 0.4,
        "label": "hybrid_60_40",
    },
    {
        "retrieval_mode": "hybrid",
        "hybrid_dense_weight": 0.7,
        "hybrid_sparse_weight": 0.3,
        "label": "hybrid_70_30",
    },
]

OBJECTIVE_WEIGHTS = {
    "faithfulness": 0.35,
    "relevance": 0.35,
    "completeness": 0.20,
    "context_recall": 0.10,
}


ORIGINAL_CHUNK_DOCUMENT = None
ORIGINAL_RETRIEVE_HYBRID = None
ORIGINAL_EVAL_RAG_ANSWER = None


@dataclass
class RunResult:
    run_id: int
    phase: str
    label: str
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int
    retrieval_mode: str
    hybrid_dense_weight: Optional[float]
    hybrid_sparse_weight: Optional[float]
    use_rerank: bool
    query_transform: bool
    query_transform_strategy: str
    averages: Dict[str, Optional[float]]
    objective: float
    run_dir: Path
    scorecard_rows: List[Dict[str, Any]]


def append_progress(progress_file: Optional[Path], payload: Dict[str, Any]) -> None:
    if progress_file is None:
        return
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        **payload,
    }
    with open(progress_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_lab_modules() -> None:
    global eval_mod, index_mod, rag_mod
    global ORIGINAL_CHUNK_DOCUMENT, ORIGINAL_RETRIEVE_HYBRID, ORIGINAL_EVAL_RAG_ANSWER

    eval_mod = importlib.import_module("eval")
    index_mod = importlib.import_module("index")
    rag_mod = importlib.import_module("rag_answer")

    ORIGINAL_CHUNK_DOCUMENT = index_mod.chunk_document
    ORIGINAL_RETRIEVE_HYBRID = rag_mod.retrieve_hybrid
    ORIGINAL_EVAL_RAG_ANSWER = eval_mod.rag_answer


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
    return text.strip("_")[:80] or "run"


def compute_averages(rows: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]
    out: Dict[str, Optional[float]] = {}
    for metric in metrics:
        vals = [r.get(metric) for r in rows if isinstance(r.get(metric), (int, float))]
        out[metric] = (sum(vals) / len(vals)) if vals else None
    return out


def compute_objective(avg: Dict[str, Optional[float]]) -> float:
    score = 0.0
    for metric, weight in OBJECTIVE_WEIGHTS.items():
        value = avg.get(metric)
        score += weight * (value if value is not None else 0.0)
    return score


def _select_splitter(strategy: str):
    fn_name = CHUNK_STRATEGIES[strategy]
    return getattr(index_mod, fn_name)


def _build_chunk_document_with_strategy(strategy: str):
    splitter = _select_splitter(strategy)

    def _chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        text = doc["text"]
        base_metadata = doc["metadata"].copy()
        chunks: List[Dict[str, Any]] = []

        sections = re.split(r"(===.*?===)", text)
        current_section = "General"
        current_section_text = ""

        for part in sections:
            if re.match(r"===.*?===", part):
                if current_section_text.strip():
                    section_chunks = splitter(
                        current_section_text.strip(),
                        base_metadata=base_metadata,
                        section=current_section,
                    )
                    chunks.extend(section_chunks)
                current_section = part.strip("= ").strip()
                current_section_text = ""
            else:
                current_section_text += part

        if current_section_text.strip():
            section_chunks = splitter(
                current_section_text.strip(),
                base_metadata=base_metadata,
                section=current_section,
            )
            chunks.extend(section_chunks)

        return chunks

    return _chunk_document


def apply_chunking_config(strategy: str, chunk_size: int, chunk_overlap: int) -> None:
    index_mod.CHUNK_SIZE = chunk_size
    index_mod.CHUNK_OVERLAP = chunk_overlap
    index_mod.chunk_document = _build_chunk_document_with_strategy(strategy)


def apply_hybrid_weights(dense_w: Optional[float], sparse_w: Optional[float]) -> None:
    if dense_w is None or sparse_w is None:
        rag_mod.retrieve_hybrid = ORIGINAL_RETRIEVE_HYBRID
        return

    def _wrapped_hybrid(query: str, top_k: int = rag_mod.TOP_K_SEARCH, **_: Any):
        return ORIGINAL_RETRIEVE_HYBRID(
            query,
            top_k=top_k,
            dense_weight=dense_w,
            sparse_weight=sparse_w,
        )

    rag_mod.retrieve_hybrid = _wrapped_hybrid


def _chunk_key(chunk: Dict[str, Any]) -> str:
    meta = chunk.get("metadata", {}) or {}
    source = str(meta.get("source", ""))
    section = str(meta.get("section", ""))
    text = str(chunk.get("text", ""))
    fp = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
    return f"{source}|{section}|{fp}"


def make_rag_answer_with_query_transform(enabled: bool, strategy: str):
    if not enabled:
        return ORIGINAL_EVAL_RAG_ANSWER

    def _rag_answer(
        query: str,
        retrieval_mode: str = "dense",
        top_k_search: int = rag_mod.TOP_K_SEARCH,
        top_k_select: int = rag_mod.TOP_K_SELECT,
        use_rerank: bool = False,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        try:
            transformed = rag_mod.transform_query(query, strategy=strategy)
        except Exception:
            transformed = []

        queries = [query]
        for q in transformed or []:
            if q and q not in queries:
                queries.append(q)

        merged: Dict[str, Dict[str, Any]] = {}
        for q in queries:
            if retrieval_mode == "dense":
                candidates = rag_mod.retrieve_dense(q, top_k=top_k_search)
            elif retrieval_mode == "sparse":
                candidates = rag_mod.retrieve_sparse(q, top_k=top_k_search)
            elif retrieval_mode == "hybrid":
                candidates = rag_mod.retrieve_hybrid(q, top_k=top_k_search)
            else:
                raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

            for chunk in candidates:
                key = _chunk_key(chunk)
                score = float(chunk.get("score", 0) or 0)
                if key not in merged or score > float(merged[key].get("score", 0) or 0):
                    merged[key] = chunk

        all_candidates = sorted(
            merged.values(),
            key=lambda c: float(c.get("score", 0) or 0),
            reverse=True,
        )

        if use_rerank:
            selected = rag_mod.rerank(query, all_candidates, top_k=top_k_select)
        else:
            selected = all_candidates[:top_k_select]

        context_block = rag_mod.build_context_block(selected)
        prompt = rag_mod.build_grounded_prompt(query, context_block)
        answer = rag_mod.call_llm(prompt)
        sources = list({c.get("metadata", {}).get("source", "unknown") for c in selected})

        if verbose:
            print(f"[query-transform] transformed queries: {queries}")
            print(f"[query-transform] selected chunks: {len(selected)}")

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "chunks_used": selected,
            "config": {
                "retrieval_mode": retrieval_mode,
                "top_k_search": top_k_search,
                "top_k_select": top_k_select,
                "use_rerank": use_rerank,
                "query_transform": True,
                "query_transform_strategy": strategy,
            },
        }

    return _rag_answer


def run_one_experiment(
    run_id: int,
    phase: str,
    output_root: Path,
    *,
    chunk_strategy: str,
    chunk_size: int,
    chunk_overlap: int,
    retrieval_mode: str,
    hybrid_dense_weight: Optional[float] = None,
    hybrid_sparse_weight: Optional[float] = None,
    use_rerank: bool = False,
    query_transform: bool = False,
    query_transform_strategy: str = "expansion",
    top_k_search: int = 10,
    top_k_select: int = 3,
    rebuild_index: bool = False,
    progress_file: Optional[Path] = None,
) -> RunResult:
    label_parts = [
        phase,
        chunk_strategy,
        f"cs{chunk_size}",
        f"ov{chunk_overlap}",
        retrieval_mode,
    ]
    if retrieval_mode == "hybrid" and hybrid_dense_weight is not None and hybrid_sparse_weight is not None:
        label_parts.append(f"w{hybrid_dense_weight:.1f}_{hybrid_sparse_weight:.1f}")
    if use_rerank:
        label_parts.append("rerank")
    if query_transform:
        label_parts.append(f"qt_{query_transform_strategy}")

    label = "_".join(label_parts)
    run_dir = output_root / f"{run_id:03d}_{slugify(label)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    append_progress(progress_file, {
        "event": "run_started",
        "run_id": run_id,
        "phase": phase,
        "label": label,
        "run_dir": str(run_dir),
    })
    started_at = time.time()

    apply_chunking_config(chunk_strategy, chunk_size, chunk_overlap)
    apply_hybrid_weights(hybrid_dense_weight, hybrid_sparse_weight)
    eval_mod.rag_answer = make_rag_answer_with_query_transform(query_transform, query_transform_strategy)

    if rebuild_index:
        print(f"\n[run {run_id:03d}] Rebuilding index for {chunk_strategy}, size={chunk_size}, overlap={chunk_overlap}", flush=True)
        index_mod.build_index()

    eval_config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
        "label": label,
    }

    print(f"[run {run_id:03d}] Evaluating {label}", flush=True)

    try:
        rows = eval_mod.run_scorecard(config=eval_config, test_questions=None, verbose=False)
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        append_progress(progress_file, {
            "event": "run_failed",
            "run_id": run_id,
            "phase": phase,
            "label": label,
            "error": err_msg,
            "traceback": traceback.format_exc(),
        })
        raise

    averages = compute_averages(rows)
    objective = compute_objective(averages)

    summary_md = eval_mod.generate_scorecard_summary(rows, label)
    (run_dir / "scorecard.md").write_text(summary_md, encoding="utf-8")
    (run_dir / "rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    config_payload = {
        "run_id": run_id,
        "phase": phase,
        "label": label,
        "chunk_strategy": chunk_strategy,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "retrieval_mode": retrieval_mode,
        "hybrid_dense_weight": hybrid_dense_weight,
        "hybrid_sparse_weight": hybrid_sparse_weight,
        "use_rerank": use_rerank,
        "query_transform": query_transform,
        "query_transform_strategy": query_transform_strategy,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "rebuild_index": rebuild_index,
        "averages": averages,
        "objective": objective,
    }
    (run_dir / "config.json").write_text(json.dumps(config_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    elapsed = time.time() - started_at
    print(f"[run {run_id:03d}] DONE in {elapsed:.1f}s | objective={objective:.4f}", flush=True)
    append_progress(progress_file, {
        "event": "run_finished",
        "run_id": run_id,
        "phase": phase,
        "label": label,
        "elapsed_sec": round(elapsed, 2),
        "objective": objective,
        "averages": averages,
    })

    return RunResult(
        run_id=run_id,
        phase=phase,
        label=label,
        chunk_strategy=chunk_strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        retrieval_mode=retrieval_mode,
        hybrid_dense_weight=hybrid_dense_weight,
        hybrid_sparse_weight=hybrid_sparse_weight,
        use_rerank=use_rerank,
        query_transform=query_transform,
        query_transform_strategy=query_transform_strategy,
        averages=averages,
        objective=objective,
        run_dir=run_dir,
        scorecard_rows=rows,
    )


def write_master_summary(output_root: Path, runs: List[RunResult]) -> None:
    rows = []
    for r in runs:
        rows.append({
            "run_id": r.run_id,
            "phase": r.phase,
            "label": r.label,
            "chunk_strategy": r.chunk_strategy,
            "chunk_size": r.chunk_size,
            "chunk_overlap": r.chunk_overlap,
            "retrieval_mode": r.retrieval_mode,
            "hybrid_dense_weight": r.hybrid_dense_weight,
            "hybrid_sparse_weight": r.hybrid_sparse_weight,
            "use_rerank": r.use_rerank,
            "query_transform": r.query_transform,
            "query_transform_strategy": r.query_transform_strategy,
            "faithfulness": r.averages.get("faithfulness"),
            "relevance": r.averages.get("relevance"),
            "context_recall": r.averages.get("context_recall"),
            "completeness": r.averages.get("completeness"),
            "objective": r.objective,
            "run_dir": str(r.run_dir),
        })

    csv_path = output_root / "master_summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    best = max(runs, key=lambda x: x.objective)
    baseline = runs[0]

    report_lines = [
        "# Experiment Summary",
        "",
        f"Total runs: {len(runs)}",
        "",
        "## Best Run",
        f"- Run ID: {best.run_id}",
        f"- Label: {best.label}",
        f"- Objective: {best.objective:.4f}",
        f"- Location: {best.run_dir}",
        "",
        "## Baseline",
        f"- Run ID: {baseline.run_id}",
        f"- Label: {baseline.label}",
        f"- Objective: {baseline.objective:.4f}",
        "",
        "## Delta (Best - Baseline)",
    ]

    for metric in ["faithfulness", "relevance", "context_recall", "completeness"]:
        b = baseline.averages.get(metric)
        v = best.averages.get(metric)
        if b is None or v is None:
            report_lines.append(f"- {metric}: N/A")
        else:
            report_lines.append(f"- {metric}: {v - b:+.4f} (baseline={b:.4f}, best={v:.4f})")

    (output_root / "README.md").write_text("\n".join(report_lines), encoding="utf-8")

    # Print A/B table with eval helper.
    eval_mod.compare_ab(
        baseline.scorecard_rows,
        best.scorecard_rows,
        output_csv=None,
    )

    # Save A/B CSV in the experiment folder.
    ab_csv_path = output_root / "ab_comparison.csv"
    combined = baseline.scorecard_rows + best.scorecard_rows
    if combined:
        with open(ab_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(combined[0].keys()))
            writer.writeheader()
            writer.writerows(combined)


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = Path("results") / "experiments" / timestamp
    output_root.mkdir(parents=True, exist_ok=True)
    progress_file = output_root / "progress.jsonl"

    append_progress(progress_file, {
        "event": "experiment_started",
        "output_root": str(output_root),
    })

    print("=" * 80)
    print("Running full tuning experiment plan")
    print(f"Output directory: {output_root}")
    print(f"Progress file: {progress_file}")
    print("=" * 80)

    rebuild_index_env = os.getenv("REBUILD_INDEX", "0").strip().lower()
    rebuild_index_enabled = rebuild_index_env in {"1", "true", "yes", "y"}
    print(
        f"[init] Rebuild index: {'ON' if rebuild_index_enabled else 'OFF (using existing index)'}",
        flush=True,
    )
    append_progress(progress_file, {
        "event": "rebuild_policy",
        "enabled": rebuild_index_enabled,
    })

    print("[init] Importing eval/index/rag modules...", flush=True)
    append_progress(progress_file, {"event": "import_started"})
    load_lab_modules()
    print("[init] Imports done.", flush=True)
    append_progress(progress_file, {"event": "import_finished"})

    runs: List[RunResult] = []
    run_id = 1

    try:
        # ---------------------------------------------------------------------
        # Baseline
        # ---------------------------------------------------------------------
        baseline = run_one_experiment(
            run_id,
            phase="baseline",
            output_root=output_root,
            chunk_strategy="paragraph_recursive",
            chunk_size=500,
            chunk_overlap=80,
            retrieval_mode="dense",
            use_rerank=False,
            query_transform=False,
            rebuild_index=rebuild_index_enabled,
            progress_file=progress_file,
        )
        runs.append(baseline)
        run_id += 1

        # ---------------------------------------------------------------------
        # Phase 1 - chunking
        # ---------------------------------------------------------------------
        if rebuild_index_enabled:
            stage1_runs: List[RunResult] = []
            for strategy in CHUNK_STRATEGIES.keys():
                for chunk_size in CHUNK_SIZES:
                    rr = run_one_experiment(
                        run_id,
                        phase="phase1_stage1",
                        output_root=output_root,
                        chunk_strategy=strategy,
                        chunk_size=chunk_size,
                        chunk_overlap=PHASE1_FIXED_OVERLAP,
                        retrieval_mode="dense",
                        use_rerank=False,
                        query_transform=False,
                        rebuild_index=True,
                        progress_file=progress_file,
                    )
                    runs.append(rr)
                    stage1_runs.append(rr)
                    run_id += 1

            top2_seed = sorted(stage1_runs, key=lambda r: r.objective, reverse=True)[:2]

            stage2_runs: List[RunResult] = []
            for seed in top2_seed:
                for overlap in CHUNK_OVERLAPS:
                    rr = run_one_experiment(
                        run_id,
                        phase="phase1_stage2",
                        output_root=output_root,
                        chunk_strategy=seed.chunk_strategy,
                        chunk_size=seed.chunk_size,
                        chunk_overlap=overlap,
                        retrieval_mode="dense",
                        use_rerank=False,
                        query_transform=False,
                        rebuild_index=True,
                        progress_file=progress_file,
                    )
                    runs.append(rr)
                    stage2_runs.append(rr)
                    run_id += 1

            phase1_best = max(stage1_runs + stage2_runs, key=lambda r: r.objective)
            print(
                f"\n[phase1] Best chunking: {phase1_best.chunk_strategy}, "
                f"size={phase1_best.chunk_size}, overlap={phase1_best.chunk_overlap}, "
                f"objective={phase1_best.objective:.4f}"
            )
        else:
            phase1_best = baseline
            print("\n[phase1] Skipped (REBUILD_INDEX=0). Using existing indexed chunks.", flush=True)
            append_progress(progress_file, {
                "event": "phase1_skipped",
                "reason": "rebuild_disabled",
            })

        # ---------------------------------------------------------------------
        # Phase 2 - retrieval
        # ---------------------------------------------------------------------
        phase2_runs: List[RunResult] = []
        indexed_once = False
        for variant in RETRIEVAL_VARIANTS:
            rr = run_one_experiment(
                run_id,
                phase="phase2_retrieval",
                output_root=output_root,
                chunk_strategy=phase1_best.chunk_strategy,
                chunk_size=phase1_best.chunk_size,
                chunk_overlap=phase1_best.chunk_overlap,
                retrieval_mode=variant["retrieval_mode"],
                hybrid_dense_weight=variant.get("hybrid_dense_weight"),
                hybrid_sparse_weight=variant.get("hybrid_sparse_weight"),
                use_rerank=False,
                query_transform=False,
                rebuild_index=(rebuild_index_enabled and not indexed_once),
                progress_file=progress_file,
            )
            runs.append(rr)
            phase2_runs.append(rr)
            indexed_once = True
            run_id += 1

        phase2_best = max(phase2_runs, key=lambda r: r.objective)
        print(
            f"\n[phase2] Best retrieval: {phase2_best.retrieval_mode}, "
            f"objective={phase2_best.objective:.4f}"
        )

        # ---------------------------------------------------------------------
        # Phase 3 - technical improvements
        # ---------------------------------------------------------------------
        tech_a = run_one_experiment(
            run_id,
            phase="phase3_tech",
            output_root=output_root,
            chunk_strategy=phase1_best.chunk_strategy,
            chunk_size=phase1_best.chunk_size,
            chunk_overlap=phase1_best.chunk_overlap,
            retrieval_mode=phase2_best.retrieval_mode,
            hybrid_dense_weight=phase2_best.hybrid_dense_weight,
            hybrid_sparse_weight=phase2_best.hybrid_sparse_weight,
            use_rerank=True,
            query_transform=False,
            rebuild_index=False,
            progress_file=progress_file,
        )
        runs.append(tech_a)
        run_id += 1

        tech_b = run_one_experiment(
            run_id,
            phase="phase3_tech",
            output_root=output_root,
            chunk_strategy=phase1_best.chunk_strategy,
            chunk_size=phase1_best.chunk_size,
            chunk_overlap=phase1_best.chunk_overlap,
            retrieval_mode=phase2_best.retrieval_mode,
            hybrid_dense_weight=phase2_best.hybrid_dense_weight,
            hybrid_sparse_weight=phase2_best.hybrid_sparse_weight,
            use_rerank=False,
            query_transform=True,
            query_transform_strategy="expansion",
            rebuild_index=False,
            progress_file=progress_file,
        )
        runs.append(tech_b)
        run_id += 1

        if max(tech_a.objective, tech_b.objective) > phase2_best.objective:
            tech_c = run_one_experiment(
                run_id,
                phase="phase3_tech",
                output_root=output_root,
                chunk_strategy=phase1_best.chunk_strategy,
                chunk_size=phase1_best.chunk_size,
                chunk_overlap=phase1_best.chunk_overlap,
                retrieval_mode=phase2_best.retrieval_mode,
                hybrid_dense_weight=phase2_best.hybrid_dense_weight,
                hybrid_sparse_weight=phase2_best.hybrid_sparse_weight,
                use_rerank=True,
                query_transform=True,
                query_transform_strategy="expansion",
                rebuild_index=False,
                progress_file=progress_file,
            )
            runs.append(tech_c)
            run_id += 1

        write_master_summary(output_root, runs)

        best = max(runs, key=lambda r: r.objective)
        print("\n" + "=" * 80)
        print("Finished experiments")
        print(f"Best run: {best.label}")
        print(f"Best objective: {best.objective:.4f}")
        print(f"Artifacts: {output_root}")
        print("=" * 80)

        append_progress(progress_file, {
            "event": "experiment_finished",
            "best_label": best.label,
            "best_objective": best.objective,
        })

    except Exception as e:
        crash = {
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }
        (output_root / "crash_report.json").write_text(
            json.dumps(crash, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        append_progress(progress_file, {
            "event": "experiment_failed",
            "error": crash["error"],
        })
        print("\nExperiment failed. See crash report:", output_root / "crash_report.json", flush=True)
        raise

    finally:
        # Restore module state to avoid side effects in interactive sessions.
        if index_mod is not None and ORIGINAL_CHUNK_DOCUMENT is not None:
            index_mod.chunk_document = ORIGINAL_CHUNK_DOCUMENT
        if rag_mod is not None and ORIGINAL_RETRIEVE_HYBRID is not None:
            rag_mod.retrieve_hybrid = ORIGINAL_RETRIEVE_HYBRID
        if eval_mod is not None and ORIGINAL_EVAL_RAG_ANSWER is not None:
            eval_mod.rag_answer = ORIGINAL_EVAL_RAG_ANSWER


if __name__ == "__main__":
    main()
