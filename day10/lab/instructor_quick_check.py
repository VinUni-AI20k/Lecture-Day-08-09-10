#!/usr/bin/env python3
"""
Kiểm tra nhanh artifact lab (không thay thế chấm tay).

Ví dụ:
  python instructor_quick_check.py
  python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl

Kiểm tra:
  - grading_run.jsonl: mỗi dòng JSON hợp lệ, đủ khóa, câu chấm chuẩn (gq_d10_01..03)
  - (tuỳ chọn) --manifest: manifest có run_id, đếm record, cleaned path
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"line {i}: invalid json: {e}") from e
    return lines


def check_grading_jsonl(path: Path) -> Tuple[int, List[str]]:
    msgs: List[str] = []
    if not path.is_file():
        return 1, [f"MISSING: {path}"]

    rows = _load_jsonl(path)
    if len(rows) < 3:
        msgs.append(f"WARN: expected >=3 grading rows, got {len(rows)}")

    required_ids = {"gq_d10_01", "gq_d10_02", "gq_d10_03"}
    seen = {r.get("id") for r in rows if r.get("id")}
    missing = required_ids - seen
    if missing:
        msgs.append(f"FAIL: missing grading ids: {sorted(missing)}")

    by_id = {r.get("id"): r for r in rows if r.get("id")}

    for r in rows:
        gid = r.get("id")
        for k in ("contains_expected", "hits_forbidden"):
            if k not in r:
                msgs.append(f"FAIL: {gid} missing key {k}")
        if r.get("hits_forbidden") is True:
            msgs.append(f"NOTE: {gid} hits_forbidden=true (có thể inject / index bẩn / chưa prune)")
        want = r.get("top1_doc_matches")
        if want is not None and r.get("id") == "gq_d10_03" and want is not True:
            msgs.append(f"WARN: gq_d10_03 top1_doc_matches expected true, got {want!r}")

    def _merit_line(gid: str, label: str) -> None:
        row = by_id.get(gid)
        if not row:
            return
        ok = bool(row.get("contains_expected")) and not bool(row.get("hits_forbidden"))
        if gid == "gq_d10_03":
            ok = ok and row.get("top1_doc_matches") is True
        sym = "OK" if ok else "FAIL"
        msgs.append(f"MERIT_CHECK[{gid}] {sym} :: {label}")

    _merit_line("gq_d10_01", "refund window + không forbidden trong top-k")
    _merit_line("gq_d10_02", "P1 resolution SLA")
    _merit_line("gq_d10_03", "HR 12 ngày + top1 doc_id + không 10 ngày stale trong top-k")

    merit_fail = any("MERIT_CHECK[" in m and "] FAIL ::" in m for m in msgs)
    fails = [m for m in msgs if m.startswith("FAIL:")]
    return (1 if fails or merit_fail else 0), msgs


def check_manifest(path: Path) -> Tuple[int, List[str]]:
    msgs: List[str] = []
    if not path.is_file():
        return 1, [f"MISSING manifest: {path}"]
    data = json.loads(path.read_text(encoding="utf-8"))
    for k in ("run_id", "raw_records", "cleaned_records", "quarantine_records"):
        if k not in data:
            msgs.append(f"FAIL: manifest missing {k}")
    if msgs:
        return 1, msgs
    msgs.append(
        f"OK manifest run_id={data.get('run_id')} "
        f"raw={data.get('raw_records')} clean={data.get('cleaned_records')} "
        f"quar={data.get('quarantine_records')}"
    )
    return 0, msgs


def main() -> int:
    p = argparse.ArgumentParser(description="Day 10 lab — quick artifact checks for instructors")
    root = Path(__file__).resolve().parent
    p.add_argument(
        "--grading",
        default=str(root / "artifacts" / "eval" / "grading_run.jsonl"),
        help="Đường dẫn grading_run.jsonl",
    )
    p.add_argument("--manifest", default="", help="Tuỳ chọn: manifest.json để sanity check")
    args = p.parse_args()

    code, msgs = check_grading_jsonl(Path(args.grading))
    for m in msgs:
        print(m)

    if args.manifest:
        c2, m2 = check_manifest(Path(args.manifest))
        code = max(code, c2)
        for m in m2:
            print(m)

    return code


if __name__ == "__main__":
    raise SystemExit(main())
