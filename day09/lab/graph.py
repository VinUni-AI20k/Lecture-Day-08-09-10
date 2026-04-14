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
    worker_io_logs: list                # Log chi tiết của từng worker (input/output)
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
        "worker_io_logs": [],
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
    1. Route sang worker nào (retrieval_worker | policy_tool_worker | human_review)
    2. Có cần MCP tool không (needs_tool)
    3. Có risk cao cần HITL không (risk_high)

    Routing dựa trên keyword matching với thứ tự ưu tiên:
        1. Human review: mã lỗi không rõ (ERR-xxx) và thiếu context
        2. Policy/Tool worker: refund, access control, policy exception questions
        3. Retrieval worker: SLA, ticket, helpdesk, HR, và mặc định
    """
    task = state["task"].lower()
    state["history"].append(f"[supervisor] received task: {state['task'][:80]}")

    # ── Keyword sets ─────────────────────────────────────
    # Nhóm 1: Policy exception / access control → policy_tool_worker
    #   Chỉ trigger khi câu hỏi liên quan đến exceptions, edge cases,
    #   hoặc cần kiểm tra policy rule cụ thể.
    policy_exception_keywords = [
        "flash sale", "store credit",
        "ngoại lệ", "exception",
        "license key", "subscription", "kỹ thuật số",
        "đã kích hoạt", "kích hoạt", "đã đăng ký",
        "không được hoàn",
    ]
    access_keywords = [
        "cấp quyền", "access level", "level 2", "level 3", "level 4",
        "admin access", "elevated access",
        "quyền truy cập", "quyền tạm thời", "thu hồi quyền",
    ]

    # Nhóm 1b: Kết hợp refund + action verb → policy_tool_worker
    #   "hoàn tiền" chỉ trigger policy khi đi kèm tín hiệu hành động/kiểm tra
    refund_action_signals = [
        "được không", "được hoàn", "có được", "xử lý hoàn",
        "chính sách hoàn", "điều kiện hoàn",
    ]

    # Nhóm 2: SLA & Ticket → retrieval_worker
    sla_keywords = [
        "p1", "p2", "p3", "p4", "sla", "ticket",
        "escalation", "escalate", "sự cố", "incident",
        "on-call", "phản hồi", "resolution",
    ]

    # Nhóm 3: Risk signals
    risk_keywords = [
        "emergency", "khẩn cấp", "2am", "3am", "ngoài giờ",
        "tạm thời", "urgent", "critical",
    ]

    # ── Classify ─────────────────────────────────────────
    route = "retrieval_worker"
    route_reason = ""
    needs_tool = False
    risk_high = False

    # Detect matched keywords for explainability
    matched_exception = [kw for kw in policy_exception_keywords if kw in task]
    matched_access    = [kw for kw in access_keywords if kw in task]
    matched_sla       = [kw for kw in sla_keywords if kw in task]
    matched_risk      = [kw for kw in risk_keywords if kw in task]

    # Refund + action signal combo check
    has_refund_word = any(kw in task for kw in ["hoàn tiền", "refund"])
    has_refund_action = any(kw in task for kw in refund_action_signals)
    refund_policy_trigger = has_refund_word and has_refund_action

    # ── Step 1: Check human_review (only for truly ambiguous cases) ──
    import re
    err_match = re.search(r"err[-_]?\d{3}", task)
    ambiguity_signals = ["không rõ", "không hiểu", "giải thích"]
    is_ambiguous = err_match and any(s in task for s in ambiguity_signals)

    if is_ambiguous:
        route = "human_review"
        route_reason = f"unknown error code '{err_match.group()}' + ambiguous context → human review needed"
        risk_high = True

    # ── Step 2: Policy exception / Access control routing ──
    elif matched_exception or matched_access or refund_policy_trigger:
        route = "policy_tool_worker"
        needs_tool = True
        triggers = matched_exception + matched_access
        if refund_policy_trigger:
            triggers += ["refund+action"]
        route_reason = f"task contains policy/access keywords: [{', '.join(triggers[:4])}]"

        # Multi-hop: nếu câu hỏi vừa chứa cả policy keywords VÀ SLA keywords
        if matched_sla:
            route_reason += f" + SLA context [{', '.join(matched_sla[:3])}] → multi-hop policy+retrieval"

    # ── Step 3: SLA / Ticket routing ──
    elif matched_sla:
        route = "retrieval_worker"
        route_reason = f"task contains SLA/ticket keywords: [{', '.join(matched_sla[:4])}]"

    # ── Step 4: Default → retrieval_worker ──
    else:
        route = "retrieval_worker"
        route_reason = "no specific policy/SLA signal detected — default to knowledge base retrieval"

    # ── Risk assessment (additive, independent of route) ──
    if matched_risk:
        risk_high = True
        route_reason += f" | risk_high flagged: [{', '.join(matched_risk[:3])}]"

    # ── Persist decisions to state ────────────────────────
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
    """Wrapper gọi retrieval worker (Sprint 2)."""
    return retrieval_run(state)


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker (Sprint 2)."""
    return policy_tool_run(state)


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker (Sprint 2)."""
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
        route = route_decision(state)

        if route == "human_review":
            state = human_review_node(state)
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

        state["latency_ms"] = int((time.time() - start) * 1000)
        state["history"].append(f"[graph] completed in {state['latency_ms']}ms")
        return state

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
    import io, sys
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("=" * 60)
    print("Day 09 Lab -- Supervisor-Worker Graph")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
        "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?",
    ]

    for query in test_queries:
        print(f"\n>> Query: {query}")
        result = run_graph(query)
        print(f"  Route   : {result['supervisor_route']}")
        print(f"  Reason  : {result['route_reason']}")
        print(f"  Workers : {result['workers_called']}")
        print(f"  Answer  : {result['final_answer'][:120]}...")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Latency : {result['latency_ms']}ms")

        trace_file = save_trace(result)
        print(f"  Trace   : {trace_file}")

    print("\n[OK] graph.py Sprint 2 wired -- real workers active.")
