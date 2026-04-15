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

def supervisor_node(state: AgentState) -> AgentState:
    task = state["task"].lower()

    state["history"].append(
        f"[supervisor] received task: {task[:80]}"
    )

    policy_keywords = [
        "hoàn tiền", "refund", "flash sale",
        "license", "cấp quyền", "access", "level 3"
    ]

    risk_keywords = [
        "emergency", "khẩn cấp", "err-"
    ]

    retrieval_keywords = [
        "p1", "escalation", "sla", "ticket"
    ]

    # flags
    is_policy = any(kw in task for kw in policy_keywords)
    is_retrieval = any(kw in task for kw in retrieval_keywords)
    risk_high = any(kw in task for kw in risk_keywords)

    route = "retrieval_worker"
    route_reason = "fallback retrieval"
    needs_tool = False

    # ─────────────────────────────
    # 1. HIGHEST PRIORITY: HUMAN REVIEW
    # ─────────────────────────────
    if risk_high and "err-" in task:
        route = "human_review"
        route_reason = "error + risk_high → human review"

    # ─────────────────────────────
    # 2. POLICY ROUTE
    # ─────────────────────────────
    elif is_policy:
        route = "policy_tool_worker"
        route_reason = "policy / access task"
        needs_tool = True

    # ─────────────────────────────
    # 3. RETRIEVAL ROUTE
    # ─────────────────────────────
    elif is_retrieval:
        route = "retrieval_worker"
        route_reason = "sla / ticket query"
        needs_tool = True

    state["supervisor_route"] = route
    state["route_reason"] = route_reason
    state["needs_tool"] = needs_tool
    state["risk_high"] = risk_high

    state["history"].append(
        f"[supervisor] route={route} risk={risk_high} tool={needs_tool}"
    )

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

# TODO Sprint 2: Uncomment sau khi implement workers
# from workers.retrieval import run as retrieval_run
# from workers.policy_tool import run as policy_tool_run
# from workers.synthesis import run as synthesis_run


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Retrieve relevant documents based on task."""

    state["workers_called"].append("retrieval_worker")
    state["history"].append("[retrieval_worker] called")

    query = state["task"].lower()

    kb = [
        {
            "text": "SLA P1: phản hồi 15 phút, xử lý 4 giờ.",
            "source": "sla_p1.txt",
            "keywords": ["p1", "sla", "ticket"]
        },
        {
            "text": "Escalation P1 cần notify team lead ngay lập tức.",
            "source": "escalation.txt",
            "keywords": ["escalation", "p1"]
        },
        {
            "text": "Ticket xử lý theo mức độ ưu tiên P0 P1 P2.",
            "source": "ticket_priority.txt",
            "keywords": ["ticket", "priority"]
        }
    ]

    results = []

    for doc in kb:
        if any(kw in query for kw in doc["keywords"]):
            results.append({
                "text": doc["text"],
                "source": doc["source"],
                "score": 0.9
            })

    # fallback nếu không match
    if not results:
        results = [{
            "text": "Không tìm thấy dữ liệu phù hợp.",
            "source": "fallback",
            "score": 0.3
        }]

    # IMPORTANT: dùng results thật (fix bug của bạn)
    state["retrieved_chunks"] = results
    state["retrieved_sources"] = list(set([r["source"] for r in results]))

    state["history"].append(
        f"[retrieval_worker] retrieved {len(results)} chunks"
    )

    return state


def policy_tool_worker_node(state: AgentState) -> AgentState:
    state["workers_called"].append("policy_tool_worker")
    state["history"].append("[policy_tool_worker] called")

    task = state["task"].lower()

    result = {
        "policy_applies": False,
        "policy_name": None,
        "decision": None,
        "reason": "",
        "source": "policy_db",
        "exceptions_found": []
    }

    # Rule 1: refund
    if "hoàn tiền" in task or "refund" in task:
        result["policy_applies"] = True
        result["policy_name"] = "refund_policy_v4"

        if "flash sale" in task:
            result["decision"] = "allowed_with_condition"
            result["reason"] = "Flash sale chỉ hoàn tiền nếu sản phẩm lỗi"
        else:
            result["decision"] = "allowed"
            result["reason"] = "Refund tiêu chuẩn"

        result["source"] = "policy_refund_v4.txt"

    # Rule 2: access control
    elif "cấp quyền" in task or "access" in task:
        result["policy_applies"] = True
        result["policy_name"] = "access_control_v2"
        result["decision"] = "requires_approval"
        result["reason"] = "Cấp quyền level cao cần approval"

        result["source"] = "policy_access_control_v2.txt"

    else:
        result["reason"] = "No matching policy"

    state["policy_result"] = result

    state["history"].append(
        f"[policy_tool_worker] policy={result['policy_name']} decision={result['decision']}"
    )

    return state


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker."""
    state["workers_called"].append("synthesis_worker")
    state["history"].append("[synthesis_worker] called")

    chunks = state.get("retrieved_chunks", [])
    sources = state.get("retrieved_sources", [])
    policy = state.get("policy_result", {})

    answer_parts = []

    # ─────────────────────────────
    # 1. POLICY LAYER
    # ─────────────────────────────
    if policy and policy.get("policy_applies"):
        answer_parts.append(
            f"[Policy Decision] {policy.get('policy_name')} → {policy.get('decision')}. "
            f"Lý do: {policy.get('reason')}"
        )

    # ─────────────────────────────
    # 2. RETRIEVAL LAYER
    # ─────────────────────────────
    if chunks:
        answer_parts.append("\n[Evidence]")
        for c in chunks:
            answer_parts.append(f"- {c['text']} (source: {c['source']})")

    # ─────────────────────────────
    # 3. FALLBACK
    # ─────────────────────────────
    if not answer_parts:
        final_answer = "Không tìm thấy đủ thông tin để trả lời câu hỏi này."
        confidence = 0.3
    else:
        final_answer = "\n".join(answer_parts)

        # confidence logic đơn giản nhưng thực tế
        confidence = 0.5

        if chunks:
            confidence += 0.2
        if policy and policy.get("policy_applies"):
            confidence += 0.2
        if len(chunks) > 1:
            confidence += 0.1

        confidence = min(confidence, 0.95)

    # ─────────────────────────────
    # 4. UPDATE STATE
    # ─────────────────────────────
    state["final_answer"] = final_answer
    state["sources"] = sources
    state["confidence"] = confidence

    state["history"].append(
        f"[synthesis_worker] generated answer | confidence={confidence}"
    )

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
