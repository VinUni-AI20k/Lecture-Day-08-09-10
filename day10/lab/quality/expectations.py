"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.
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
    """
    Trả về (results, should_halt).

    should_halt = True nếu có bất kỳ expectation severity halt nào fail.
    """
    results: List[ExpectationResult] = []

    # E1: có ít nhất 1 dòng sau clean
    ok = len(cleaned_rows) >= 1
    results.append(
        ExpectationResult(
            "min_one_row",
            ok,
            "halt",
            f"cleaned_rows={len(cleaned_rows)}",
        )
    )

    # E2: không doc_id rỗng
    bad_doc = [r for r in cleaned_rows if not (r.get("doc_id") or "").strip()]
    ok2 = len(bad_doc) == 0
    results.append(
        ExpectationResult(
            "no_empty_doc_id",
            ok2,
            "halt",
            f"empty_doc_id_count={len(bad_doc)}",
        )
    )

    # E3: policy refund không được chứa cửa sổ sai 14 ngày (sau khi đã fix)
    bad_refund = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4"
        and "14 ngày làm việc" in (r.get("chunk_text") or "")
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

    # E4: chunk_text đủ dài
    short = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) < 8]
    ok4 = len(short) == 0
    results.append(
        ExpectationResult(
            "chunk_min_length_8",
            ok4,
            "warn",
            f"short_chunks={len(short)}",
        )
    )

    # E5: effective_date đúng định dạng ISO sau clean (phát hiện parser lỏng)
    iso_bad = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", (r.get("effective_date") or "").strip())
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

    # E6: không còn marker phép năm cũ 10 ngày trên doc HR (conflict version sau clean)
    bad_hr_annual = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy"
        and "10 ngày phép năm" in (r.get("chunk_text") or "")
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

    # E7: warn if any chunk_text exceeds 2000 chars — may indicate a parse/merge error upstream
    # (e.g. two sections accidentally concatenated, or OCR dumping an entire page as one chunk).
    # severity=warn: pipeline continues but flags for review.
    # metric_impact: inject a row with chunk_text > 2000 chars → E7 FAIL (warn) appears in log.
    oversized = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) > 2000]
    results.append(
        ExpectationResult(
            "chunk_max_length_2000",
            len(oversized) == 0,
            "warn",
            f"oversized_chunks={len(oversized)}",
        )
    )

    # E8: halt if any unknown doc_id survived cleaning — second-line defence after Rule 1.
    # Should never happen in a clean run; fires only if cleaning_rules is bypassed or
    # ALLOWED_DOC_IDS diverges from the contract.
    # metric_impact: pass --skip-validate + inject unknown doc_id row → E8 FAIL (halt) in log.
    from transform.cleaning_rules import ALLOWED_DOC_IDS  # noqa: PLC0415
    unknown_doc = [r for r in cleaned_rows if (r.get("doc_id") or "") not in ALLOWED_DOC_IDS]
    results.append(
        ExpectationResult(
            "all_doc_ids_in_allowlist",
            len(unknown_doc) == 0,
            "halt",
            f"unknown_doc_count={len(unknown_doc)}",
        )
    )

    # E9: warn if any cleaned row has an empty exported_at field.
    # An empty exported_at means freshness_check cannot compute age accurately for that row —
    # the pipeline still publishes it, but the freshness SLI is blind to its source timestamp.
    # severity=warn: publish proceeds; flag for backlog review so the source export is fixed.
    # metric_impact: inject a row with exported_at="" that passes all other rules → E9 FAIL (warn) in log.
    missing_exported = [r for r in cleaned_rows if not (r.get("exported_at") or "").strip()]
    results.append(
        ExpectationResult(
            "exported_at_not_empty",
            len(missing_exported) == 0,
            "warn",
            f"missing_exported_at={len(missing_exported)}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt
