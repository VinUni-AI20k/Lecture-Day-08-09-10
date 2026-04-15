"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).
"""

from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
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
# Zero-width / BOM — thường gặp khi copy-paste từ PDF/Slack; làm lệch dedupe và retrieval.
_INVISIBLE_CHARS = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None)


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
    return "", "invalid_effective_date_format"


def _sanitize_chunk_text_unicode(text: str) -> Tuple[str, bool]:
    """
    Rule: **unicode_whitespace_hygiene**

    Chuẩn hoá NFC, bỏ ký tự zero-width/BOM, gom khoảng trắng Unicode về space rồi collapse.
    Chuỗi chỉ còn khoảng trắng → rỗng (giúp bắt whitespace-only mà strip đơn giản không bắt được).

    metric_impact: thay đổi `chunk_text` (và `chunk_id` phụ thuộc hash) khi có ký tự ẩn / NBSP;
    có thể làm tăng/giảm duplicate hoặc quarantine nếu text trở thành rỗng.
    """
    if not text:
        return "", False
    t = unicodedata.normalize("NFC", text)
    t = t.translate(_INVISIBLE_CHARS)
    # NBSP và một số khoảng trắng phổ biến → ASCII space trước khi collapse
    t = t.replace("\u00a0", " ").replace("\u1680", " ").replace("\u2000", " ").replace("\u2001", " ")
    t = t.replace("\u2002", " ").replace("\u2003", " ").replace("\u2004", " ").replace("\u2005", " ")
    t = t.replace("\u2006", " ").replace("\u2007", " ").replace("\u2008", " ").replace("\u2009", " ")
    t = t.replace("\u200a", " ").replace("\u202f", " ").replace("\u205f", " ").replace("\u3000", " ")
    t = " ".join(t.split())
    return t, t != text


def _canonical_exported_at(raw: str) -> Tuple[str, str]:
    """
    Rule: **exported_at_iso_or_quarantine**

    Parse `exported_at` về dạng ISO `YYYY-MM-DDTHH:MM:SS` (UTC-naive, không timezone offset trong string).
    Thiếu hoặc không parse được → lỗi để quarantine.

    metric_impact: tăng `quarantine_records` khi timestamp export sai; chuẩn hoá giá trị hợp lệ cho downstream.
    """
    s = (raw or "").strip()
    if not s:
        return "", "missing_exported_at"
    # Cho phép 'Z' cuối (UTC) rồi bỏ khi canonical
    if s.endswith("Z"):
        s = s[:-1]
    s = s.replace(" ", "T", 1) if " " in s and "T" not in s else s
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return "", "invalid_exported_at"
    return dt.strftime("%Y-%m-%dT%H:%M:%S"), ""


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
    5) **unicode_whitespace_hygiene**: NFC + bỏ zero-width/BOM + collapse whitespace (metric_impact khi có ký tự ẩn).
    6) **exported_at_iso_or_quarantine**: exported_at bắt buộc parse được → canonical ISO datetime string.
    7) **dedupe_doc_scoped_content**: loại trùng theo (doc_id, normalized chunk_text), không gộp nhầm giữa các doc (giữ bản đầu).
    8) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_doc_text: set[Tuple[str, str]] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_raw = raw.get("exported_at", "")

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        text, unicode_changed = _sanitize_chunk_text_unicode(text)
        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        exported_at, exp_err = _canonical_exported_at(exported_raw)
        if exp_err:
            quarantine.append(
                {
                    **raw,
                    "reason": exp_err,
                    "exported_at_raw": exported_raw,
                }
            )
            continue

        # Rule: **dedupe_doc_scoped_content** — cùng nội dung ở hai doc_id khác nhau không bị coi là trùng.
        dedupe_key = (doc_id, _norm_text(text))
        if dedupe_key in seen_doc_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_doc_text.add(dedupe_key)

        fixed_text = text
        if unicode_changed:
            fixed_text += " [cleaned: unicode_whitespace_hygiene]"
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at or "",
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
