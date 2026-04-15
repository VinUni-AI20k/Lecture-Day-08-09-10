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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict

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


def _log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _resolve_cli_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if path.is_absolute():
        return path
    return (ROOT / path).resolve()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _slugify_run_id(run_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", run_id)


def _write_manifest(path: Path, manifest: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_run(args: argparse.Namespace) -> int:
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%MZ")
    run_token = _slugify_run_id(run_id)
    raw_path = _resolve_cli_path(args.raw)
    if not raw_path.is_file():
        print(f"ERROR: raw file not found: {raw_path}", file=sys.stderr)
        return 1

    if args.skip_validate and not args.no_refund_fix:
        print(
            "ERROR: --skip-validate chỉ dành cho demo inject; hiện tại hãy dùng kèm --no-refund-fix.",
            file=sys.stderr,
        )
        return 1

    log_path = LOG_DIR / f"run_{run_token}.log"
    man_path = MAN_DIR / f"manifest_{run_token}.json"
    for p in (LOG_DIR, MAN_DIR, QUAR_DIR, CLEAN_DIR):
        p.mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        print(msg)
        _log(log_path, msg)

    rows = load_raw_csv(raw_path)
    raw_count = len(rows)
    log(f"run_id={run_id}")
    log(f"raw_records={raw_count}")

    cleaned, quarantine = clean_rows(
        rows,
        apply_refund_window_fix=not args.no_refund_fix,
    )
    cleaned_path = CLEAN_DIR / f"cleaned_{run_token}.csv"
    quar_path = QUAR_DIR / f"quarantine_{run_token}.csv"
    write_cleaned_csv(cleaned_path, cleaned)
    write_quarantine_csv(quar_path, quarantine)

    log(f"cleaned_records={len(cleaned)}")
    log(f"quarantine_records={len(quarantine)}")
    log(f"cleaned_csv={_display_path(cleaned_path)}")
    log(f"quarantine_csv={_display_path(quar_path)}")

    results, halt = run_expectations(cleaned)
    halt_failures = 0
    warn_failures = 0
    for r in results:
        sym = "OK" if r.passed else "FAIL"
        log(f"expectation[{r.name}] {sym} ({r.severity}) :: {r.detail}")
        if not r.passed and r.severity == "halt":
            halt_failures += 1
        if not r.passed and r.severity == "warn":
            warn_failures += 1

    latest_exported = ""
    if cleaned:
        latest_exported = max((r.get("exported_at") or "" for r in cleaned), default="")

    manifest: Dict[str, Any] = {
        "run_id": run_id,
        "run_token": run_token,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "command": "python etl_pipeline.py run",
        "raw_path": _display_path(raw_path),
        "raw_records": raw_count,
        "cleaned_records": len(cleaned),
        "quarantine_records": len(quarantine),
        "latest_exported_at": latest_exported,
        "no_refund_fix": bool(args.no_refund_fix),
        "skip_validate": bool(args.skip_validate),
        "skipped_validate": bool(args.skip_validate and halt),
        "artifacts": {
            "log_path": _display_path(log_path),
            "cleaned_csv": _display_path(cleaned_path),
            "quarantine_csv": _display_path(quar_path),
            "manifest_path": _display_path(man_path),
        },
        "validation": {
            "halt": halt,
            "halt_failures": halt_failures,
            "warn_failures": warn_failures,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "severity": r.severity,
                    "detail": r.detail,
                }
                for r in results
            ],
        },
        "embed": {
            "attempted": False,
            "status": "not_started",
            "collection": os.environ.get("CHROMA_COLLECTION", "day10_kb"),
            "db_path": os.environ.get("CHROMA_DB_PATH", str(ROOT / "chroma_db")),
        },
        "freshness": {
            "status": "not_run",
            "detail": {},
            "sla_hours": float(os.environ.get("FRESHNESS_SLA_HOURS", "24")),
        },
        "pipeline_status": "running",
        "exit_code": None,
        "cleaned_csv": _display_path(cleaned_path),
        "quarantine_csv": _display_path(quar_path),
        "log_path": _display_path(log_path),
        "chroma_path": os.environ.get("CHROMA_DB_PATH", str(ROOT / "chroma_db")),
        "chroma_collection": os.environ.get("CHROMA_COLLECTION", "day10_kb"),
    }

    exit_code = 0
    if halt and not args.skip_validate:
        manifest["pipeline_status"] = "halted_validation"
        manifest["exit_code"] = 2
        manifest["embed"]["status"] = "skipped_validation_halt"
        log("PIPELINE_HALT: expectation suite failed (halt).")
        exit_code = 2
    else:
        if halt and args.skip_validate:
            log("WARN: expectation failed but --skip-validate → tiếp tục embed (chỉ dùng cho demo Sprint 3).")
        manifest["embed"]["attempted"] = True
        embed_ok = cmd_embed_internal(
            cleaned_path,
            run_id=run_id,
            log=log,
        )
        if not embed_ok:
            manifest["pipeline_status"] = "embed_failed"
            manifest["exit_code"] = 3
            manifest["embed"]["status"] = "failed"
            exit_code = 3
        else:
            manifest["pipeline_status"] = "ok"
            manifest["exit_code"] = 0
            manifest["embed"]["status"] = "completed"

    _write_manifest(man_path, manifest)
    log(f"manifest_written={_display_path(man_path)}")

    status, fdetail = check_manifest_freshness(
        man_path,
        sla_hours=float(manifest["freshness"]["sla_hours"]),
    )
    manifest["freshness"]["status"] = status
    manifest["freshness"]["detail"] = fdetail
    _write_manifest(man_path, manifest)
    log(f"freshness_check={status} {json.dumps(fdetail, ensure_ascii=False)}")

    if exit_code == 0:
        log("PIPELINE_OK")
    return exit_code


def cmd_embed_internal(cleaned_csv: Path, *, run_id: str, log: Callable[[str], None]) -> bool:
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        log("ERROR: chromadb chưa cài. pip install -r requirements.txt")
        return False

    try:
        db_path = os.environ.get("CHROMA_DB_PATH", str(ROOT / "chroma_db"))
        collection_name = os.environ.get("CHROMA_COLLECTION", "day10_kb")
        model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

        from transform.cleaning_rules import load_raw_csv as load_csv  # same loader

        rows = load_csv(cleaned_csv)
        if not rows:
            log("WARN: cleaned CSV rỗng — không embed.")
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
                log(f"embed_prune_removed={len(drop)}")
        except Exception as e:
            log(f"WARN: embed prune skip: {e}")
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
        log(f"embed_upsert count={len(ids)} collection={collection_name}")
        return True
    except Exception as e:
        log(f"ERROR: embed failed: {e}")
        return False


def cmd_freshness(args: argparse.Namespace) -> int:
    p = _resolve_cli_path(args.manifest)
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
