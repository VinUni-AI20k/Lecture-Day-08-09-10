"""
Telemetry lab: thời gian chạy + token API + chi phí USD ước lượng.

Liên quan slide Day 08:
- **ROI** (chi phí vs chất lượng vs latency): log `duration_ms`, `cost_usd`.
- **CI/CD dữ liệu RAG**: tích hợp RAGAS vào pipeline — ví dụ block deploy nếu faithfulness < 80%.
  Ở lab, faithfulness chấm thang 1–5 → quy ước `faithfulness_ratio = avg/5`; gate 80% ⇔ avg ≥ 4.0.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

LAB_DIR = Path(__file__).resolve().parent
LOGS_DIR = LAB_DIR / "logs"
RUNS_JSONL = LOGS_DIR / "runs.jsonl"

# USD / 1 triệu tokens — cập nhật theo https://openai.com/api/pricing (ghi đè bằng .env)
# LAB_PRICE_CHAT_INPUT_PER_M   — giá input chat (gpt-4o-mini mặc định: $0.15/M)
# LAB_PRICE_CHAT_OUTPUT_PER_M  — giá output chat (gpt-4o-mini mặc định: $0.60/M)
# LAB_PRICE_EMBEDDING_PER_M    — giá embedding   (text-embedding-3-small: $0.02/M)
_DEFAULT_PRICING = {
    "LAB_PRICE_CHAT_INPUT_PER_M": "0.15",
    "LAB_PRICE_CHAT_OUTPUT_PER_M": "0.60",
    "LAB_PRICE_EMBEDDING_PER_M": "0.02",
}

telemetry_ctx: ContextVar[Optional["RunTelemetry"]] = ContextVar("lab_run_telemetry", default=None)


def get_telemetry() -> Optional["RunTelemetry"]:
    return telemetry_ctx.get()


class RunTelemetry:
    """Gom token + thời gian cho một lần chạy; có thể lồng (parent gom cả con)."""

    def __init__(self, run_type: str, label: str = "") -> None:
        self.run_id = str(uuid.uuid4())
        self.run_type = run_type
        self.label = label or ""
        self.t0 = time.perf_counter()
        self.started_iso = datetime.now(timezone.utc).isoformat()
        self.chat_prompt_tokens = 0
        self.chat_completion_tokens = 0
        self.chat_calls = 0
        self.embedding_tokens = 0
        self.embedding_calls = 0

    def add_chat_usage(self, usage: Any) -> None:
        if usage is None:
            return
        self.chat_prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        self.chat_completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        self.chat_calls += 1

    def add_embedding_usage(self, usage: Any) -> None:
        if usage is None:
            return
        t = int(
            getattr(usage, "total_tokens", 0)
            or getattr(usage, "prompt_tokens", 0)
            or 0
        )
        self.embedding_tokens += t
        self.embedding_calls += 1

    def _cost_usd(self) -> Dict[str, float]:
        pin = float(os.getenv("LAB_PRICE_CHAT_INPUT_PER_M", _DEFAULT_PRICING["LAB_PRICE_CHAT_INPUT_PER_M"]))
        pout = float(os.getenv("LAB_PRICE_CHAT_OUTPUT_PER_M", _DEFAULT_PRICING["LAB_PRICE_CHAT_OUTPUT_PER_M"]))
        pemb = float(os.getenv("LAB_PRICE_EMBEDDING_PER_M", _DEFAULT_PRICING["LAB_PRICE_EMBEDDING_PER_M"]))
        c_chat = (self.chat_prompt_tokens / 1e6) * pin + (self.chat_completion_tokens / 1e6) * pout
        c_emb = (self.embedding_tokens / 1e6) * pemb
        return {
            "chat_usd": round(c_chat, 6),
            "embedding_usd": round(c_emb, 6),
            "total_usd": round(c_chat + c_emb, 6),
        }

    # Tên field chuẩn dùng trong extra (nhất quán giữa api_server, rag_answer, eval):
    #   success      bool  — True nếu run hoàn thành không lỗi
    #   error_type   str   — tên exception class khi lỗi, None nếu thành công
    #   query_preview str  — 200 ký tự đầu của query (không log toàn bộ)
    #   retrieval_mode str — "dense" | "sparse" | "hybrid"
    #   request_id   str  — X-Request-ID từ HTTP header (api_server)

    # Các key chứa secret bị lọc khỏi extra trước khi ghi log
    _SECRET_KEYS = frozenset({"key", "token", "secret", "password", "api_key", "hf_token"})

    def finish(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        duration_ms = round((time.perf_counter() - self.t0) * 1000, 2)
        cost = self._cost_usd()

        # Lọc bỏ các field có thể chứa secret trước khi ghi ra file log
        safe_extra: Optional[Dict[str, Any]] = None
        if extra:
            safe_extra = {
                k: v for k, v in extra.items()
                if not any(s in k.lower() for s in self._SECRET_KEYS)
            }

        entry: Dict[str, Any] = {
            "run_id": self.run_id,
            "started_at": self.started_iso,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "run_type": self.run_type,
            "label": self.label,
            "usage": {
                "chat": {
                    "prompt_tokens": self.chat_prompt_tokens,
                    "completion_tokens": self.chat_completion_tokens,
                    "calls": self.chat_calls,
                },
                "embedding": {
                    "total_tokens": self.embedding_tokens,
                    "calls": self.embedding_calls,
                },
            },
            "cost_usd": cost,
        }
        if safe_extra:
            entry["extra"] = safe_extra
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(RUNS_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry


def attach_cicd_faithfulness_fields(extra: Dict[str, Any], faithfulness_avg_1_to_5: Optional[float]) -> None:
    """Bổ sung trường phục vụ gate kiểu slide (faithfulness < 80% → fail)."""
    if faithfulness_avg_1_to_5 is None:
        extra["faithfulness_avg_1_to_5"] = None
        extra["faithfulness_ratio_0_to_1"] = None
        extra["cicd_faithfulness_gate_min_80pct"] = None
        return
    ratio = round(faithfulness_avg_1_to_5 / 5.0, 4)
    extra["faithfulness_avg_1_to_5"] = round(faithfulness_avg_1_to_5, 3)
    extra["faithfulness_ratio_0_to_1"] = ratio
    extra["cicd_faithfulness_gate_min_80pct"] = ratio >= 0.8
