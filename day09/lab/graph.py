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


# ─────────────────────────────────────────────
# 2. Supervisor Node — quyết định route
# ─────────────────────────────────────────────

import re

def _needs_policy_check(task: str) -> bool:
    """
    Route sang policy_tool_worker CHỈ KHI câu hỏi yêu cầu kiểm tra
    exception, quyền truy cập, hoặc cross-reference policy.
    
    Câu hỏi tra cứu đơn giản (VD: "hoàn tiền trong mấy ngày") → False
    """
    task_lower = task.lower()
    
    # Group A: Refund + exception signal
    has_refund = any(kw in task_lower for kw in ["hoàn tiền", "refund"])
    exception_signals = [
        "flash sale", "license", "kích hoạt", "đăng ký tài khoản",
        "kỹ thuật số", "digital", "subscription", "store credit",
        "ngoại lệ", "exception", "được không", "có được",
        "được hoàn", "không được",
    ]
    if has_refund and any(sig in task_lower for sig in exception_signals):
        return True
    
    # Group B: Access control / permission  
    access_signals = [
        "cấp quyền", "level 2", "level 3", "level 4",
        "admin access", "elevated", "quyền truy cập",
        "phê duyệt quyền", "phê duyệt để cấp",
    ]
    if any(sig in task_lower for sig in access_signals):
        return True

    # Group C: Temporal scoping (đơn trước effective date v4)
    temporal_signals = ["31/01", "30/01", "trước 01/02", "trước ngày"]
    if has_refund and any(sig in task_lower for sig in temporal_signals):
        return True
    
    # Group D: Emergency + access combo
    if any(kw in task_lower for kw in ["emergency", "khẩn cấp"]):
        if any(kw in task_lower for kw in ["level", "quyền", "access", "contractor"]):
            return True
    
    return False

def _detect_risk(task: str) -> tuple:
    """Phát hiện risk signals. Returns (risk_high, risk_reason)."""
    task_lower = task.lower()
    signals = []
    
    if any(kw in task_lower for kw in ["emergency", "khẩn cấp"]):
        signals.append("emergency")
    if any(kw in task_lower for kw in ["2am", "3am", "ngoài giờ"]):
        signals.append("off_hours")
    if "contractor" in task_lower:
        signals.append("external_personnel")
    if any(kw in task_lower for kw in ["level 3", "level 4", "admin"]):
        signals.append("high_privilege")
    
    return (len(signals) > 0, ", ".join(signals))

