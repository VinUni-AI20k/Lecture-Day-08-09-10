"""
graph.py — Supervisor Orchestrator
<<<<<<< HEAD
Sprint 1: Implement AgentState, supervisor_node, route_decision và kết nối graph.

Kiến trúc:
    Input → Supervisor → [retrieval_worker | policy_tool_worker | human_review] → synthesis → Output

Chạy thử:
    python graph.py
=======
Input -> Supervisor -> [retrieval_worker | policy_tool_worker | human_review] -> synthesis -> Output
>>>>>>> NhatVi
"""

import json
import os
<<<<<<< HEAD
import re
from datetime import datetime
from typing import TypedDict, Literal, Optional

# Uncomment nếu dùng LangGraph:
# from langgraph.graph import StateGraph, END

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
=======
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
>>>>>>> NhatVi
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


<<<<<<< HEAD
# ─────────────────────────────────────────────
# 2. Supervisor Node — quyết định route
# ─────────────────────────────────────────────

def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor phân tích task và quyết định:
    1. Route sang worker nào
    2. Có cần MCP tool không
    3. Có risk cao cần HITL không

    TODO Sprint 1: Implement routing logic dựa vào task keywords.
    """
    task = state["task"].lower()
    state["history"].append(f"[supervisor] received task: {state['task'][:80]}")

    # --- TODO: Implement routing logic ---
    # Gợi ý:
    # - "hoàn tiền", "refund", "flash sale", "license" → policy_tool_worker
    # - "cấp quyền", "access level", "level 3", "emergency" → policy_tool_worker
    # - "P1", "escalation", "sla", "ticket" → retrieval_worker
    # - mã lỗi không rõ (ERR-XXX), không đủ context → human_review
    # - còn lại → retrieval_worker

    route = "retrieval_worker"         # TODO: thay bằng logic thực
    route_reason = "default route"    # TODO: thay bằng lý do thực
    needs_tool = False
    risk_high = False

    # Ví dụ routing cơ bản — nhóm phát triển thêm:
    policy_keywords = ["hoàn tiền", "refund", "flash sale", "license", "cấp quyền", "access", "level 3"]
    risk_keywords = ["emergency", "khẩn cấp", "2am", "không rõ"]
    has_error_code = bool(re.search(r'err-\d+', task))

    if any(kw in task for kw in policy_keywords):
        route = "policy_tool_worker"
        route_reason = "task contains policy/access keyword"
        needs_tool = True

    if any(kw in task for kw in risk_keywords) or has_error_code:
        risk_high = True
        route_reason += " | risk_high flagged"

    # Human review override: unknown ERR-\d+ code → human review
    if has_error_code:
        route = "human_review"
        route_reason = "unknown error code (ERR-\\d+) + risk_high → human review"

    # Append MCP signal so route_reason is self-documenting in grading log
    if needs_tool:
        route_reason += " | MCP tools planned"
=======
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
>>>>>>> NhatVi

    state["supervisor_route"] = route
    state["route_reason"] = route_reason
    state["needs_tool"] = needs_tool
    state["risk_high"] = risk_high
    state["history"].append(f"[supervisor] route={route} reason={route_reason}")
<<<<<<< HEAD

    return state


# ─────────────────────────────────────────────
# 3. Route Decision — conditional edge
# ─────────────────────────────────────────────

def route_decision(state: AgentState) -> Literal["retrieval_worker", "policy_tool_worker", "human_review"]:
    """
    Trả về tên worker tiếp theo dựa vào supervisor_route trong state.
    Đây là conditional edge của graph.
    """
=======
    return state


def route_decision(state: AgentState) -> Literal["retrieval_worker", "policy_tool_worker", "human_review"]:
>>>>>>> NhatVi
    route = state.get("supervisor_route", "retrieval_worker")
    return route  # type: ignore


<<<<<<< HEAD
# ─────────────────────────────────────────────
# 4. Human Review Node — HITL placeholder
# ─────────────────────────────────────────────

def human_review_node(state: AgentState) -> AgentState:
    """
    HITL node: pause và chờ human approval.
    Trong lab này, implement dưới dạng placeholder (in ra warning).

    TODO Sprint 3 (optional): Implement actual HITL với interrupt_before hoặc
    breakpoint nếu dùng LangGraph.
    """
    state["hitl_triggered"] = True
    state["history"].append("[human_review] HITL triggered — awaiting human input")
    state["workers_called"].append("human_review")

    # Placeholder: tự động approve để pipeline tiếp tục
    print(f"\n⚠️  HITL TRIGGERED")
    print(f"   Task: {state['task']}")
    print(f"   Reason: {state['route_reason']}")
    print(f"   Action: Auto-approving in lab mode (set hitl_triggered=True)\n")

    # Sau khi human approve, route về retrieval để lấy evidence
    state["supervisor_route"] = "retrieval_worker"
    state["route_reason"] += " | human approved → retrieval"

    return state


# ─────────────────────────────────────────────
# 5. Import Workers
# ─────────────────────────────────────────────

from workers.retrieval import run as retrieval_run
from workers.policy_tool import run as policy_tool_run
from workers.synthesis import run as synthesis_run


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi retrieval worker (hybrid dense+BM25 via RRF)."""
=======
def human_review_node(state: AgentState) -> AgentState:
    state["hitl_triggered"] = True
    state["workers_called"].append("human_review")
    state["history"].append("[human_review] HITL triggered; auto-approve in lab mode")
    state["supervisor_route"] = "retrieval_worker"
    state["route_reason"] += " | human approved -> retrieval"
    return state


