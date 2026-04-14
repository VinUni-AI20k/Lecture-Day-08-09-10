"""
graph.py — Supervisor Orchestrator (Day 09)
Input → Supervisor → [retrieval | policy_tool | multi_hop] → synthesis → Output

Chạy:
    python graph.py
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load day09/lab/.env (copy từ day08/lab/.env nếu dùng chung OpenAI key)
load_dotenv(Path(__file__).resolve().parent / ".env")

import json
import os
import re
import time
from datetime import datetime
from typing import Literal, Optional, TypedDict

from workers.retrieval import run as retrieval_run
from workers.policy_tool import run as policy_tool_run
from workers.synthesis import run as synthesis_run


class AgentState(TypedDict, total=False):
    task: str
    route_reason: str
    risk_high: bool
    needs_tool: bool
    hitl_triggered: bool
    retrieved_chunks: list
    retrieved_sources: list
    policy_result: dict
    mcp_tools_used: list
    final_answer: str
    sources: list
    confidence: float
    history: list
    workers_called: list
    supervisor_route: str
    latency_ms: Optional[int]
    run_id: str
    worker_io_logs: list
    retrieval_top_k: int


def make_initial_state(task: str) -> AgentState:
    return {
        "task": task,
        "route_reason": "",
        "risk_high": False,
        "needs_tool": False,
        "hitl_triggered": False,
        "retrieved_chunks": [],
        "retrieved_sources": [],
        "policy_result": {},
        "mcp_tools_used": [],
        "final_answer": "",
        "sources": [],
        "confidence": 0.0,
        "history": [],
        "workers_called": [],
        "supervisor_route": "",
        "latency_ms": None,
        "run_id": f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "worker_io_logs": [],
        "retrieval_top_k": 5,
    }


def supervisor_node(state: AgentState) -> AgentState:
    """Keyword routing — ưu tiên multi-hop (SLA + access), rồi policy, rồi retrieval."""
    task = state["task"]
    t = task.lower()

    state["history"].append(f"[supervisor] received task: {task[:120]}")

    # Multi-hop: incident / P1 + access / level / contractor
    mh_incident = any(
        k in t
        for k in (
            "p1",
            "sla",
            "2am",
            "sự cố",
            "khẩn cấp",
            "incident",
            "ticket",
            "notify",
            "stakeholder",
            "pagerduty",
        )
    )
    mh_access = any(
        k in t
        for k in (
            "level",
            "access",
            "contractor",
            "cấp quyền",
            "quyền",
            "admin access",
            "emergency fix",
            "khắc phục",
        )
    )
    multi_hop = mh_incident and mh_access

    info_q = bool(
        re.search(
            r"bao nhiêu ngày|bao lâu|mấy bước|sau bao nhiêu|lần đăng nhập|tài khoản bị khóa|remote tối đa|thử việc|probation",
            t,
        )
    )

    sla_ops = any(
        k in t
        for k in (
            "sla",
            "p1",
            "escalation",
            "pagerduty",
            "slack",
            "10 phút",
            "10 phut",
            "sự cố",
            "incident",
            "helpdesk",
            "faq",
        )
    )

    policy_strong = any(
        k in t
        for k in (
            "store credit",
            "flash sale",
            "license",
            "kỹ thuật số",
            "subscription",
            "31/01",
            "07/02",
            "trước 01/02",
            "được hoàn tiền không",
            "yêu cầu hoàn tiền ngày",
        )
    )

    policy_access = (
        ("level 3" in t or "level 2" in t or "level 1" in t or "level 4" in t)
        or ("cấp quyền" in t)
        or ("admin access" in t)
        or ("contractor" in t and any(x in t for x in ("access", "level", "quyền", "admin", "cấp")))
        or ("phê duyệt" in t and "level" in t)
    )

    if multi_hop:
        state["supervisor_route"] = "multi_hop"
        state["route_reason"] = (
            "multi-hop: task mentions incident/SLA/P1/ticket AND access/level/contractor — "
            "run retrieval then policy (+ MCP tools)"
        )
        state["needs_tool"] = True
        state["risk_high"] = "emergency" in t or "khẩn cấp" in t
        state["retrieval_top_k"] = 8
    elif sla_ops and not policy_strong:
        # SLA / IT ops trước nhánh info_q để không nhầm "P1 ... bao lâu?" sang informational-only
        state["supervisor_route"] = "retrieval_worker"
        state["route_reason"] = "SLA / P1 / IT ops keywords — retrieval + synthesis"
        state["needs_tool"] = False
        state["risk_high"] = False
        state["retrieval_top_k"] = 6
    elif policy_strong or policy_access:
        state["supervisor_route"] = "policy_tool_worker"
        state["route_reason"] = (
            "policy/access/refund exception keywords — policy_tool uses MCP search_kb (not direct Chroma)"
        )
        state["needs_tool"] = True
        state["risk_high"] = False
        state["retrieval_top_k"] = 5
    elif info_q and not policy_strong:
        state["supervisor_route"] = "retrieval_worker"
        state["route_reason"] = "informational question — dense retrieval + synthesis"
        state["needs_tool"] = False
        state["risk_high"] = False
        state["retrieval_top_k"] = 5
    elif "err-" in t or "err_" in t:
        state["supervisor_route"] = "retrieval_worker"
        state["route_reason"] = "error-code style question — retrieve; abstain if no doc match"
        state["needs_tool"] = False
        state["risk_high"] = False
        state["retrieval_top_k"] = 5
    else:
        state["supervisor_route"] = "retrieval_worker"
        state["route_reason"] = "default: retrieval_worker → synthesis"
        state["needs_tool"] = False
        state["risk_high"] = False
        state["retrieval_top_k"] = 5

    state["history"].append(
        f"[supervisor] route={state['supervisor_route']} reason={state['route_reason']}"
    )
    return state


def route_decision(state: AgentState) -> Literal[
    "retrieval_worker", "policy_tool_worker", "human_review", "multi_hop"
]:
    r = state.get("supervisor_route") or "retrieval_worker"
    if r in ("retrieval_worker", "policy_tool_worker", "human_review", "multi_hop"):
        return r  # type: ignore[return-value]
    return "retrieval_worker"


def human_review_node(state: AgentState) -> AgentState:
    state["hitl_triggered"] = True
    state["history"].append("[human_review] HITL placeholder — auto-continue in lab")
    state["workers_called"] = list(state.get("workers_called") or [])
    if "human_review" not in state["workers_called"]:
        state["workers_called"].append("human_review")
    return state


def _dedupe_workers_called(calls: list) -> list:
    seen = set()
    out = []
    for w in calls:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def build_graph():
    def run(state: AgentState) -> AgentState:
        t0 = time.time()
        state = supervisor_node(state)
        route = route_decision(state)

        if route == "human_review":
            state = human_review_node(state)
            state = retrieval_run(state)
            state = synthesis_run(state)
        elif route == "multi_hop":
            state = retrieval_run(state)
            state = policy_tool_run(state)
            state = synthesis_run(state)
        elif route == "policy_tool_worker":
            state = policy_tool_run(state)
            state = synthesis_run(state)
        else:
            state = retrieval_run(state)
            state = synthesis_run(state)

        state["workers_called"] = _dedupe_workers_called(state.get("workers_called") or [])
        state["latency_ms"] = int((time.time() - t0) * 1000)
        state["history"].append(f"[graph] completed in {state['latency_ms']}ms")
        return state

    return run


_graph = build_graph()


def run_graph(task: str) -> AgentState:
    state = make_initial_state(task)
    return _graph(state)


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{state['run_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(state), f, ensure_ascii=False, indent=2, default=str)
    return path


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print("=" * 60)
    print("Day 09 — Supervisor-Worker Graph (wired)")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
        "Ticket P1 lúc 2am. Cần cấp Level 2 access tạm thời cho contractor để emergency fix. Nêu cả SLA notify và quy trình cấp quyền.",
    ]

    for query in test_queries:
        print(f"\n>> Query: {query[:90]}...")
        result = run_graph(query)
        print(f"  Route   : {result['supervisor_route']}")
        print(f"  Reason  : {result['route_reason'][:100]}...")
        print(f"  Workers : {result['workers_called']}")
        print(f"  Answer  : {(result.get('final_answer') or '')[:160]}...")
        print(f"  Conf    : {result.get('confidence')}")
        print(f"  Latency : {result['latency_ms']}ms")
        print(f"  Trace   : {save_trace(result)}")

    print("\n[OK] graph.py smoke test done.")
