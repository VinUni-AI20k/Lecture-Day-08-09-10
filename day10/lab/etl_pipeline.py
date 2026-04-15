#!/usr/bin/env python3
"""
Lab Day 10 — ETL entrypoint: ingest → clean → validate → embed.

Tiếp nối Day 09: cùng corpus docs trong data/docs/; pipeline này xử lý *export* raw (CSV)
đại diện cho lớp ingestion từ DB/API trước khi embed lại vector store.

Chạy nhanh:
  pip install -r requirements.txt
  cp .env.example .env
  python etl_pipeline.py run

Chế độ inject (Sprint 3 — bỏ fix refund để expectation fail / eval xấu):
  python etl_pipeline.py run --no-refund-fix --skip-validate
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from monitoring.freshness_check import check_manifest_freshness
from quality.expectations import run_expectations
from transform.cleaning_rules import clean_rows, load_raw_csv, write_cleaned_csv, write_quarantine_csv

load_dotenv()

ROOT = Path(__file__).resolve().parent
RAW_DEFAULT = ROOT / "data" / "raw" / "policy_export_dirty.csv"
ART = ROOT / "artifacts"
LOG_DIR = ART / "logs"
MAN_DIR = ART / "manifests"
QUAR_DIR = ART / "quarantine"
CLEAN_DIR = ART / "cleaned"
TASK_OWNER_MAP = ROOT / "contracts" / "task_owner_map.json"


def _log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _load_owner_map(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def cmd_run(args: argparse.Namespace) -> int:
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%MZ")
    raw_path = Path(args.raw)
    if not raw_path.is_file():
        print(f"ERROR: raw file not found: {raw_path}", file=sys.stderr)
        return 1

    log_path = LOG_DIR / f"run_{run_id.replace(':', '-')}.log"
    for p in (LOG_DIR, MAN_DIR, QUAR_DIR, CLEAN_DIR):
        p.mkdir(parents=True, exist_ok=True)

    owner_map = _load_owner_map(TASK_OWNER_MAP)

    def resolve_owner(task_id: str) -> str:
        rec = owner_map.get(task_id, {})
        return str(rec.get("owner") or "UNASSIGNED")

    def log(msg: str, *, task_id: str = "D10-T00", level: str = "INFO", event: str = "") -> None:
        print(msg)
        _log(log_path, msg)
        payload: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "task_id": task_id,
            "owner": resolve_owner(task_id),
            "event": event or "pipeline_event",
            "message": msg,
        }
        _log(log_path, f"event_json={json.dumps(payload, ensure_ascii=False)}")

    rows = load_raw_csv(raw_path)
    raw_count = len(rows)
    log(f"run_id={run_id}", task_id="D10-T00", event="run_start")
    log(f"raw_records={raw_count}", task_id="D10-T01", event="ingest_raw_count")

    cleaned, quarantine = clean_rows(
        rows,
        apply_refund_window_fix=not args.no_refund_fix,
    )
    cleaned_path = CLEAN_DIR / f"cleaned_{run_id.replace(':', '-')}.csv"
    quar_path = QUAR_DIR / f"quarantine_{run_id.replace(':', '-')}.csv"
    write_cleaned_csv(cleaned_path, cleaned)
    write_quarantine_csv(quar_path, quarantine)

    log(f"cleaned_records={len(cleaned)}", task_id="D10-T02", event="cleaned_count")
    log(f"quarantine_records={len(quarantine)}", task_id="D10-T02", event="quarantine_count")
    log(f"cleaned_csv={cleaned_path.relative_to(ROOT)}", task_id="D10-T02", event="cleaned_path")
    log(f"quarantine_csv={quar_path.relative_to(ROOT)}", task_id="D10-T02", event="quarantine_path")

    results, halt = run_expectations(cleaned)
    for r in results:
        sym = "OK" if r.passed else "FAIL"
        level = "INFO" if r.passed else ("ERROR" if r.severity.lower() == "halt" else "WARN")
        log(
            f"expectation[{r.name}] {sym} ({r.severity}) :: {r.detail}",
            task_id="D10-T03",
            level=level,
            event="expectation_result",
        )
    if halt and not args.skip_validate:
        log(
            "PIPELINE_HALT: expectation suite failed (halt).",
            task_id="D10-T03",
            level="ERROR",
            event="expectation_halt",
        )
        return 2
    if halt and args.skip_validate:
        log(
            "WARN: expectation failed but --skip-validate → tiếp tục embed (chỉ dùng cho demo Sprint 3).",
            task_id="D10-T03",
            level="WARN",
            event="expectation_skip_validate",
        )

    # Embed
    embed_ok = cmd_embed_internal(
        cleaned_path,
        run_id=run_id,
        log=log,
    )
    if not embed_ok:
        log(
            "PIPELINE_ERROR: embed stage failed.",
            task_id="D10-T05",
            level="ERROR",
            event="embed_failed",
        )
        return 3

    latest_exported = ""
    if cleaned:
        latest_exported = max((r.get("exported_at") or "" for r in cleaned), default="")

    manifest = {
        "run_id": run_id,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_path": str(raw_path.relative_to(ROOT)),
        "raw_records": raw_count,
        "cleaned_records": len(cleaned),
        "quarantine_records": len(quarantine),
        "latest_exported_at": latest_exported,
        "no_refund_fix": bool(args.no_refund_fix),
        "skipped_validate": bool(args.skip_validate and halt),
        "cleaned_csv": str(cleaned_path.relative_to(ROOT)),
        "chroma_path": os.environ.get("CHROMA_DB_PATH", "./chroma_db"),
        "chroma_collection": os.environ.get("CHROMA_COLLECTION", "day10_kb"),
    }
    man_path = MAN_DIR / f"manifest_{run_id.replace(':', '-')}.json"
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"manifest_written={man_path.relative_to(ROOT)}", task_id="D10-T05", event="manifest_written")

    status, fdetail = check_manifest_freshness(man_path, sla_hours=float(os.environ.get("FRESHNESS_SLA_HOURS", "24")))
    f_level = "INFO" if status == "PASS" else ("WARN" if status == "WARN" else "ERROR")
    log(
        f"freshness_check={status} {json.dumps(fdetail, ensure_ascii=False)}",
        task_id="D10-T05",
        level=f_level,
        event="freshness_check",
    )

    log("PIPELINE_OK", task_id="D10-T00", event="run_completed")
    return 0


def cmd_embed_internal(cleaned_csv: Path, *, run_id: str, log) -> bool:
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        log(
            "ERROR: chromadb chưa cài. pip install -r requirements.txt",
            task_id="D10-T05",
            level="ERROR",
            event="embed_import_error",
        )
        return False

    db_path = os.environ.get("CHROMA_DB_PATH", str(ROOT / "chroma_db"))
    collection_name = os.environ.get("CHROMA_COLLECTION", "day10_kb")
    model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    from transform.cleaning_rules import load_raw_csv as load_csv  # same loader

    rows = load_csv(cleaned_csv)
    if not rows:
        log(
            "WARN: cleaned CSV rỗng — không embed.",
            task_id="D10-T05",
            level="WARN",
            event="embed_empty_cleaned_csv",
        )
        return True

    client = chromadb.PersistentClient(path=db_path)
    emb = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
    col = client.get_or_create_collection(name=collection_name, embedding_function=emb)

    ids = [r["chunk_id"] for r in rows]
    # Tránh “mồi cũ” trong top-k: xóa id không còn trong cleaned run này (index = snapshot publish).
    try:
        prev = col.get(include=[])
        prev_ids = set(prev.get("ids") or [])
        drop = sorted(prev_ids - set(ids))
        if drop:
            col.delete(ids=drop)
            log(
                f"embed_prune_removed={len(drop)}",
                task_id="D10-T05",
                event="embed_prune_removed",
            )
    except Exception as e:
        log(
            f"WARN: embed prune skip: {e}",
            task_id="D10-T05",
            level="WARN",
            event="embed_prune_skipped",
        )
    documents = [r["chunk_text"] for r in rows]
    metadatas = [
        {
            "doc_id": r.get("doc_id", ""),
            "effective_date": r.get("effective_date", ""),
            "run_id": run_id,
        }
        for r in rows
    ]
    # Idempotent: upsert theo chunk_id
    col.upsert(ids=ids, documents=documents, metadatas=metadatas)
    log(
        f"embed_upsert count={len(ids)} collection={collection_name}",
        task_id="D10-T05",
        event="embed_upsert",
    )
    return True


def cmd_freshness(args: argparse.Namespace) -> int:
    p = Path(args.manifest)
    if not p.is_file():
        print(f"manifest not found: {p}", file=sys.stderr)
        return 1
    sla = float(os.environ.get("FRESHNESS_SLA_HOURS", "24"))
    status, detail = check_manifest_freshness(p, sla_hours=sla)
    print(status, json.dumps(detail, ensure_ascii=False))
    return 0 if status != "FAIL" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Day 10 ETL pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="ingest → clean → validate → embed")
    p_run.add_argument("--raw", default=str(RAW_DEFAULT), help="Đường dẫn CSV raw export")
    p_run.add_argument("--run-id", default="", help="ID run (mặc định: UTC timestamp)")
    p_run.add_argument(
        "--no-refund-fix",
        action="store_true",
        help="Không áp dụng rule fix cửa sổ 14→7 ngày (dùng cho inject corruption / before).",
    )
    p_run.add_argument(
        "--skip-validate",
        action="store_true",
        help="Vẫn embed khi expectation halt (chỉ phục vụ demo có chủ đích).",
    )
    p_run.set_defaults(func=cmd_run)

    p_fr = sub.add_parser("freshness", help="Đọc manifest và kiểm tra SLA freshness")
    p_fr.add_argument("--manifest", required=True)
    p_fr.set_defaults(func=cmd_freshness)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
