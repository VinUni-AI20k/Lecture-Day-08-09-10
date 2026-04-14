"""
graph.py — Day 09 Supervisor-Worker Orchestrator (LangGraph)

Mục tiêu:
- Supervisor route request vào đúng worker
- Worker xử lý độc lập theo contract
- Synthesis trả lời grounded
- Supervisor audit log: MCP có được dùng hay không
"""

from __future__ import annotations

import json
import os
import re
import time
from copy import deepcopy
from datetime import datetime
from typing import Any, Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph

from workers.policy_tool import run as policy_tool_run
from workers.retrieval import run as retrieval_run
from workers.synthesis import run as synthesis_run


class AgentState(TypedDict):
    # Input
    task: str

    # Supervisor
    route_reason: str
    risk_high: bool
    needs_tool: bool
    hitl_triggered: bool
    supervisor_route: str

    # Worker outputs
    retrieved_chunks: list
    retrieved_sources: list
    policy_result: dict
    mcp_tools_used: list
    worker_io_logs: list

    # Final output
    final_answer: str
    sources: list
    confidence: float

    # Trace
    history: list
    workers_called: list
    latency_ms: Optional[int]
    run_id: str
    timestamp: str
    run_started_at: float


RETRIEVAL_KEYWORDS = (
    "p1",
    "sla",
    "ticket",
    "escalation",
    "incident",
    "sự cố",
    "outage",
)

ACCESS_POLICY_KEYWORDS = (
    "cấp quyền",
    "access",
    "admin access",
    "level 1",
    "level 2",
    "level 3",
    "permission",
    "phê duyệt",
    "approver",
    "contractor",
)

REFUND_POLICY_KEYWORDS = (
    "refund",
    "hoàn tiền",
    "flash sale",
    "license",
    "digital",
    "activated",
    "subscription",
    "store credit",
)

POLICY_KEYWORDS = tuple(dict.fromkeys((*ACCESS_POLICY_KEYWORDS, *REFUND_POLICY_KEYWORDS)))

RISK_KEYWORDS = (
    "emergency",
    "khẩn cấp",
    "2am",
    "2 am",
    "ngoài giờ",
    "after hours",
    "critical",
    "sev1",
)

ERROR_PATTERN = re.compile(r"\b(?:err[-_ ]?[a-z0-9]+)\b", re.IGNORECASE)


def _is_simple_refund_fact_query(task_lower: str, matched_refund: list[str]) -> bool:
    """
    Route simple refund fact-lookup queries to retrieval_worker.
    Example: "hoàn tiền trong bao nhiêu ngày?"
    """
    if not matched_refund:
        return False

    has_time_or_amount_ask = any(
        token in task_lower
        for token in ("bao nhiêu", "bao lâu", "mấy", "trong bao", "trong vòng", "bao ngày")
    )
    if not has_time_or_amount_ask:
        return False

    strong_policy_markers = (
        "flash sale",
        "license",
        "digital",
        "subscription",
        "activated",
        "store credit",
        "ngoại lệ",
        "exception",
        "level 1",
        "level 2",
        "level 3",
        "access",
        "cấp quyền",
    )
    return not any(marker in task_lower for marker in strong_policy_markers)


def _new_run_id() -> str:
    return f"run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


def _ensure_defaults(state: dict[str, Any]) -> None:
    state.setdefault("task", "")
    state.setdefault("route_reason", "")
    state.setdefault("risk_high", False)
    state.setdefault("needs_tool", False)
    state.setdefault("hitl_triggered", False)
    state.setdefault("supervisor_route", "")

    state.setdefault("retrieved_chunks", [])
    state.setdefault("retrieved_sources", [])
    state.setdefault("policy_result", {})
    state.setdefault("mcp_tools_used", [])
    state.setdefault("worker_io_logs", [])

    state.setdefault("final_answer", "")
    state.setdefault("sources", [])
    state.setdefault("confidence", 0.0)

    state.setdefault("history", [])
    state.setdefault("workers_called", [])
    state.setdefault("latency_ms", None)
    state.setdefault("run_id", _new_run_id())
    state.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
    state.setdefault("run_started_at", time.time())


