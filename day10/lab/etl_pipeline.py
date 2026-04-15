#!/usr/bin/env python3
"""
Day 10 ETL entrypoint: ingest -> clean -> validate -> embed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

from embedding_provider import build_embedding_function
from monitoring.freshness_check import check_manifest_freshness
from quality.expectations import run_expectations
from transform.cleaning_rules import clean_rows, load_raw_csv, write_cleaned_csv, write_quarantine_csv

load_dotenv()

ROOT = Path(__file__).resolve().parent
RAW_DEFAULT = ROOT / "data" / "raw" / "policy_export_dirty.csv"
CONTRACT_DEFAULT = ROOT / "contracts" / "data_contract.yaml"
ART = ROOT / "artifacts"
LOG_DIR = ART / "logs"
MAN_DIR = ART / "manifests"
QUAR_DIR = ART / "quarantine"
CLEAN_DIR = ART / "cleaned"


def _safe_relpath(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def _log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


def _load_contract(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _parse_doc_keywords(contract_data: Dict[str, Any]) -> Dict[str, tuple[str, ...]]:
    config = contract_data.get("doc_topic_keywords")
    if not isinstance(config, dict):
        return {}
    parsed: Dict[str, tuple[str, ...]] = {}
    for doc_id, values in config.items():
        if not isinstance(values, list):
            continue
        normalized = tuple(str(item).strip().lower() for item in values if str(item).strip())
        if normalized:
            parsed[str(doc_id).strip()] = normalized
    return parsed


def cmd_run(args: argparse.Namespace) -> int:
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%MZ")
    raw_path = Path(args.raw).resolve()
    contract_path = Path(args.contract).resolve()
    if not raw_path.is_file():
        print(f"ERROR: raw file not found: {raw_path}", file=sys.stderr)
        return 1

    contract_data = _load_contract(contract_path)
    hr_cutoff = str(
        os.environ.get("HR_LEAVE_MIN_EFFECTIVE_DATE")
        or (contract_data.get("policy_versioning") or {}).get("hr_leave_min_effective_date")
        or "2026-01-01"
    )
    refund_window_days = int(
        os.environ.get("REFUND_WINDOW_DAYS")
        or (contract_data.get("policy_versioning") or {}).get("refund_window_days")
        or 7
    )
    doc_keywords = _parse_doc_keywords(contract_data)

    log_path = LOG_DIR / f"run_{run_id.replace(':', '-')}.log"
    for folder in (LOG_DIR, MAN_DIR, QUAR_DIR, CLEAN_DIR):
        folder.mkdir(parents=True, exist_ok=True)

    def log(message: str) -> None:
        print(message)
        _log(log_path, message)

    rows = load_raw_csv(raw_path)
    raw_count = len(rows)
    latest_raw_exported_at = max((row.get("exported_at") or "" for row in rows), default="")

    log(f"run_id={run_id}")
    log(f"raw_records={raw_count}")
    log(f"config.hr_leave_min_effective_date={hr_cutoff}")
    log(f"config.refund_window_days={refund_window_days}")

    cleaned, quarantine = clean_rows(
        rows,
        apply_refund_window_fix=not args.no_refund_fix,
        refund_window_days=refund_window_days,
        hr_leave_min_effective_date=hr_cutoff,
        doc_keywords=doc_keywords,
    )
    cleaned_path = CLEAN_DIR / f"cleaned_{run_id.replace(':', '-')}.csv"
    quarantine_path = QUAR_DIR / f"quarantine_{run_id.replace(':', '-')}.csv"
    write_cleaned_csv(cleaned_path, cleaned)
    write_quarantine_csv(quarantine_path, quarantine)

    log(f"cleaned_records={len(cleaned)}")
    log(f"quarantine_records={len(quarantine)}")
    log(f"cleaned_csv={cleaned_path.relative_to(ROOT)}")
    log(f"quarantine_csv={quarantine_path.relative_to(ROOT)}")

    results, halt = run_expectations(cleaned)
    for result in results:
        symbol = "OK" if result.passed else "FAIL"
        log(f"expectation[{result.name}] {symbol} ({result.severity}) :: {result.detail}")
    if halt and not args.skip_validate:
        log("PIPELINE_HALT: expectation suite failed (halt).")
        return 2
    if halt and args.skip_validate:
        log("WARN: expectation failed but --skip-validate enabled; continue for inject demo.")

    embed_ok = cmd_embed_internal(cleaned_path, run_id=run_id, log=log)
    if not embed_ok:
        return 3

    latest_cleaned_exported_at = max((row.get("exported_at") or "" for row in cleaned), default="")
    manifest = {
        "run_id": run_id,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_path": _safe_relpath(raw_path),
        "contract_path": _safe_relpath(contract_path),
        "raw_records": raw_count,
        "cleaned_records": len(cleaned),
        "quarantine_records": len(quarantine),
        "latest_raw_exported_at": latest_raw_exported_at,
        "latest_exported_at": latest_cleaned_exported_at,
        "latest_cleaned_exported_at": latest_cleaned_exported_at,
        "hr_leave_min_effective_date": hr_cutoff,
        "refund_window_days": refund_window_days,
        "no_refund_fix": bool(args.no_refund_fix),
        "skipped_validate": bool(args.skip_validate and halt),
        "cleaned_csv": str(cleaned_path.relative_to(ROOT)),
        "chroma_path": os.environ.get("CHROMA_DB_PATH", "./chroma_db"),
        "chroma_collection": os.environ.get("CHROMA_COLLECTION", "day10_kb"),
        "embedding_provider": (os.environ.get("OPENAI_EMBEDDING_MODEL") or "").strip()
        or os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
    }

    manifest_path = MAN_DIR / f"manifest_{run_id.replace(':', '-')}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"manifest_written={manifest_path.relative_to(ROOT)}")

    publish_status, publish_detail = check_manifest_freshness(
        manifest_path,
        sla_hours=float(os.environ.get("FRESHNESS_SLA_HOURS", "24")),
        timestamp_field="latest_cleaned_exported_at",
    )
    log(f"freshness_publish={publish_status} {json.dumps(publish_detail, ensure_ascii=False)}")

    ingest_status, ingest_detail = check_manifest_freshness(
        manifest_path,
        sla_hours=float(os.environ.get("INGEST_FRESHNESS_SLA_HOURS", os.environ.get("FRESHNESS_SLA_HOURS", "24"))),
        timestamp_field="latest_raw_exported_at",
    )
    log(f"freshness_ingest={ingest_status} {json.dumps(ingest_detail, ensure_ascii=False)}")

    log("PIPELINE_OK")
    return 0


def cmd_embed_internal(cleaned_csv: Path, *, run_id: str, log) -> bool:
    try:
        import chromadb
    except ImportError:
        log("ERROR: chromadb not installed. Run: pip install -r requirements.txt")
        return False

    db_path = os.environ.get("CHROMA_DB_PATH", str(ROOT / "chroma_db"))
    collection_name = os.environ.get("CHROMA_COLLECTION", "day10_kb")

    rows = load_raw_csv(cleaned_csv)
    if not rows:
        log("WARN: cleaned CSV empty, skip embed.")
        return True

    client = chromadb.PersistentClient(path=db_path)
    try:
        emb, provider_name = build_embedding_function()
    except Exception as exc:
        log(f"ERROR: cannot initialize embedding provider: {exc}")
        return False
    log(f"embedding_provider={provider_name}")
    collection = client.get_or_create_collection(name=collection_name, embedding_function=emb)

    ids = [row["chunk_id"] for row in rows]
    try:
        previous = collection.get(include=["metadatas"], limit=100000)
        previous_ids = set(previous.get("ids") or [])
        drop_ids = sorted(previous_ids - set(ids))
        if drop_ids:
            collection.delete(ids=drop_ids)
            log(f"embed_prune_removed={len(drop_ids)}")
    except Exception as exc:
        log(f"WARN: embed prune skipped: {exc}")

    documents = [row["chunk_text"] for row in rows]
    metadatas = [
        {
            "doc_id": row.get("doc_id", ""),
            "effective_date": row.get("effective_date", ""),
            "run_id": run_id,
        }
        for row in rows
    ]
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    log(f"embed_upsert count={len(ids)} collection={collection_name}")
    return True


def cmd_freshness(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(f"manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    default_field = "latest_cleaned_exported_at"
    if args.boundary == "ingest":
        field_name = "latest_raw_exported_at"
    elif args.boundary == "publish":
        field_name = "latest_cleaned_exported_at"
    else:
        field_name = default_field

    sla = float(os.environ.get("FRESHNESS_SLA_HOURS", "24"))
    status, detail = check_manifest_freshness(
        manifest_path,
        sla_hours=sla,
        timestamp_field=field_name,
    )
    print(status, json.dumps(detail, ensure_ascii=False))
    return 0 if status != "FAIL" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Day 10 ETL pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="ingest -> clean -> validate -> embed")
    run_parser.add_argument("--raw", default=str(RAW_DEFAULT), help="Path to raw CSV export")
    run_parser.add_argument("--contract", default=str(CONTRACT_DEFAULT), help="Path to data contract YAML")
    run_parser.add_argument("--run-id", default="", help="Run ID (default: UTC timestamp)")
    run_parser.add_argument(
        "--no-refund-fix",
        action="store_true",
        help="Disable refund 14->configured-days fix for inject scenario.",
    )
    run_parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Continue embedding even if halt expectations fail (inject demo only).",
    )
    run_parser.set_defaults(func=cmd_run)

    fresh_parser = sub.add_parser("freshness", help="Read manifest and check freshness SLA")
    fresh_parser.add_argument("--manifest", required=True)
    fresh_parser.add_argument(
        "--boundary",
        choices=["ingest", "publish", "auto"],
        default="publish",
        help="Which freshness boundary to evaluate.",
    )
    fresh_parser.set_defaults(func=cmd_freshness)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
