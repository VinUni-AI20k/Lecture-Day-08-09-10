"""
graph.py — Supervisor Orchestrator
Sprint 1: Implement AgentState, supervisor_node, route_decision và kết nối graph.

Kiến trúc:
    Input → Supervisor → [retrieval_worker | policy_tool_worker | human_review] → synthesis → Output

Chạy thử:
    python graph.py
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Literal, Optional, TypedDict

try:
    from langgraph.graph import END, StateGraph
    LANGGRAPH_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - phụ thuộc env cài package
    END = "__END__"  # type: ignore[assignment]
    StateGraph = None  # type: ignore[assignment]
    LANGGRAPH_IMPORT_ERROR = exc

from workers.policy_tool import run as policy_tool_run
from workers.retrieval import run as retrieval_run
from workers.synthesis import run as synthesis_run


# ─────────────────────────────────────────────
# 1. Shared State — dữ liệu đi xuyên toàn graph
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    # Input
    task: str                           # Câu hỏi đầu vào từ user

    # Supervisor decisions
    route_reason: str                   # Lý do route sang worker nào
    risk_high: bool                     # True → cần HITL hoặc human_review
    needs_tool: bool                    # True → cần gọi external tool qua MCP
    hitl_triggered: bool                # True → đã pause cho human review

    # Worker outputs
    retrieved_chunks: list              # Output từ retrieval_worker
    retrieved_sources: list             # Danh sách nguồn tài liệu
    policy_result: dict                 # Output từ policy_tool_worker
    mcp_tools_used: list                # Danh sách MCP tools đã gọi
    worker_io_logs: list                # Log IO của từng worker
    error: Optional[dict]               # Lỗi pipeline nếu có

    # Final output
    final_answer: str                   # Câu trả lời tổng hợp
    sources: list                       # Sources được cite
    confidence: float                   # Mức độ tin cậy (0.0 - 1.0)

    # Trace & history
    history: list                       # Lịch sử các bước đã qua
    workers_called: list                # Danh sách workers đã được gọi
    supervisor_route: str               # Worker được chọn bởi supervisor
    latency_ms: Optional[int]           # Thời gian xử lý (ms)
    run_id: str                         # ID của run này


def make_initial_state(task: str) -> AgentState:
    """Khởi tạo state cho một run mới."""
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
        "worker_io_logs": [],
        "error": None,
        "final_answer": "",
        "sources": [],
        "confidence": 0.0,
        "history": [],
        "workers_called": [],
        "supervisor_route": "",
        "latency_ms": None,
        "run_id": f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    }


# ─────────────────────────────────────────────
# 2. Supervisor Node — quyết định route
# ─────────────────────────────────────────────

def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor phân tích task và quyết định:
    1. Route sang worker nào
    2. Có cần MCP tool không
    3. Có risk cao cần HITL không
    """
    task_lower = state["task"].lower()
    state["history"].append(f"[supervisor] received task: {state['task'][:120]}")

    policy_keywords = [
        "hoàn tiền", "refund", "flash sale", "license", "subscription",
        "cấp quyền", "access", "level 3", "level 4", "contractor",
        "admin access", "approval", "quy trình", "security",
    ]
    incident_keywords = [
        "p1", "sla", "ticket", "escalation", "incident", "on-call",
        "sự cố", "hotline", "pagerduty",
    ]
    human_review_keywords = ["err-"]
    risk_keywords = ["err-", "emergency", "khẩn cấp", "2am", "ngoài giờ"]

    matched_policy = [kw for kw in policy_keywords if kw in task_lower]
    matched_incident = [kw for kw in incident_keywords if kw in task_lower]
    matched_human = [kw for kw in human_review_keywords if kw in task_lower]
    matched_risk = [kw for kw in risk_keywords if kw in task_lower]

    risk_high = bool(matched_risk)
    needs_tool = bool(matched_policy) or any(kw in task_lower for kw in ["ticket", "p1", "jira"])

    if matched_human:
        route = "human_review"
        route_reason = f"matched high-risk unknown error keywords: {', '.join(matched_human)}"
    elif matched_policy:
        route = "policy_tool_worker"
        route_reason = f"matched policy/access keywords: {', '.join(matched_policy[:4])}"
        if matched_incident:
            route_reason += f" | also saw incident keywords: {', '.join(matched_incident[:3])}"
    elif matched_incident:
        route = "retrieval_worker"
        route_reason = f"matched incident/SLA keywords: {', '.join(matched_incident[:4])}"
    else:
        route = "retrieval_worker"
        route_reason = "no explicit policy/error keyword → fallback retrieval"

    if risk_high and route != "human_review":
        route_reason += f" | risk_high via: {', '.join(matched_risk[:3])}"

    state["supervisor_route"] = route
    state["route_reason"] = route_reason
    state["needs_tool"] = needs_tool
    state["risk_high"] = risk_high
    state["history"].append(f"[supervisor] route={route} reason={route_reason}")
    return state


