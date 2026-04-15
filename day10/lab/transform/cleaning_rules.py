"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).
"""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")

_REASON_UNKNOWN_DOC_ID = "unknown_doc_id"
_REASON_MISSING_EFFECTIVE_DATE = "missing_effective_date"
_REASON_INVALID_EFFECTIVE_DATE_FORMAT = "invalid_effective_date_format"
_REASON_STALE_HR_POLICY_EFFECTIVE_DATE = "stale_hr_policy_effective_date"
_REASON_MISSING_CHUNK_TEXT = "missing_chunk_text"
_REASON_DUPLICATE_CHUNK_TEXT = "duplicate_chunk_text"
_REASON_NON_ISO_EFFECTIVE_DATE_SOURCE = "non_iso_effective_date_source"
_REASON_MISSING_EXPORTED_AT = "missing_exported_at"
_REASON_INVALID_EXPORTED_AT_FORMAT = "invalid_exported_at_format"


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", _REASON_INVALID_EFFECTIVE_DATE_FORMAT


def _validate_exported_at(raw: str) -> Tuple[str, str]:
    """Validate exported_at as ISO datetime; return normalized raw value if valid."""
    s = (raw or "").strip()
    if not s:
        return "", _REASON_MISSING_EXPORTED_AT

    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return s, ""
    except ValueError:
        return "", _REASON_INVALID_EXPORTED_AT_FORMAT


def _is_non_iso_source_effective_date(raw: str) -> bool:
    """Detect source dates that are parseable but violate ISO input contract."""
    s = (raw or "").strip()
    return bool(_DMY_SLASH.match(s))


def _quarantine_row(raw: Dict[str, str], reason: str, **extra: Any) -> Dict[str, Any]:
    """Create a consistent quarantine payload for downstream observability."""
    row: Dict[str, Any] = {**raw, "reason": reason}
    if extra:
        row.update(extra)
    return row


def _apply_refund_window_fix(text: str, doc_id: str, enabled: bool) -> str:
    """Apply 14-day -> 7-day refund correction for policy_refund_v4 when enabled."""
    if not enabled or doc_id != "policy_refund_v4":
        return text
    if "14 ngày làm việc" not in text:
        return text

    fixed = text.replace("14 ngày làm việc", "7 ngày làm việc")
    return fixed + " [cleaned: stale_refund_window]"


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.
    7) Quarantine bản ghi có effective_date nguồn không phải ISO (ví dụ DD/MM/YYYY).
    8) Quarantine bản ghi có exported_at thiếu hoặc sai định dạng datetime ISO.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append(_quarantine_row(raw, _REASON_UNKNOWN_DOC_ID))
            continue

        exported_at_norm, exported_at_err = _validate_exported_at(exported_at)
        if exported_at_err:
            quarantine.append(
                _quarantine_row(
                    raw,
                    exported_at_err,
                    exported_at_raw=exported_at,
                )
            )
            continue

        if _is_non_iso_source_effective_date(eff_raw):
            eff_norm_preview, _ = _normalize_effective_date(eff_raw)
            quarantine.append(
                _quarantine_row(
                    raw,
                    _REASON_NON_ISO_EFFECTIVE_DATE_SOURCE,
                    effective_date_raw=eff_raw,
                    suggested_effective_date=eff_norm_preview,
                )
            )
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append(_quarantine_row(raw, _REASON_MISSING_EFFECTIVE_DATE))
            continue
        if eff_err == _REASON_INVALID_EFFECTIVE_DATE_FORMAT:
            quarantine.append(
                _quarantine_row(
                    raw,
                    _REASON_INVALID_EFFECTIVE_DATE_FORMAT,
                    effective_date_raw=eff_raw,
                )
            )
            continue

        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                _quarantine_row(
                    raw,
                    _REASON_STALE_HR_POLICY_EFFECTIVE_DATE,
                    effective_date_normalized=eff_norm,
                )
            )
            continue

        if not text:
            quarantine.append(_quarantine_row(raw, _REASON_MISSING_CHUNK_TEXT))
            continue

        key = _norm_text(text)
        if key in seen_text:
            quarantine.append(_quarantine_row(raw, _REASON_DUPLICATE_CHUNK_TEXT))
            continue
        seen_text.add(key)

        fixed_text = _apply_refund_window_fix(text, doc_id, apply_refund_window_fix)

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at_norm,
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
