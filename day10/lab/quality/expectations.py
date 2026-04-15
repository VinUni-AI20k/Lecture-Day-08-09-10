"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.

Bổ sung (Member 1 — Quality Owner):
  E7  (halt) : doc_id phải thuộc allowlist sau clean (không còn doc lạ nào lọt qua).
  E8  (halt) : chunk_text không được rỗng sau clean.
  E9  (halt) : Không tồn tại cặp (doc_id, chunk_text_key) xung đột version HR cũ (10 ngày phép) lẫn mới (12 ngày phép).
  E10 (warn) : exported_at phải ở định dạng ISO 8601 (YYYY-MM-DDTHH:MM:SS).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

# Phải khớp với ALLOWED_DOC_IDS trong cleaning_rules.py
ALLOWED_DOC_IDS: Set[str] = {
    "policy_refund_v4",
    "sla_p1_2026",
    "it_helpdesk_faq",
    "hr_leave_policy",
}

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


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

    # ─────────────────────────────────────────────────────────────
    # E1: có ít nhất 1 dòng sau clean
    # ─────────────────────────────────────────────────────────────
    ok = len(cleaned_rows) >= 1
    results.append(
        ExpectationResult(
            "min_one_row",
            ok,
            "halt",
            f"cleaned_rows={len(cleaned_rows)}",
        )
    )

    # ─────────────────────────────────────────────────────────────
    # E2: không doc_id rỗng
    # ─────────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────────
    # E3: policy refund không được chứa cửa sổ sai 14 ngày (sau khi đã fix)
    # ─────────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────────
    # E4: chunk_text đủ dài (≥8 ký tự)
    # ─────────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────────
    # E5: effective_date đúng định dạng ISO sau clean (phát hiện parser lỏng)
    # ─────────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────────
    # E6: không còn marker phép năm cũ 10 ngày trên doc HR (conflict version sau clean)
    # ─────────────────────────────────────────────────────────────
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

    # ═════════════════════════════════════════════════════════════
    # E7 [NEW — halt]: doc_id sau clean phải thuộc allowlist
    #    Metric impact: nếu cleaning_rules bỏ qua rule allowlist,
    #    expectation này bắt được doc lạ lọt vào cleaned output.
    #    Kịch bản: thêm dòng "legacy_catalog_xyz_zzz" vào CSV mà
    #    không có rule quarantine → E7 FAIL → pipeline halt.
    # ═════════════════════════════════════════════════════════════
    unauthorized_docs = [
        r
        for r in cleaned_rows
        if (r.get("doc_id") or "") not in ALLOWED_DOC_IDS
    ]
    ok7 = len(unauthorized_docs) == 0
    results.append(
        ExpectationResult(
            "doc_id_in_allowlist",
            ok7,
            "halt",
            (
                f"unauthorized_count={len(unauthorized_docs)}"
                + (
                    f" ids={[r.get('doc_id') for r in unauthorized_docs[:5]]}"
                    if unauthorized_docs
                    else ""
                )
            ),
        )
    )

    # ═════════════════════════════════════════════════════════════
    # E8 [NEW — halt]: chunk_text không được rỗng sau clean
    #    Metric impact: nếu clean_rows cho phép text rỗng qua,
    #    vector embedding sẽ tạo ra noise vector → top-k sai.
    #    Kịch bản: dòng có chunk_text="" mà không bị quarantine
    #    → E8 FAIL → pipeline halt.
    # ═════════════════════════════════════════════════════════════
    empty_text = [
        r
        for r in cleaned_rows
        if not (r.get("chunk_text") or "").strip()
    ]
    ok8 = len(empty_text) == 0
    results.append(
        ExpectationResult(
            "chunk_text_not_empty",
            ok8,
            "halt",
            f"empty_chunk_text_count={len(empty_text)}",
        )
    )

    # ═════════════════════════════════════════════════════════════
    # E9 [NEW — halt]: Không tồn tại xung đột version policy
    #    (cùng doc_id xuất hiện với 2+ effective_date KHÁC NHAU
    #    trong cùng một batch → dấu hiệu merge nhầm snapshot).
    #    Metric impact: nếu 2 bản hr_leave_policy năm 2025 & 2026
    #    lọt cùng lúc vào cleaned, retrieval trả về kết quả mâu thuẫn.
    #    Kịch bản: bỏ rule quarantine stale HR → E9 FAIL → halt.
    # ═════════════════════════════════════════════════════════════
    from collections import defaultdict

    doc_dates: Dict[str, set] = defaultdict(set)
    for r in cleaned_rows:
        d = r.get("doc_id", "")
        e = (r.get("effective_date") or "").strip()
        if d and e:
            doc_dates[d].add(e)

    conflicting_docs = {
        doc_id: sorted(dates)
        for doc_id, dates in doc_dates.items()
        if len(dates) > 1
    }
    ok9 = len(conflicting_docs) == 0
    results.append(
        ExpectationResult(
            "no_conflicting_version_policy",
            ok9,
            "halt",
            (
                f"conflicting_docs={len(conflicting_docs)}"
                + (f" detail={conflicting_docs}" if conflicting_docs else "")
            ),
        )
    )

    # ═════════════════════════════════════════════════════════════
    # E10 [NEW — warn]: exported_at phải ở định dạng ISO 8601
    #    (YYYY-MM-DDTHH:MM:SS …).
    #    Severity = warn vì trường này không ảnh hưởng trực tiếp
    #    đến nội dung truy vấn, nhưng sai format gây lỗi freshness check.
    #    Metric impact: freshness_check đọc exported_at để tính SLA;
    #    format sai → freshness luôn FAIL dù data mới.
    # ═════════════════════════════════════════════════════════════
    bad_exported = [
        r
        for r in cleaned_rows
        if not _ISO_DATETIME.match((r.get("exported_at") or "").strip())
    ]
    ok10 = len(bad_exported) == 0
    results.append(
        ExpectationResult(
            "exported_at_iso8601_format",
            ok10,
            "warn",
            f"non_iso_exported_at={len(bad_exported)}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt
