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
import time

# Uncomment nếu dùng LangGraph:
from langgraph.graph import StateGraph, END

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
        "history": [f"Run started at {datetime.now().isoformat()}"],
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
    route_reason = "General query: defaulting to retrieval"    # TODO: thay bằng lý do thực
    needs_tool = False
    risk_high = False

    # Ví dụ routing cơ bản — nhóm phát triển thêm:
    policy_kws = ["hoàn tiền", "refund", "flash sale", "license", "cấp quyền", "access"]
    risk_kws = ["emergency", "khẩn cấp", "sập", "critical", "p0", "p1"]
    error_kws = ["err-", "mã lỗi", "không chạy được"]

    # Logic điều hướng phân cấp
    if any(kw in task for kw in risk_kws):
        risk_high = True
        reason = "High risk/Priority detected"
        
    if any(kw in task for kw in policy_kws):
        route = "policy_tool_worker"
        reason = "Policy/Access related task"
        needs_tool = True

    if any(kw in task for kw in error_kws) and risk_high:
        route = "human_review"
        reason = "Critical error detected: Human intervention required"

    state["supervisor_route"] = route
    state["route_reason"] = reason
    state["risk_high"] = risk_high
    state["needs_tool"] = needs_tool
    state["history"].append(f"[supervisor] route={route} reason={reason}")
    return state


# ─────────────────────────────────────────────
# 3. Route Decision — conditional edge
# ─────────────────────────────────────────────

def route_decision(state: AgentState) -> Literal["retrieval_worker", "policy_tool_worker", "human_review"]:
    """
    Trả về tên worker tiếp theo dựa vào supervisor_route trong state.
    Đây là conditional edge của graph.
    """
    route = state.get("supervisor_route")
    if route == "human_review": return "human"
    if route == "policy_tool_worker": return "policy"
    return "retrieval"


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
    """HITL: Tạm dừng để con người xác nhận (Lab Placeholder)."""
    state["hitl_triggered"] = True
    state["workers_called"].append("human_review")
    
    print(f"\n[!] HITL Triggered: {state['route_reason']}")
    print(f"    Approving and moving to retrieval...")
    
    state["history"].append("[human_review] approved by admin")
    return state


# ─────────────────────────────────────────────
# 5. Import Workers
# ─────────────────────────────────────────────

# TODO Sprint 2: Uncomment sau khi implement workers
from workers.retrieval import run as retrieval_run
from workers.policy_tool import run as policy_tool_run
from workers.synthesis import run as synthesis_run


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi retrieval worker."""
    # TODO Sprint 2: Thay bằng retrieval_run(state)
    """Node xử lý tra cứu dữ liệu (Sprint 2 thực tế)."""
    state["workers_called"].append("retrieval_worker")
    
    # Placeholder data
    state["retrieved_chunks"] = [{"text": "SLA P1: 15m response", "source": "SLA_2026.pdf"}]
    state["retrieved_sources"] = ["SLA_2026.pdf"]
    state["history"].append("[retrieval_worker] data fetched")
    return state


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker."""
    # TODO Sprint 2: Thay bằng policy_tool_run(state)
    """Node xử lý công cụ chính sách (Sprint 2 thực tế)."""
    state["workers_called"].append("policy_tool_worker")
    
    # Placeholder data
    state["policy_result"] = {"status": "authorized", "policy": "Standard_Refund_v1"}
    state["history"].append("[policy_tool_worker] policy check done")
    return state


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker."""
    # TODO Sprint 2: Thay bằng synthesis_run(state)
    """Node tổng hợp câu trả lời cuối cùng."""
    state["workers_called"].append("synthesis_worker")
    
    # Giả lập logic tổng hợp
    state["final_answer"] = f"Dựa trên dữ liệu, tôi xác nhận: {state['task']}. (Confidence: 0.85)"
    state["sources"] = state.get("retrieved_sources", [])
    state["confidence"] = 0.85
    state["history"].append("[synthesis_worker] final answer generated")
    return state


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
    workflow = StateGraph(AgentState)

    # Thêm Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("retrieval", retrieval_worker_node)
    workflow.add_node("policy", policy_tool_worker_node)
    workflow.add_node("human", human_review_node)
    workflow.add_node("synthesis", synthesis_worker_node)

    # Thiết lập luồng
    workflow.set_entry_point("supervisor")

    # Luồng điều hướng từ Supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_decision,
        {
            "human": "human",
            "policy": "policy",
            "retrieval": "retrieval"
        }
    )

    # Các worker đều dẫn về Synthesis
    workflow.add_edge("human", "retrieval") # Sau khi duyệt, đi lấy data
    workflow.add_edge("retrieval", "synthesis")
    workflow.add_edge("policy", "synthesis")
    
    # Synthesis là bước cuối
    workflow.add_edge("synthesis", END)

    return workflow.compile()


# ─────────────────────────────────────────────
# 7. Public API
# ─────────────────────────────────────────────

_app = build_graph()


def run_graph(task: str) -> AgentState:
    """
    Entry point: nhận câu hỏi, trả về AgentState với full trace.

    Args:
        task: Câu hỏi từ user

    Returns:
        AgentState với final_answer, trace, routing info, v.v.
    """
    start_time = time.time()
    state = make_initial_state(task)
    
    # Thực thi graph
    final_state = _app.invoke(state)
    
    # Tính toán latency
    final_state["latency_ms"] = int((time.time() - start_time) * 1000)
    return final_state


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
