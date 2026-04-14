"""
graph.py - Supervisor orchestrator for Day 09 lab.

This file keeps the supervisor/setup layer compatible with the three worker
modules in workers/.
"""

import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from typing import Literal, Optional, TypedDict

try:
    from langgraph.graph import END, StateGraph
except Exception:
    END = "__end__"
    StateGraph = None

from workers.policy_tool import run as policy_tool_run
from workers.retrieval import run as retrieval_run
from workers.synthesis import run as synthesis_run


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class AgentState(TypedDict, total=False):
    # Shared state passed through supervisor, workers, and trace export.
    task: str
    question_type: str
    route_reason: str
    risk_high: bool
    needs_tool: bool
    hitl_triggered: bool
    retrieved_chunks: list
    retrieved_sources: list
    policy_result: dict
    mcp_tools_used: list
    mcp_tool_called: list
    mcp_result: list
    final_answer: str
    answer_schema_type: str
    answer_schema: dict
    sources: list
    confidence: float
    history: list
    workers_called: list
    worker_io_logs: list
    supervisor_route: str
    retrieval_top_k: int
    latency_ms: Optional[int]
    run_id: str
    timestamp: str


def _normalize(text: str) -> str:
    # Remove Vietnamese accents so keyword routing still works with plain ASCII input.
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.lower()


def make_initial_state(task: str) -> AgentState:
    # Every run starts from the same predictable state shape for easier tracing/debugging.
    now = datetime.now()
    return {
        "task": task,
        "question_type": "generic_lookup",
        "route_reason": "",
        "risk_high": False,
        "needs_tool": False,
        "hitl_triggered": False,
        "retrieved_chunks": [],
        "retrieved_sources": [],
        "policy_result": {},
        "mcp_tools_used": [],
        "mcp_tool_called": [],
        "mcp_result": [],
        "final_answer": "",
        "answer_schema_type": "generic_lookup",
        "answer_schema": {},
        "sources": [],
        "confidence": 0.0,
        "history": [f"Run started at {now.isoformat()}"],
        "workers_called": [],
        "worker_io_logs": [],
        "supervisor_route": "",
        "retrieval_top_k": 3,
        "latency_ms": None,
        "run_id": f"run_{now.strftime('%Y%m%d_%H%M%S_%f')}",
        "timestamp": now.isoformat(),
    }


def _infer_question_type(task_normalized: str) -> str:
    # Question types are coarse-grained task classes, not per-question hacks.
    def has_negated_phrase(phrase: str) -> bool:
        return any(
            marker in task_normalized
            for marker in [
                f"khong phai {phrase}",
                f"khong phai la {phrase}",
                f"not {phrase}",
            ]
        )

    if any(keyword in task_normalized for keyword in ["muc phat", "tai chinh cu the", "khong co trong tai lieu"]):
        return "abstain_missing_info"

    if any(keyword in task_normalized for keyword in ["cap quyen", "access", "level 2", "level 3", "level 4"]):
        if any(keyword in task_normalized for keyword in ["p1", "sla", "incident", "2am", "thong bao"]):
            return "access_sla_multi_hop"
        return "access_control"

    if any(keyword in task_normalized for keyword in ["hoan tien", "refund", "policy", "flash sale", "store credit"]):
        if re.search(r"\b\d{2}/\d{2}/\d{4}\b", task_normalized):
            return "policy_temporal_scope"
        if "store credit" in task_normalized:
            return "numeric_policy"
        if any(
            keyword in task_normalized and not has_negated_phrase(keyword)
            for keyword in ["flash sale", "license", "subscription", "ky thuat so", "kich hoat"]
        ):
            return "policy_exception"
        return "eligibility_policy"

    if any(keyword in task_normalized for keyword in ["probation", "remote", "duoc chap thuan khong", "dieu kien de duoc"]):
        return "eligibility_policy"

    if any(keyword in task_normalized for keyword in ["mat khau", "password"]):
        return "faq_multi_detail"

    if any(keyword in task_normalized for keyword in ["p1", "sla", "ticket", "escalation", "pagerduty", "incident"]):
        if any(keyword in task_normalized for keyword in ["ai nhan", "kenh nao", "deadline", "may gio"]):
            return "sla_detail"
        if any(keyword in task_normalized for keyword in ["lam gi tiep theo", "he thong se lam gi", "khong phan hoi sau"]):
            return "sla_action"
        return "sla_detail"

    return "generic_lookup"


def supervisor_node(state: AgentState) -> AgentState:
    # Supervisor only decides where the task should go next; workers do the actual work.
    task = state.get("task", "")
    task_normalized = _normalize(task)
    state.setdefault("history", [])
    state["history"].append(f"[supervisor] received task: {task[:80]}")

    refund_keywords = [
        "hoan tien",
        "refund",
        "flash sale",
        "license",
        "subscription",
        "digital product",
        "store credit",
        "policy",
    ]
    access_keywords = [
        "cap quyen",
        "access",
        "access level",
        "level 2",
        "level 3",
        "level 4",
        "admin access",
        "contractor",
    ]
    retrieval_keywords = [
        "p1",
        "sla",
        "ticket",
        "escalation",
        "incident",
        "pagerduty",
        "thong bao",
        "notify",
    ]
    risk_keywords = ["emergency", "khan cap", "critical", "p0", "p1", "2am", "ciso"]

    # Convert keyword hits into routing signals the graph can act on.
    has_refund_signal = any(keyword in task_normalized for keyword in refund_keywords)
    has_access_signal = any(keyword in task_normalized for keyword in access_keywords)
    has_retrieval_signal = any(keyword in task_normalized for keyword in retrieval_keywords)
    has_unknown_error_signal = "err-" in task_normalized
    risk_high = any(keyword in task_normalized for keyword in risk_keywords)

    route = "retrieval_worker"
    route_reasons = ["default retrieval for evidence gathering"]
    needs_tool = False

    if has_refund_signal or has_access_signal:
        route = "policy_tool_worker"
        route_reasons = []
        if has_refund_signal:
            route_reasons.append("refund/policy signal detected")
        if has_access_signal:
            route_reasons.append("access-control signal detected")
        if has_retrieval_signal:
            route_reasons.append("incident/SLA context also detected")
        needs_tool = True
        route_reasons.append("MCP lookup enabled for policy worker")
    elif has_retrieval_signal:
        route = "retrieval_worker"
        route_reasons = ["SLA/ticket/escalation signal detected"]
    elif has_unknown_error_signal:
        route = "human_review" if risk_high else "retrieval_worker"
        route_reasons = [
            "unknown error code with high-risk context" if risk_high else "unknown error code, retrieve evidence first"
        ]

    if risk_high and "risk_high flagged" not in route_reasons:
        route_reasons.append("risk_high flagged")

    route_reason = " | ".join(route_reasons)
    question_type = _infer_question_type(task_normalized)
    state["supervisor_route"] = route
    state["question_type"] = question_type
    state["route_reason"] = route_reason
    state["risk_high"] = risk_high
    state["needs_tool"] = needs_tool
    state["history"].append(
        f"[supervisor] route={route} question_type={question_type} needs_tool={needs_tool} "
        f"risk_high={risk_high} reason={route_reason}"
    )
    return state


def route_decision(state: AgentState) -> Literal["retrieval", "policy", "human"]:
    # LangGraph edge labels are intentionally short; they map from the verbose worker route above.
    route = state.get("supervisor_route")
    if route == "human_review":
        return "human"
    if route == "policy_tool_worker":
        return "policy"
    return "retrieval"


def human_review_node(state: AgentState) -> AgentState:
    """
    HITL node: pause và chờ human approval.
    Trong lab này, implement dưới dạng placeholder (in ra warning).

    TODO Sprint 3 (optional): Implement actual HITL với interrupt_before hoặc
    breakpoint nếu dùng LangGraph.
    """
    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["hitl_triggered"] = True
    state["workers_called"].append("human_review")
    state["history"].append("[human_review] lab placeholder approved, continuing to retrieval")
    return state


def retrieval_worker_node(state: AgentState) -> AgentState:
    # Thin wrapper keeps graph wiring readable and lets the worker stay independently testable.
    return retrieval_run(state)


def policy_tool_worker_node(state: AgentState) -> AgentState:
    # Policy worker is responsible for MCP/tool-assisted checks and exceptions.
    return policy_tool_run(state)


def synthesis_worker_node(state: AgentState) -> AgentState:
    # Final worker turns collected evidence into the answer shown to the user.
    return synthesis_run(state)


class _FallbackApp:
    def invoke(self, state: AgentState) -> AgentState:
        # Simple pure-Python execution path when LangGraph is unavailable.
        state = supervisor_node(state)
        route = route_decision(state)

        if route == "human":
            state = human_review_node(state)
            state = retrieval_worker_node(state)
        elif route == "policy":
            state = policy_tool_worker_node(state)
        else:
            state = retrieval_worker_node(state)

        return synthesis_worker_node(state)


def build_graph():
    if StateGraph is None:
        return _FallbackApp()

    # Graph shape:
    # supervisor -> retrieval/policy/human -> synthesis -> END
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("retrieval", retrieval_worker_node)
    workflow.add_node("policy", policy_tool_worker_node)
    workflow.add_node("human", human_review_node)
    workflow.add_node("synthesis", synthesis_worker_node)

    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_decision,
        {
            "human": "human",
            "policy": "policy",
            "retrieval": "retrieval",
        },
    )
    workflow.add_edge("human", "retrieval")
    workflow.add_edge("retrieval", "synthesis")
    workflow.add_edge("policy", "synthesis")
    workflow.add_edge("synthesis", END)
    return workflow.compile()


_app = build_graph()


def run_graph(task: str) -> AgentState:
    # Measure end-to-end latency around the whole orchestration run.
    start_time = time.time()
    state = make_initial_state(task)
    final_state = _app.invoke(state)
    final_state["latency_ms"] = int((time.time() - start_time) * 1000)
    return final_state


def save_trace(state: AgentState, output_dir: Optional[str] = None) -> str:
    # Persist the full final state so reports can inspect routing, worker IO, and answer quality later.
    trace_dir = output_dir or os.path.join(BASE_DIR, "artifacts", "traces")
    os.makedirs(trace_dir, exist_ok=True)
    filename = os.path.join(trace_dir, f"{state['run_id']}.json")
    with open(filename, "w", encoding="utf-8") as file_obj:
        json.dump(state, file_obj, ensure_ascii=False, indent=2)
    return filename


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("=" * 60)
    print("Day 09 Lab - Supervisor-Worker Graph")
    print("=" * 60)

    test_queries = [
        "SLA xu ly ticket P1 la bao lau?",
        "Khach hang Flash Sale yeu cau hoan tien vi san pham loi - duoc khong?",
        "Can cap quyen Level 3 de khac phuc P1 khan cap. Quy trinh la gi?",
    ]

    for query in test_queries:
        print(f"\n> Query: {query}")
        result = run_graph(query)
        print(f"  Route      : {result['supervisor_route']}")
        print(f"  Reason     : {result['route_reason']}")
        print(f"  Workers    : {result['workers_called']}")
        print(f"  Confidence : {result['confidence']}")
        print(f"  Latency    : {result['latency_ms']}ms")
        print(f"  Answer     : {result['final_answer'][:120]}...")
        trace_file = save_trace(result)
        print(f"  Trace saved: {trace_file}")

    print("\nDone: graph.py wiring is compatible with the current workers.")
