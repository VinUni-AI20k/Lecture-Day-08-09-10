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

    # E7: không còn effective_date rỗng sau clean
    missing_effective_date = [
        r
        for r in cleaned_rows
        if not (r.get("effective_date") or "").strip()
    ]
    ok7 = len(missing_effective_date) == 0
    results.append(
        ExpectationResult(
            "no_missing_effective_date",
            ok7,
            "halt",
            f"missing_effective_date_rows={len(missing_effective_date)}",
        )
    )

    # E8: exported_at phải chứa định dạng ISO datetime (VD: YYYY-MM-DDTHH:MM:SS)
    exported_at_bad = [
        r
        for r in cleaned_rows
        if not re.search(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
            (r.get("exported_at") or "").strip(),
        )
    ]
    ok9 = len(exported_at_bad) == 0
    results.append(
        ExpectationResult(
            "exported_at_iso_datetime",
            ok9,
            "halt",
            f"non_iso_exported_at_rows={len(exported_at_bad)}",
        )
    )
    
    #E9: SLA P1 nên là 15 phút / 4 giờ (chấp nhận cả dạng 15p, 4h)
    bad_sla = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "sla_p1_2026"
        and not (
            re.search(r"\b15\s*(phút|p)\b", (r.get("chunk_text") or ""), re.IGNORECASE)
            and re.search(r"\b4\s*(giờ|h)\b", (r.get("chunk_text") or ""), re.IGNORECASE)
        )
    ]
    ok_w1 = len(bad_sla) == 0
    results.append(
        ExpectationResult(
            "sla_p1_expected_response_and_resolution",
            ok_w1,
            "warn",
            f"suspicious_sla_rows={len(bad_sla)}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt

    
