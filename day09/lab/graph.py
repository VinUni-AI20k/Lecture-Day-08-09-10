"""
graph.py — Supervisor Orchestrator (LangGraph Implementation)
Sprint 1: Implement AgentState, supervisor_node, route_decision và kết nối graph.

Kiến trúc:
    Input → Supervisor → [retrieval_worker | policy_tool_worker | human_review] → synthesis → Output

LangGraph Features Used:
    - StateGraph: Automatic state management across nodes
    - Conditional Edges: Dynamic routing based on supervisor decisions
    - Type-safe State: TypedDict ensures consistent state structure
    - Visual Graph: Can generate Mermaid diagrams of the workflow

Chạy thử:
    python graph.py
"""

import json
import os
from datetime import datetime
from typing import TypedDict, Literal, Optional, Annotated
from typing_extensions import TypedDict as TypedDictExt

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

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

def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor phân tích task và quyết định:
    1. Route sang worker nào
    2. Có cần MCP tool không
    3. Có risk cao cần HITL không

    Routing logic dựa vào task keywords theo contracts.
    """
    task = state["task"].lower()
    state["history"].append(f"[supervisor] received task: {state['task'][:80]}")

    # Default values
    route = "retrieval_worker"
    route_reason = ""
    needs_tool = False
    risk_high = False

    # Define keyword groups
    policy_keywords = [
        "hoàn tiền", "refund", "flash sale", "license", 
        "cấp quyền", "access", "level 2", "level 3", 
        "digital product", "activated", "store credit"
    ]
    
    sla_keywords = ["p1", "p2", "p3", "escalation", "sla", "ticket", "thông báo", "deadline"]
    
    risk_keywords = ["emergency", "khẩn cấp", "2am", "22:47", "không rõ"]
    
    error_code_pattern = "err-"

    # Priority 1: Check for error codes + risk → human review
    if error_code_pattern in task and any(kw in task for kw in risk_keywords):
        route = "human_review"
        route_reason = "unknown error code with risk_high context → human review required"
        risk_high = True
    
    # Priority 2: Policy/access control questions → policy_tool_worker + MCP enabled
    elif any(kw in task for kw in policy_keywords):
        route = "policy_tool_worker"
        matched_keywords = [kw for kw in policy_keywords if kw in task]
        route_reason = (
            f"task contains policy/access keywords: {', '.join(matched_keywords[:2])}"
            " | MCP enabled: search_kb + check_access_permission"
        )
        needs_tool = True

        # Check if also high risk
        if any(kw in task for kw in risk_keywords):
            risk_high = True
            route_reason += " | risk_high: emergency context detected"

    # Priority 3: SLA/ticket questions → retrieval_worker (no MCP needed)
    elif any(kw in task for kw in sla_keywords):
        route = "retrieval_worker"
        matched_keywords = [kw for kw in sla_keywords if kw in task]
        route_reason = (
            f"task contains SLA/ticket keywords: {', '.join(matched_keywords[:2])}"
            " | MCP disabled: direct retrieval sufficient"
        )

        # Check if also high risk
        if any(kw in task for kw in risk_keywords):
            risk_high = True
            route_reason += " | risk_high: time-sensitive SLA query"

    # Priority 4: Default → retrieval_worker (no MCP needed)
    else:
        route = "retrieval_worker"
        route_reason = "default route: general knowledge retrieval | MCP disabled"

    # Ensure route_reason is never empty
    if not route_reason:
        route_reason = f"routed to {route} based on task analysis"

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

    # Sau khi human approve, gọi retrieval để lấy evidence
    state = retrieval_worker_node(state)
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
    return retrieval_run(state)


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker."""
    # Policy worker may need retrieval context first
    if not state.get("retrieved_chunks"):
        state = retrieval_run(state)
    return policy_tool_run(state)


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker."""
    return synthesis_run(state)


# ─────────────────────────────────────────────
# 6. Build Graph
# ─────────────────────────────────────────────

def build_graph():
    """
    Xây dựng graph với supervisor-worker pattern sử dụng LangGraph.
    
    Graph flow:
    START → supervisor → route_decision → [retrieval_worker | policy_tool_worker | human_review]
                                       → synthesis → END
    """
    # Create StateGraph with AgentState
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("retrieval_worker", retrieval_worker_node)
    workflow.add_node("policy_tool_worker", policy_tool_worker_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("synthesis", synthesis_worker_node)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Add conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_decision,
        {
            "retrieval_worker": "retrieval_worker",
            "policy_tool_worker": "policy_tool_worker",
            "human_review": "human_review",
        }
    )
    
    # Add edges from workers to synthesis
    workflow.add_edge("retrieval_worker", "synthesis")
    workflow.add_edge("policy_tool_worker", "synthesis")
    workflow.add_edge("human_review", "synthesis")
    
    # Add edge from synthesis to END
    workflow.add_edge("synthesis", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app


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
    import time
    start = time.time()
    
    state = make_initial_state(task)
    result = _graph.invoke(state)
    
    # Add latency
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


def visualize_graph(output_path: str = "./artifacts/graph_visualization.png"):
    """
    Visualize the LangGraph structure.
    Generates Mermaid diagram text that can be rendered.
    """
    try:
        # Try to get Mermaid PNG
        try:
            graph_image = _graph.get_graph().draw_mermaid_png()
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(graph_image)
            print(f"✅ Graph visualization saved to {output_path}")
            return output_path
        except:
            # Fallback: Generate Mermaid text
            mermaid_text = _graph.get_graph().draw_mermaid()
            mermaid_path = output_path.replace('.png', '.mmd')
            os.makedirs(os.path.dirname(mermaid_path), exist_ok=True)
            with open(mermaid_path, "w", encoding="utf-8") as f:
                f.write(mermaid_text)
            print(f"✅ Graph Mermaid diagram saved to {mermaid_path}")
            print(f"   View at: https://mermaid.live/ or use Mermaid CLI")
            return mermaid_path
    except Exception as e:
        print(f"⚠️  Could not generate graph visualization: {e}")
        return None


# ─────────────────────────────────────────────
# 8. Manual Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Day 09 Lab — Supervisor-Worker Graph (LangGraph)")
    print("=" * 60)

    # Optional: Visualize graph structure
    print("\n📊 Generating graph visualization...")
    visualize_graph()

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
        "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?",
        "Hệ thống báo lỗi ERR-9999 không rõ nguyên nhân, khẩn cấp cần xử lý",
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

    print("\n✅ graph.py test complete.")
    print("✅ LangGraph implementation with StateGraph and conditional edges.")
    print("   Features: Automatic state management, visual graph, conditional routing.")
