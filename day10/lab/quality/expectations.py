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

    # E7 (NEW) — no_migration_error_marker_in_cleaned
    # metric_impact: nếu cleaning_rules thiếu rule 7, chunk "lỗi migration" lọt vào cleaned →
    # expectation này halt pipeline. Chứng cứ sprint 3: chạy --skip-validate để thấy E7 FAIL.
    bad_migration = [
        r
        for r in cleaned_rows
        if "lỗi migration" in (r.get("chunk_text") or "").lower()
    ]
    ok7 = len(bad_migration) == 0
    results.append(
        ExpectationResult(
            "no_migration_error_marker_in_cleaned",
            ok7,
            "halt",
            f"violations={len(bad_migration)}",
        )
    )

    # E8 (NEW) — sla_doc_effective_date_min_2026
    # metric_impact: đảm bảo không có chunk SLA cũ (< 2026-01-01) nào lọt qua clean.
    # Severity warn (không halt) vì pipeline vẫn hoạt động được với SLA warn —
    # nhưng cần alert để owner xem xét rollback.
    # Chứng cứ inject: thêm row sla_p1_2026 với effective_date=2025-06-01 + --skip-validate →
    # E8 WARN xuất hiện trong log ngay cả khi pipeline không halt.
    bad_sla_date = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "sla_p1_2026"
        and (r.get("effective_date") or "2099") < "2026-01-01"
    ]
    ok8 = len(bad_sla_date) == 0
    results.append(
        ExpectationResult(
            "sla_doc_effective_date_min_2026",
            ok8,
            "warn",
            f"stale_sla_chunks={len(bad_sla_date)}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt
