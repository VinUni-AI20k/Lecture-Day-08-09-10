"""
graph.py — Supervisor Orchestrator
Input -> Supervisor -> [retrieval_worker | policy_tool_worker | human_review] -> synthesis -> Output
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Literal, Optional, TypedDict

from workers.policy_tool import run as policy_tool_run
from workers.retrieval import run as retrieval_run
from workers.synthesis import run as synthesis_run


class AgentState(TypedDict):
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
    }


def supervisor_node(state: AgentState) -> AgentState:
    task = state["task"].lower()
    state["history"].append(f"[supervisor] received task: {state['task'][:80]}")

    route = "retrieval_worker"
    route_reason = "default -> retrieval_worker"
    needs_tool = False
    risk_high = False

    retrieval_keywords = ["p1", "sla", "ticket", "escalation", "sự cố", "incident"]
    policy_keywords = [
        "hoàn tiền", "refund", "flash sale", "license", "subscription",
        "cấp quyền", "access", "level 2", "level 3", "quyền truy cập",
    ]
    risk_keywords = ["emergency", "khẩn cấp", "2am", "không rõ", "err-"]

    has_retrieval_signal = any(kw in task for kw in retrieval_keywords)
    has_policy_signal = any(kw in task for kw in policy_keywords)

    if has_policy_signal:
        route = "policy_tool_worker"
        route_reason = "task contains policy/access keyword -> policy_tool_worker + MCP allowed"
        needs_tool = True
        if has_retrieval_signal:
            route_reason += " | multi-hop retrieval+policy"
    elif has_retrieval_signal:
        route = "retrieval_worker"
        route_reason = "task contains retrieval keyword (P1/SLA/ticket/escalation)"

    if any(kw in task for kw in risk_keywords):
        risk_high = True
        route_reason += " | risk_high flagged"

    if "err-" in task and risk_high:
        route = "human_review"
        route_reason = "unknown error code + risk_high -> human_review"
        needs_tool = False

    state["supervisor_route"] = route
    state["route_reason"] = route_reason
    state["needs_tool"] = needs_tool
    state["risk_high"] = risk_high
    state["history"].append(f"[supervisor] route={route} reason={route_reason}")
    return state


def route_decision(state: AgentState) -> Literal["retrieval_worker", "policy_tool_worker", "human_review"]:
    route = state.get("supervisor_route", "retrieval_worker")
    return route  # type: ignore


def human_review_node(state: AgentState) -> AgentState:
    state["hitl_triggered"] = True
    state["workers_called"].append("human_review")
    state["history"].append("[human_review] HITL triggered; auto-approve in lab mode")
    state["supervisor_route"] = "retrieval_worker"
    state["route_reason"] += " | human approved -> retrieval"
    return state


def retrieval_worker_node(state: AgentState) -> AgentState:
    return retrieval_run(state)


def policy_tool_worker_node(state: AgentState) -> AgentState:
    return policy_tool_run(state)


def synthesis_worker_node(state: AgentState) -> AgentState:
    return synthesis_run(state)


def build_graph():
    def run(state: AgentState) -> AgentState:
        start = time.time()
        state = supervisor_node(state)
        route = route_decision(state)

        if route == "human_review":
            state = human_review_node(state)
            state = retrieval_worker_node(state)
        elif route == "policy_tool_worker":
            task_lower = state.get("task", "").lower()
            retrieval_keywords = ["p1", "sla", "ticket", "escalation", "sự cố", "incident"]
            needs_retrieval_first = any(kw in task_lower for kw in retrieval_keywords)

            # Multi-hop case: lấy evidence retrieval trước để policy + synthesis có đủ 2 domain.
            if needs_retrieval_first:
                state = retrieval_worker_node(state)
                state["history"].append("[graph] multi-hop: retrieval before policy")

            state = policy_tool_worker_node(state)
            if not state.get("retrieved_chunks"):
                state = retrieval_worker_node(state)
        else:
            state = retrieval_worker_node(state)

        state = synthesis_worker_node(state)
        state["latency_ms"] = int((time.time() - start) * 1000)
        state["history"].append(f"[graph] completed in {state['latency_ms']}ms")
        return state

    return run


_graph = build_graph()


def run_graph(task: str) -> AgentState:
    state = make_initial_state(task)
    return _graph(state)


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{state['run_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return filename


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 60)
    print("Day 09 Lab — Supervisor-Worker Graph")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
        "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?",
    ]

    for query in test_queries:
        print(f"\n> Query: {query}")
        result = run_graph(query)
        print(f"  Route   : {result['supervisor_route']}")
        print(f"  Reason  : {result['route_reason']}")
        print(f"  Workers : {result['workers_called']}")
        print(f"  Answer  : {result['final_answer'][:100]}...")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Latency : {result['latency_ms']}ms")
        print(f"  Trace saved -> {save_trace(result)}")

    print("\n[OK] graph.py test complete.")