# ─────────────────────────────────────────────
# 3. Route Decision — conditional edge
# ─────────────────────────────────────────────

def route_decision(state: AgentState) -> Literal["retrieval_worker", "policy_tool_worker", "human_review"]:
    """
    Trả về tên worker tiếp theo dựa vào supervisor_route trong state.
    Đây là conditional edge của graph.
    """
    route = state.get("supervisor_route", "retrieval_worker")
    if route not in {"retrieval_worker", "policy_tool_worker", "human_review"}:
        return "retrieval_worker"
    return route  # type: ignore[return-value]


# ─────────────────────────────────────────────
# 4. Human Review Node — HITL placeholder
# ─────────────────────────────────────────────

def human_review_node(state: AgentState) -> AgentState:
    """
    HITL node: placeholder auto-approve để pipeline tiếp tục.
    """
    state["hitl_triggered"] = True
    state["workers_called"].append("human_review")
    state["history"].append("[human_review] HITL triggered — awaiting human input")

    print(f"\n⚠️  HITL TRIGGERED")
    print(f"   Task: {state['task']}")
    print(f"   Reason: {state['route_reason']}")
    print("   Action: Auto-approving in lab mode\n")

    state["supervisor_route"] = "retrieval_worker"
    state["route_reason"] += " | human approved → retrieval"
    return state


# ─────────────────────────────────────────────
# 5. Worker Node Wrappers
# ─────────────────────────────────────────────

def _record_node_error(state: AgentState, worker_name: str, code: str, exc: Exception) -> AgentState:
    state["error"] = {"worker": worker_name, "code": code, "reason": str(exc)}
    state["history"].append(f"[{worker_name}] ERROR: {exc}")

    if worker_name == "synthesis_worker":
        state["final_answer"] = "Không đủ thông tin trong tài liệu nội bộ."
        state["sources"] = state.get("retrieved_sources", [])
        state["confidence"] = 0.0

    return state


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi retrieval worker thật."""
    state["history"].append("[graph] dispatch -> retrieval_worker")
    try:
        return retrieval_run(state)
    except Exception as exc:
        return _record_node_error(state, "retrieval_worker", "RETRIEVAL_FAILED", exc)


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker thật."""
    state["history"].append("[graph] dispatch -> policy_tool_worker")
    try:
        return policy_tool_run(state)
    except Exception as exc:
        return _record_node_error(state, "policy_tool_worker", "POLICY_CHECK_FAILED", exc)


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker thật."""
    state["history"].append("[graph] dispatch -> synthesis_worker")
    try:
        return synthesis_run(state)
    except Exception as exc:
        return _record_node_error(state, "synthesis_worker", "SYNTHESIS_FAILED", exc)


# ─────────────────────────────────────────────
# 6. Build Graph
# ─────────────────────────────────────────────

def build_graph():
    """
    Xây dựng graph với LangGraph StateGraph.
    """
    if StateGraph is None:
        raise RuntimeError(
            "LangGraph chưa được cài. Hãy chạy `pip install -r requirements.txt` trong day09/lab."
        ) from LANGGRAPH_IMPORT_ERROR

    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("retrieval_worker", retrieval_worker_node)
    workflow.add_node("policy_tool_worker", policy_tool_worker_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("synthesis_worker", synthesis_worker_node)

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
    workflow.add_edge("human_review", "retrieval_worker")
    workflow.add_edge("synthesis_worker", END)

    return workflow.compile()


# ─────────────────────────────────────────────
# 7. Public API
# ─────────────────────────────────────────────

try:
    _graph = build_graph()
except RuntimeError:
    _graph = None


def run_graph(task: str) -> AgentState:
    """
    Entry point: nhận câu hỏi, trả về AgentState với full trace.
    """
    global _graph
    if _graph is None:
        _graph = build_graph()

    state = make_initial_state(task)
    start = time.time()
    result = _graph.invoke(state)
    result["latency_ms"] = int((time.time() - start) * 1000)
    result["history"].append(f"[graph] completed in {result['latency_ms']}ms")
    return result


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
    """Lưu trace ra file JSON."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{state['run_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return filename


# ─────────────────────────────────────────────
# 8. Manual Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Day 09 Lab — Supervisor-Worker Graph")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
        "ERR-403-AUTH là lỗi gì?",
    ]

    try:
        for query in test_queries:
            print(f"\n▶ Query: {query}")
            result = run_graph(query)
            print(f"  Route      : {result['supervisor_route']}")
            print(f"  Reason     : {result['route_reason']}")
            print(f"  Workers    : {result['workers_called']}")
            print(f"  Answer     : {result['final_answer'][:120]}...")
            print(f"  Confidence : {result['confidence']}")
            print(f"  Latency    : {result['latency_ms']}ms")

            trace_file = save_trace(result)
            print(f"  Trace saved → {trace_file}")
    except RuntimeError as exc:
        print(f"❌ {exc}")

    print("\n✅ graph.py test complete.")
