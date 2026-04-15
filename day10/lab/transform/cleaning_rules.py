"""
Cleaning rules for raw export -> cleaned rows + quarantine.

Baseline rules are preserved and extended with measurable rules:
- validate and normalize exported_at
- reject temporal inconsistency (effective_date > exported_at)
- reject coarse off-topic chunks by doc keyword checks
"""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

DEFAULT_DOC_KEYWORDS: Mapping[str, Tuple[str, ...]] = {
    "policy_refund_v4": ("hoàn tiền", "refund", "ngày làm việc"),
    "sla_p1_2026": ("p1", "sla"),
    "it_helpdesk_faq": ("đăng nhập", "mật khẩu", "tài khoản"),
    "hr_leave_policy": ("phép năm", "chính sách"),
}

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    digest = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{digest}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def _normalize_exported_at(raw: str) -> Tuple[str, str]:
    s = (raw or "").strip()
    if not s:
        return "", "missing_exported_at"
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        return dt.replace(tzinfo=None).isoformat(timespec="seconds") + "Z", ""
    except ValueError:
        return "", "invalid_exported_at_format"


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rows.append({key: (value or "").strip() for key, value in row.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
    refund_window_days: int = 7,
    hr_leave_min_effective_date: str = "2026-01-01",
    doc_keywords: Mapping[str, Tuple[str, ...]] | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    quarantine: List[Dict[str, Any]] = []
    cleaned: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    seq = 0

    keyword_map = dict(DEFAULT_DOC_KEYWORDS)
    if doc_keywords:
        keyword_map.update(dict(doc_keywords))

    refund_from = "14 ngày làm việc"
    refund_to = f"{max(1, int(refund_window_days))} ngày làm việc"

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        effective_date_raw = raw.get("effective_date", "")
        exported_at_raw = raw.get("exported_at", "")

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        effective_date_norm, effective_date_err = _normalize_effective_date(effective_date_raw)
        if effective_date_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if effective_date_err:
            quarantine.append(
                {
                    **raw,
                    "reason": effective_date_err,
                    "effective_date_raw": effective_date_raw,
                }
            )
            continue

        if doc_id == "hr_leave_policy" and effective_date_norm < hr_leave_min_effective_date:
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": effective_date_norm,
                    "hr_leave_min_effective_date": hr_leave_min_effective_date,
                }
            )
            continue

        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        exported_at_norm, exported_at_err = _normalize_exported_at(exported_at_raw)
        if exported_at_err:
            quarantine.append({**raw, "reason": exported_at_err})
            continue

        if effective_date_norm > exported_at_norm[:10]:
            quarantine.append(
                {
                    **raw,
                    "reason": "effective_date_after_exported_at",
                    "effective_date_normalized": effective_date_norm,
                    "exported_at_normalized": exported_at_norm,
                }
            )
            continue

        required_keywords = keyword_map.get(doc_id) or ()
        normalized_for_topic = _norm_text(text)
        if required_keywords and not any(keyword in normalized_for_topic for keyword in required_keywords):
            quarantine.append(
                {
                    **raw,
                    "reason": "topic_keyword_mismatch",
                    "required_keywords": "|".join(required_keywords),
                }
            )
            continue

        normalized_text = " ".join(text.strip().split())
        dedupe_key = _norm_text(normalized_text)
        if dedupe_key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(dedupe_key)

        fixed_text = normalized_text
        if apply_refund_window_fix and doc_id == "policy_refund_v4" and refund_from in fixed_text:
            fixed_text = fixed_text.replace(refund_from, refund_to)
            fixed_text += " [cleaned: stale_refund_window]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": effective_date_norm,
                "exported_at": exported_at_norm,
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    if not rows:
        path.write_text(",".join(fieldnames) + "\n", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return

    ordered_keys: List[str] = []
    seen_keys: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen_keys:
                seen_keys.add(key)
                ordered_keys.append(key)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=ordered_keys, extrasaction="ignore", restval="")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
