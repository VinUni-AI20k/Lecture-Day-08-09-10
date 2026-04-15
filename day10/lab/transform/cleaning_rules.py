"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).
"""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime, timezone
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

# ──────────────────────────────────────────────
# Rule 7 — Chunk text quá ngắn (noise / spam)
# metric_impact: inject row chunk_text="OK" (2 ký tự) → quarantine_records tăng 1.
#   Trên bộ mẫu baseline: 0 row bị ảnh hưởng (tất cả text hợp lệ đủ dài).
#   Khi inject 1 row ngắn: quarantine_records baseline=5 → 6 (+1).
# ──────────────────────────────────────────────
MIN_CHUNK_CHARS = 20

# ──────────────────────────────────────────────
# Rule 8 — Phát hiện HTML/script injection trong chunk_text
# metric_impact: inject row chunk_text="<script>alert(1)</script>" → quarantine_records tăng 1.
#   Pattern khớp thẻ HTML mở bất kỳ (<tag, </tag); đủ rộng để bắt XSS phổ biến.
#   Trên bộ mẫu baseline: 0 row bị ảnh hưởng.
#   Khi inject 1 row HTML: quarantine_records baseline=5 → 6 (+1).
# ──────────────────────────────────────────────
_HTML_TAG = re.compile(r"<[a-zA-Z/][^>]*>")

# ──────────────────────────────────────────────
# Rule 9 — exported_at trong tương lai (future timestamp)
# metric_impact: inject row exported_at="2099-01-01T00:00:00" → quarantine_records tăng 1.
#   Timestamp tương lai báo hiệu lỗi clock DB hoặc dữ liệu giả mạo.
#   Trên bộ mẫu baseline: 0 row bị ảnh hưởng (tất cả exported_at=2026-04-10, hợp lệ).
#   Khi inject 1 row future: quarantine_records baseline=5 → 6 (+1).
# ──────────────────────────────────────────────
_ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


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


def _parse_exported_at(raw: str) -> datetime | None:
    """Parse exported_at ISO datetime; trả None nếu không parse được."""
    s = (raw or "").strip()
    if not _ISO_DATETIME.match(s):
        return None
    # Cắt phần microsecond/timezone để parse đơn giản
    s_trim = s[:19]  # "YYYY-MM-DDTHH:MM:SS"
    try:
        return datetime.strptime(s_trim, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


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

    (Sprint 2):
    7) Quarantine: chunk_text quá ngắn (< MIN_CHUNK_CHARS ký tự sau strip) — noise / spam.
       metric_impact: inject "OK" → quarantine_records +1.
    8) Quarantine: chunk_text chứa HTML/script tag — nguy cơ injection vào vector store.
       metric_impact: inject "<script>alert(1)</script>" → quarantine_records +1.
    9) Quarantine: exported_at là timestamp tương lai (> thời điểm chạy pipeline) — lỗi clock DB.
       metric_impact: inject exported_at="2099-01-01T00:00:00" → quarantine_records +1.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0
    now_utc = datetime.now(timezone.utc)

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        # ── Baseline rule 1: allowlist doc_id ──────────────────────────────
        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        # ── Baseline rule 2: chuẩn hoá effective_date ──────────────────────
        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        # ── Baseline rule 3: HR stale version ──────────────────────────────
        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        # ── Baseline rule 4: chunk_text rỗng ───────────────────────────────
        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        # ── Rule 7 (MỚI): chunk_text quá ngắn ─────────────────────────────
        # Kiểm tra sau khi đã loại rỗng (rule 4) để reason rõ ràng hơn.
        if len(text.strip()) < MIN_CHUNK_CHARS:
            quarantine.append(
                {
                    **raw,
                    "reason": "chunk_text_too_short",
                    "chunk_text_len": len(text.strip()),
                    "min_required": MIN_CHUNK_CHARS,
                }
            )
            continue

        # ── Rule 8 (MỚI): HTML/script injection ────────────────────────────
        if _HTML_TAG.search(text):
            quarantine.append(
                {
                    **raw,
                    "reason": "chunk_text_contains_html",
                    "matched_pattern": _HTML_TAG.search(text).group(0),
                }
            )
            continue

        # ── Rule 9 (MỚI): exported_at future timestamp ─────────────────────
        if exported_at:
            exp_dt = _parse_exported_at(exported_at)
            if exp_dt is not None and exp_dt > now_utc:
                quarantine.append(
                    {
                        **raw,
                        "reason": "exported_at_future_timestamp",
                        "exported_at_parsed": exp_dt.isoformat(),
                        "pipeline_run_utc": now_utc.isoformat(),
                    }
                )
                continue

        # ── Baseline rule 5: dedupe chunk_text ─────────────────────────────
        key = _norm_text(text)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        # ── Baseline rule 6: fix stale refund window ────────────────────────
        fixed_text = text
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