def _hits(text: str, keywords: tuple[str, ...]) -> list[str]:
    lower = text.lower()
    return [keyword for keyword in keywords if keyword in lower]


def make_initial_state(task: str) -> AgentState:
    state: dict[str, Any] = {
        "task": task,
        "route_reason": "",
        "risk_high": False,
        "needs_tool": False,
        "hitl_triggered": False,
        "supervisor_route": "",
        "retrieved_chunks": [],
        "retrieved_sources": [],
        "policy_result": {},
        "mcp_tools_used": [],
        "worker_io_logs": [],
        "final_answer": "",
        "sources": [],
        "confidence": 0.0,
        "history": [],
        "workers_called": [],
        "latency_ms": None,
        "run_id": _new_run_id(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "run_started_at": time.time(),
    }
    return state  # type: ignore[return-value]


def supervisor_node(state: AgentState) -> AgentState:
    state = deepcopy(state)
    _ensure_defaults(state)

    task = state["task"]
    task_lower = task.lower()
    state["history"].append(f"[supervisor] received task: {task[:120]}")

    matched_retrieval = _hits(task, RETRIEVAL_KEYWORDS)
    matched_policy = _hits(task, POLICY_KEYWORDS)
    matched_access_policy = _hits(task, ACCESS_POLICY_KEYWORDS)
    matched_refund_policy = _hits(task, REFUND_POLICY_KEYWORDS)
    matched_risk = _hits(task, RISK_KEYWORDS)
    error_codes = ERROR_PATTERN.findall(task_lower)
    ambiguous_error = bool(error_codes) or (
        "mã lỗi" in task_lower and any(token in task_lower for token in ("không rõ", "unknown", "chưa rõ"))
    )
    simple_refund_fact = _is_simple_refund_fact_query(task_lower, matched_refund_policy)

    risk_high = bool(matched_risk)

    if ambiguous_error and risk_high:
        route = "human_review"
        needs_tool = False
        route_reason = (
            f"ambiguous error code detected in high-risk context ({', '.join(error_codes) if error_codes else 'mã lỗi không rõ'}); "
            "human review required; needs_tool=False; mcp_expected=False"
        )
    elif ambiguous_error:
        route = "retrieval_worker"
        needs_tool = False
        route_reason = (
            f"ambiguous error code detected ({', '.join(error_codes) if error_codes else 'mã lỗi không rõ'}); "
            "route retrieval first for grounded abstain/lookup; needs_tool=False; mcp_expected=False"
        )
    elif matched_access_policy:
        route = "policy_tool_worker"
        needs_tool = True
        if matched_retrieval:
            route_reason = (
                f"access-control keywords matched ({', '.join(matched_access_policy)}); "
                f"incident/SLA keywords also present ({', '.join(matched_retrieval)}), policy is prioritized for multi-hop; "
                "needs_tool=True; mcp_expected=True"
            )
        else:
            route_reason = (
                f"access-control keywords matched ({', '.join(matched_access_policy)}); "
                "needs_tool=True; mcp_expected=True"
            )
    elif matched_refund_policy and not simple_refund_fact:
        route = "policy_tool_worker"
        needs_tool = True
        route_reason = (
            f"refund/policy keywords matched ({', '.join(matched_refund_policy)}); "
            "needs_tool=True; mcp_expected=True"
        )
    elif simple_refund_fact:
        route = "retrieval_worker"
        needs_tool = False
        route_reason = (
            f"simple refund fact query detected ({', '.join(matched_refund_policy)} + quantity/time ask); "
            "retrieval-first for direct lookup; needs_tool=False; mcp_expected=False"
        )
    elif matched_retrieval:
        route = "retrieval_worker"
        needs_tool = False
        if matched_policy:
            route_reason = (
                f"incident/SLA keywords matched ({', '.join(matched_retrieval)}); "
                f"policy keywords also present ({', '.join(matched_policy)}), but retrieval is prioritized; "
                "needs_tool=False; mcp_expected=False"
            )
        else:
            route_reason = (
                f"incident/SLA keywords matched ({', '.join(matched_retrieval)}); "
                "needs_tool=False; mcp_expected=False"
            )
    elif matched_policy:
        route = "policy_tool_worker"
        needs_tool = True
        route_reason = (
            f"policy/access keywords matched ({', '.join(matched_policy)}); "
            "needs_tool=True; mcp_expected=True"
        )
    else:
        route = "retrieval_worker"
        needs_tool = False
        route_reason = "no policy/access or error-code signals; default retrieval; needs_tool=False; mcp_expected=False"

    if risk_high:
        route_reason = f"{route_reason} | risk_high=True due to {', '.join(matched_risk) or 'ambiguous error'}"

    state["supervisor_route"] = route
    state["route_reason"] = route_reason
    state["needs_tool"] = needs_tool
    state["risk_high"] = risk_high
    state["history"].append(f"[supervisor] route={route} reason={route_reason}")
    return state


def route_decision(state: AgentState) -> Literal["retrieval_worker", "policy_tool_worker", "human_review"]:
    route = state.get("supervisor_route") or "retrieval_worker"
    if route not in {"retrieval_worker", "policy_tool_worker", "human_review"}:
        return "retrieval_worker"
    return route  # type: ignore[return-value]


def human_review_node(state: AgentState) -> AgentState:
    state = deepcopy(state)
    _ensure_defaults(state)
    state["hitl_triggered"] = True
    state["workers_called"].append("human_review")
    state["history"].append("[human_review] HITL triggered — awaiting human review")
    return state


def retrieval_worker_node(state: AgentState) -> AgentState:
    state = deepcopy(state)
    _ensure_defaults(state)
    return retrieval_run(state)


def policy_tool_worker_node(state: AgentState) -> AgentState:
    state = deepcopy(state)
    _ensure_defaults(state)
    return policy_tool_run(state)


def synthesis_worker_node(state: AgentState) -> AgentState:
    state = deepcopy(state)
    _ensure_defaults(state)
    return synthesis_run(state)


def supervisor_audit_node(state: AgentState) -> AgentState:
    state = deepcopy(state)
    _ensure_defaults(state)

    mcp_used = len(state.get("mcp_tools_used", [])) > 0
    total_latency = int(max(0.0, (time.time() - float(state.get("run_started_at", time.time()))) * 1000))

    state["latency_ms"] = total_latency
    state["history"].append(f"[supervisor] mcp_used={mcp_used} calls={len(state.get('mcp_tools_used', []))}")
    state["history"].append(f"[graph] completed in {total_latency}ms")
    state["route_reason"] = f"{state.get('route_reason', '')} | mcp_used={mcp_used}".strip()
    return state


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("retrieval_worker", retrieval_worker_node)
    workflow.add_node("policy_tool_worker", policy_tool_worker_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("synthesis_worker", synthesis_worker_node)
    workflow.add_node("supervisor_audit", supervisor_audit_node)

    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_decision,
        {
            "retrieval_worker": "retrieval_worker",
            "policy_tool_worker": "policy_tool_worker",
            "human_review": "human_review",
        },
    )

    workflow.add_edge("retrieval_worker", "synthesis_worker")
    workflow.add_edge("policy_tool_worker", "synthesis_worker")
    workflow.add_edge("human_review", "synthesis_worker")
    workflow.add_edge("synthesis_worker", "supervisor_audit")
    workflow.add_edge("supervisor_audit", END)

    return workflow.compile()


graph = build_graph()
_graph = graph


def run_graph(task: str) -> AgentState:
    state = make_initial_state(task)
    return graph.invoke(state)


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{state['run_id']}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return filename


if __name__ == "__main__":
    print("=" * 60)
    print("Day 09 Lab — Supervisor-Worker Graph")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
        "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run_graph(query)
        print(f"  Route      : {result['supervisor_route']}")
        print(f"  Reason     : {result['route_reason']}")
        print(f"  Workers    : {result['workers_called']}")
        print(f"  Confidence : {result['confidence']}")
        print(f"  Latency    : {result['latency_ms']}ms")

        trace_file = save_trace(result)
        print(f"  Trace saved → {trace_file}")

    print("\n✅ graph.py demo complete.")
