"""
Simple expectation suite for cleaned data.

This file keeps baseline checks and adds non-trivial checks for:
- exported_at normalized format
- temporal consistency between effective_date and exported_at
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    results: List[ExpectationResult] = []

    ok = len(cleaned_rows) >= 1
    results.append(
        ExpectationResult(
            "min_one_row",
            ok,
            "halt",
            f"cleaned_rows={len(cleaned_rows)}",
        )
    )

    bad_doc = [row for row in cleaned_rows if not (row.get("doc_id") or "").strip()]
    ok2 = len(bad_doc) == 0
    results.append(
        ExpectationResult(
            "no_empty_doc_id",
            ok2,
            "halt",
            f"empty_doc_id_count={len(bad_doc)}",
        )
    )

    bad_refund = [
        row
        for row in cleaned_rows
        if row.get("doc_id") == "policy_refund_v4"
        and "14 ngày làm việc" in (row.get("chunk_text") or "")
    ]
    ok3 = len(bad_refund) == 0
    results.append(
        ExpectationResult(
            "refund_no_stale_14d_window",
            ok3,
            "halt",
            f"violations={len(bad_refund)}",
        )
    )

    short = [row for row in cleaned_rows if len((row.get("chunk_text") or "")) < 8]
    ok4 = len(short) == 0
    results.append(
        ExpectationResult(
            "chunk_min_length_8",
            ok4,
            "warn",
            f"short_chunks={len(short)}",
        )
    )

    iso_bad = [
        row
        for row in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", (row.get("effective_date") or "").strip())
    ]
    ok5 = len(iso_bad) == 0
    results.append(
        ExpectationResult(
            "effective_date_iso_yyyy_mm_dd",
            ok5,
            "halt",
            f"non_iso_rows={len(iso_bad)}",
        )
    )

    bad_hr_annual = [
        row
        for row in cleaned_rows
        if row.get("doc_id") == "hr_leave_policy"
        and "10 ngày phép năm" in (row.get("chunk_text") or "")
    ]
    ok6 = len(bad_hr_annual) == 0
    results.append(
        ExpectationResult(
            "hr_leave_no_stale_10d_annual",
            ok6,
            "halt",
            f"violations={len(bad_hr_annual)}",
        )
    )

    bad_exported_at = [
        row
        for row in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", (row.get("exported_at") or "").strip())
    ]
    ok7 = len(bad_exported_at) == 0
    results.append(
        ExpectationResult(
            "exported_at_iso_utc",
            ok7,
            "halt",
            f"non_iso_utc_rows={len(bad_exported_at)}",
        )
    )

    temporal_bad = [
        row
        for row in cleaned_rows
        if (row.get("effective_date") or "") > (row.get("exported_at") or "")[:10]
    ]
    ok8 = len(temporal_bad) == 0
    results.append(
        ExpectationResult(
            "effective_not_after_exported",
            ok8,
            "halt",
            f"violations={len(temporal_bad)}",
        )
    )

    halt = any((not result.passed) and result.severity == "halt" for result in results)
    return results, halt
