"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline (README): allowlist doc_id, normalize effective_date, quarantine HR stale,
reject empty text/date, dedupe, fix refund 14→7.

Sinh viên (Người 2) thêm ≥3 rule mới — mỗi rule có tên + docstring + metric_impact
(xem biến NEW_RULE_IDS và các hàm rule_* bên dưới).
"""

from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

# --- Rule mới (đủ ≥3, có tên cố định để rubric / báo cáo metric_impact) ---
NEW_RULE_IDS: Tuple[str, ...] = (
    "unicode_whitespace_hygiene",
    "exported_at_iso_or_quarantine",
    "malformed_row_guards",
    "dedupe_doc_scoped_content",
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_INVISIBLE_CHARS = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None)


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """Trả về (iso_date, error_reason). iso_date rỗng nếu không parse được."""
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


def rule_unicode_whitespace_hygiene(text: str) -> Tuple[str, bool]:
    """
    Rule **unicode_whitespace_hygiene** (NEW_RULE_IDS[0])

    Chuẩn hoá NFC, bỏ zero-width/BOM, đưa NBSP và khoảng trắng Unicode phổ biến về space rồi collapse.
    Chuỗi chỉ còn khoảng trắng → rỗng.

    metric_impact: đổi `chunk_text` / `chunk_id` khi có ký tự ẩn; có thể đổi `cleaned_records`/`quarantine_records`
    (duplicate trùng sau chuẩn hoá, hoặc text rỗng → quarantine).
    """
    if not text:
        return "", False
    t = unicodedata.normalize("NFC", text)
    t = t.translate(_INVISIBLE_CHARS)
    t = t.replace("\u00a0", " ").replace("\u1680", " ").replace("\u2000", " ").replace("\u2001", " ")
    t = t.replace("\u2002", " ").replace("\u2003", " ").replace("\u2004", " ").replace("\u2005", " ")
    t = t.replace("\u2006", " ").replace("\u2007", " ").replace("\u2008", " ").replace("\u2009", " ")
    t = t.replace("\u200a", " ").replace("\u202f", " ").replace("\u205f", " ").replace("\u3000", " ")
    t = " ".join(t.split())
    return t, t != text


def rule_exported_at_iso_or_quarantine(raw_exported: str) -> Tuple[str, str]:
    """
    Rule **exported_at_iso_or_quarantine** (NEW_RULE_IDS[1])

    Parse `exported_at` → `YYYY-MM-DDTHH:MM:SS`. Thiếu / không parse được → mã lỗi để quarantine.

    metric_impact: tăng `quarantine_records` khi timestamp export sai; chuẩn hoá giá trị hợp lệ trên cleaned.
    """
    s = (raw_exported or "").strip()
    if not s:
        return "", "missing_exported_at"
    if s.endswith("Z"):
        s = s[:-1]
    s = s.replace(" ", "T", 1) if " " in s and "T" not in s else s
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return "", "invalid_exported_at"
    return dt.strftime("%Y-%m-%dT%H:%M:%S"), ""


def rule_malformed_row_guards(raw: Dict[str, str], text_before_sanitize: str) -> Optional[str]:
    """
    Rule **malformed_row_guards** (NEW_RULE_IDS[2]) — phát hiện record malformed trước khi clean sâu.

    - `chunk_id` rỗng (không gắn được dòng source / join catalog).
    - `chunk_text` chứa byte NUL (binary corrupt / lỗi export).

    metric_impact: tăng `quarantine_records` khi export lỗi cấu trúc; 0 dòng khi dữ liệu sạch.

    Trả về: reason string nếu quarantine, hoặc None nếu OK.
    """
    if not (raw.get("chunk_id") or "").strip():
        return "malformed_missing_chunk_id"
    if "\x00" in text_before_sanitize:
        return "malformed_chunk_contains_nul_byte"
    return None


def rule_exported_covers_effective_date(eff_norm: str, exported_at_iso: str) -> bool:
    """
    Phần kiểm tra timeline dùng chung với rule exported_at (không phải rule ID riêng).

    Export không được “trước” ngày hiệu lực (dữ liệu vô lý / export lạ).

    metric_impact: `quarantine_records` khi timeline sai; cleaned nhận `exported_at` đã canonical.
    """
    eff_d = date.fromisoformat(eff_norm)
    exp_dt = datetime.fromisoformat(exported_at_iso)
    return exp_dt.date() >= eff_d


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline:
    1) unknown_doc_id
    2) effective_date parse / missing
    3) stale_hr_policy_effective_date
    4) Rule mới (xem NEW_RULE_IDS): malformed → unicode → exported_at → timeline → dedupe doc-scoped
    5) missing_chunk_text (sau unicode)
    6) duplicate_chunk_text (dedupe theo doc_id + normalized text)
    7) Refund 14→7 (+ marker)
    """
    quarantine: List[Dict[str, Any]] = []
    seen_doc_text: Set[Tuple[str, str]] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text_raw = raw.get("chunk_text", "")
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

        # --- NEW: malformed_row_guards ---
        bad = rule_malformed_row_guards(raw, text_raw)
        if bad:
            quarantine.append({**raw, "reason": bad})
            continue

        # --- NEW: unicode_whitespace_hygiene ---
        text, unicode_changed = rule_unicode_whitespace_hygiene(text_raw)
        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        # --- NEW: exported_at_iso_or_quarantine ---
        exported_at, exp_err = rule_exported_at_iso_or_quarantine(exported_raw)
        if exp_err:
            quarantine.append(
                {
                    **raw,
                    "reason": exp_err,
                    "exported_at_raw": exported_raw,
                }
            )
            continue

        # Timeline: export không được trước effective_date (cùng rule family exported_at)
        if not rule_exported_covers_effective_date(eff_norm, exported_at):
            quarantine.append(
                {
                    **raw,
                    "reason": "malformed_timeline_export_before_effective",
                    "effective_date_normalized": eff_norm,
                    "exported_at_normalized": exported_at,
                }
            )
            continue

        # --- NEW: dedupe_doc_scoped_content ---
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


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


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