def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor phân tích task và quyết định:
    1. Route sang worker nào
    2. Có cần MCP tool không
    3. Có risk cao cần HITL không
    """
    task = state["task"]
    task_lower = task.lower()
    state["history"].append(f"[supervisor] received task: {task[:80]}")
    
    # Defaults
    route = "retrieval_worker"
    route_reason = ""
    needs_tool = False

    # Risk detection
    risk_high, risk_reason = _detect_risk(task)
    
    # ── TIER 1: Human Review (mã lỗi không rõ) ──
    if re.search(r'err[-_]?\d{3}', task_lower):
        route = "human_review"
        route_reason = f"unknown error code detected → human review required"
        
    # ── TIER 2: Policy Check ──
    elif _needs_policy_check(task):
        route = "policy_tool_worker"
        needs_tool = True
        # Build specific reason
        reasons = []
        if any(kw in task_lower for kw in ["hoàn tiền", "refund"]):
            reasons.append("refund_exception_check")
        if any(kw in task_lower for kw in ["cấp quyền", "level", "access"]):
            reasons.append("access_permission_check")
        if any(kw in task_lower for kw in ["emergency", "khẩn cấp"]):
            reasons.append("emergency_scenario")
        route_reason = f"policy check required: {', '.join(reasons)}"
    
    # ── TIER 3: Retrieval (default) ──
    else:
        # Build descriptive reason
        if any(kw in task_lower for kw in ["p1", "sla", "ticket", "escalation"]):
            route_reason = "SLA/ticket information lookup"
        elif any(kw in task_lower for kw in ["hoàn tiền", "refund"]):
            route_reason = "refund policy information lookup (no exception check needed)"
        elif any(kw in task_lower for kw in ["remote", "nghỉ phép", "leave"]):
            route_reason = "HR policy information lookup"
        elif any(kw in task_lower for kw in ["mật khẩu", "vpn", "đăng nhập", "tài khoản"]):
            route_reason = "IT helpdesk FAQ lookup"
        else:
            route_reason = "general information retrieval"
    
    # Append risk info
    if risk_high:
        route_reason += f" | risk_high: {risk_reason}"
    
    # Update state
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
    return route  # type: ignore


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
    """Wrapper gọi retrieval worker."""
    try:
        state = retrieval_run(state)
        state.setdefault("workers_called", []).append("retrieval_worker")
    except Exception as e:
        state["history"].append(f"[retrieval_worker] FALLBACK: {e}")
        state.setdefault("workers_called", []).append("retrieval_worker")
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
    return state


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker."""
    try:
        state = policy_tool_run(state)
        state.setdefault("workers_called", []).append("policy_tool_worker")
    except Exception as e:
        state["history"].append(f"[policy_tool_worker] FALLBACK: {e}")
        state.setdefault("workers_called", []).append("policy_tool_worker")
        state["policy_result"] = {"error": str(e)}
    return state


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker."""
    try:
        state = synthesis_run(state)
        state.setdefault("workers_called", []).append("synthesis_worker")
    except Exception as e:
        state["history"].append(f"[synthesis_worker] FALLBACK: {e}")
        state.setdefault("workers_called", []).append("synthesis_worker")
        state["final_answer"] = f"SYNTHESIS_ERROR: {e}"
        state["confidence"] = 0.0
    return state



# ─────────────────────────────────────────────
# 6. Build Graph
# ─────────────────────────────────────────────

def build_graph():
    """
    Xây dựng graph với supervisor-worker pattern.
    Sử dụng LangGraph StateGraph.
    """
    from langgraph.graph import StateGraph, START, END
    
    # Khởi tạo graph
    builder = StateGraph(AgentState)

    # Khai báo các nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("retrieval_worker", retrieval_worker_node)
    builder.add_node("policy_tool_worker", policy_tool_worker_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("synthesis_worker", synthesis_worker_node)

    # Bắt đầu tại supervisor
    builder.add_edge(START, "supervisor")

    # Supervisor quyết định route
    def supervisor_router(state: AgentState) -> str:
        route = state.get("supervisor_route", "retrieval_worker")
        # QUAN TRỌNG: Nếu là policy, vẫn đi qua retrieval trước để lấy evidence
        if route == "policy_tool_worker":
            return "retrieval_worker"
        return route

    builder.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "human_review": "human_review",
            "retrieval_worker": "retrieval_worker"
        }
    )

    # Human review auto approve -> retrieval
    builder.add_edge("human_review", "retrieval_worker")

    # Logic sau retrieval: nếu supervisor ban đầu chọn policy -> đi sang policy
    # Ngược lại -> synthesis
    def after_retrieval_router(state: AgentState) -> str:
        if state.get("supervisor_route") == "policy_tool_worker":
            return "policy_tool_worker"
        return "synthesis_worker"
        
    builder.add_conditional_edges(
        "retrieval_worker",
        after_retrieval_router,
        {
            "policy_tool_worker": "policy_tool_worker",
            "synthesis_worker": "synthesis_worker"
        }
    )

    # Policy xong -> synthesis
    builder.add_edge("policy_tool_worker", "synthesis_worker")

    # Synthesis -> END
    builder.add_edge("synthesis_worker", END)

    # Compile graph
    graph = builder.compile()

    # Wrapper để tương thích với API test
    def run(state: AgentState) -> AgentState:
        import time
        start = time.time()
        final_state = graph.invoke(state)
        final_state["latency_ms"] = int((time.time() - start) * 1000)
        final_state["history"].append(f"[graph] completed in {final_state['latency_ms']}ms")
        return final_state

    return run


# ─────────────────────────────────────────────
# 7. Public API
# ─────────────────────────────────────────────

_graph = build_graph()


def run_graph(task: str) -> AgentState:
    """
    Entry point: nhận câu hỏi, trả về AgentState với full trace.

    Args:
        task: Câu hỏi từ user

    Returns:
        AgentState với final_answer, trace, routing info, v.v.
    """
    state = make_initial_state(task)
    result = _graph(state)
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
        "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run_graph(query)
        print(f"  Route   : {result['supervisor_route']}")
        print(f"  Reason  : {result['route_reason']}")
        print(f"  Workers : {result['workers_called']}")
        print(f"  Answer  : {result['final_answer'][:100]}...")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Latency : {result['latency_ms']}ms")

        # Lưu trace
        trace_file = save_trace(result)
        print(f"  Trace saved → {trace_file}")

    print("\n✅ graph.py test complete. Implement TODO sections in Sprint 1 & 2.")