def retrieval_worker_node(state: AgentState) -> AgentState:
>>>>>>> NhatVi
    return retrieval_run(state)


def policy_tool_worker_node(state: AgentState) -> AgentState:
<<<<<<< HEAD
    """Wrapper gọi policy/tool worker (rule-based exception check + MCP)."""
=======
>>>>>>> NhatVi
    return policy_tool_run(state)


def synthesis_worker_node(state: AgentState) -> AgentState:
<<<<<<< HEAD
    """Wrapper gọi synthesis worker (grounded LLM call, temperature=0)."""
    return synthesis_run(state)


# ─────────────────────────────────────────────
# 6. Build Graph
# ─────────────────────────────────────────────

def build_graph():
    """
    Xây dựng graph với supervisor-worker pattern.

    Option A (đơn giản — Python thuần): Dùng if/else, không cần LangGraph.
    Option B (nâng cao): Dùng LangGraph StateGraph với conditional edges.

    Lab này implement Option A theo mặc định.
    TODO Sprint 1: Có thể chuyển sang LangGraph nếu muốn.
    """
    # Option A: Simple Python orchestrator
    def run(state: AgentState) -> AgentState:
        import time
        start = time.time()

        # Step 1: Supervisor decides route
        state = supervisor_node(state)

        # Step 2: Route to appropriate worker
=======
    return synthesis_run(state)


def build_graph():
    def run(state: AgentState) -> AgentState:
        start = time.time()
        state = supervisor_node(state)
>>>>>>> NhatVi
        route = route_decision(state)

        if route == "human_review":
            state = human_review_node(state)
<<<<<<< HEAD
            # After human approval, continue with retrieval
            state = retrieval_worker_node(state)
        elif route == "policy_tool_worker":
            state = policy_tool_worker_node(state)
            # Policy worker may need retrieval context first
            if not state["retrieved_chunks"]:
                state = retrieval_worker_node(state)
        else:
            # Default: retrieval_worker
            state = retrieval_worker_node(state)

        # Step 3: Always synthesize
        state = synthesis_worker_node(state)

=======
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
>>>>>>> NhatVi
        state["latency_ms"] = int((time.time() - start) * 1000)
        state["history"].append(f"[graph] completed in {state['latency_ms']}ms")
        return state

    return run


<<<<<<< HEAD
# ─────────────────────────────────────────────
# 7. Public API
# ─────────────────────────────────────────────

_graph = build_graph()


def run_graph(task: str, **state_overrides) -> AgentState:
    """
    Entry point: nhận câu hỏi, trả về AgentState với full trace.

    Args:
        task: Câu hỏi từ user
        **state_overrides: Optional extra state fields (e.g. retrieval_top_k=5)

    Returns:
        AgentState với final_answer, trace, routing info, v.v.
    """
    state = make_initial_state(task)
    state.update(state_overrides)
    result = _graph(state)
    return result


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
    """Lưu trace ra file JSON."""
=======
_graph = build_graph()


def run_graph(task: str) -> AgentState:
    state = make_initial_state(task)
    return _graph(state)


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
>>>>>>> NhatVi
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{state['run_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return filename


<<<<<<< HEAD
# ─────────────────────────────────────────────
# 8. Manual Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
=======
if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
>>>>>>> NhatVi
    print("=" * 60)
    print("Day 09 Lab — Supervisor-Worker Graph")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
        "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?",
    ]

    for query in test_queries:
<<<<<<< HEAD
        print(f"\n▶ Query: {query}")
=======
        print(f"\n> Query: {query}")
>>>>>>> NhatVi
        result = run_graph(query)
        print(f"  Route   : {result['supervisor_route']}")
        print(f"  Reason  : {result['route_reason']}")
        print(f"  Workers : {result['workers_called']}")
        print(f"  Answer  : {result['final_answer'][:100]}...")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Latency : {result['latency_ms']}ms")
<<<<<<< HEAD

        # Lưu trace
        trace_file = save_trace(result)
        print(f"  Trace saved → {trace_file}")

    print("\n✅ graph.py test complete. Implement TODO sections in Sprint 1 & 2.")
=======
        print(f"  Trace saved -> {save_trace(result)}")

    print("\n[OK] graph.py test complete.")
>>>>>>> NhatVi
