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
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
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

# IF/ElSE cứng (Option A) — đơn giản, dễ hiểu, không cần thư viện ngoài
# def supervisor_node(state: AgentState) -> AgentState:
#     """
#     Supervisor phân tích task và quyết định:
#     1. Route sang worker nào
#     2. Có cần MCP tool không
#     3. Có risk cao cần HITL không

#     TODO Sprint 1: Implement routing logic dựa vào task keywords.
#     """
#     task = state["task"].lower()
#     state["history"].append(f"[supervisor] received task: {state['task'][:80]}")

#     # Mặc định là tra cứu vectorDB thông thường
#     route = "retrieval_worker"
#     route_reason = "Default route: General lookup needed."
#     needs_tool = False
#     risk_high = False

#     # Ví dụ routing cơ bản — nhóm phát triển thêm:
#     policy_keywords = ["hoàn tiền", "refund", "flash sale", "license", "cấp quyền", "access", "level 3"]
#     risk_keywords = ["emergency", "khẩn cấp", "2am", "không rõ", "err-"]

#     if any(kw in task for kw in policy_keywords):
#         route = "policy_tool_worker"
#         route_reason = f"task contains policy/access keyword"
#         needs_tool = True

#     # Nếu có rủi ro cao
#     if any(kw in task for kw in risk_keywords):
#         risk_high = True
#         route_reason += " | risk_high flagged"

#     # Human review override
#     if risk_high and "err-" in task:
#         route = "human_review"
#         route_reason = "unknown error code + risk_high → human review"

#     state["supervisor_route"] = route
#     state["route_reason"] = route_reason
#     state["needs_tool"] = needs_tool
#     state["risk_high"] = risk_high
#     state["history"].append(f"[supervisor] route={route} reason={route_reason}")

#     return state


# Option B: LLM-based Supervisor (Semantic Routing) — linh hoạt, thông minh hơn, nhưng phụ thuộc vào LLM và có thể phát sinh lỗi cần xử lý.
def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor sử dụng LLM để phân tích task và định tuyến (Semantic Routing).
    """
    task = state["task"]
    state["history"].append(f"[supervisor_llm] received task: {task[:80]}")

    # 1. Khởi tạo LLM Client
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # 2. Xây dựng System Prompt ép LLM trả về JSON chuẩn
    system_prompt = """
    Bạn là một AI Supervisor của hệ thống IT/CS Helpdesk. Nhiệm vụ của bạn là đọc yêu cầu của người dùng và quyết định định tuyến (route) đến 1 trong 3 worker sau:

    1. "policy_tool_worker": Chọn nếu yêu cầu liên quan đến thủ tục, chính sách (hoàn tiền, nghỉ phép, hợp đồng), quy định cấp quyền, hoặc tính toán phức tạp.
    2. "human_review": Chọn nếu yêu cầu có RỦI RO CAO (khẩn cấp, ngoài giờ hành chính, sự cố P1 nghiêm trọng) HOẶC chứa các mã lỗi hệ thống không rõ ràng (ví dụ: ERR-xxx).
    3. "retrieval_worker": Chọn cho tất cả các câu hỏi tra cứu thông tin chung, quy định cơ bản (SLA, VPN, mật khẩu) mà không rủi ro cao.

    BẮT BUỘC TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON (Không kèm markdown code block, không thêm text giải thích):
    {
        "route": "retrieval_worker" | "policy_tool_worker" | "human_review",
        "route_reason": "Giải thích ngắn gọn lý do chọn worker này",
        "needs_tool": true | false,
        "risk_high": true | false
    }
    """

    try:
        # 3. Gọi LLM yêu cầu JSON response
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Dùng model mini cho rẻ và nhanh, rất phù hợp làm Router
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task}
            ],
            response_format={"type": "json_object"}, # Ép trả về JSON
            temperature=0.1 # Để nhiệt độ thấp cho quyết định ổn định, logic
        )

        # 4. Parse JSON kết quả
        result_content = response.choices[0].message.content
        decision = json.loads(result_content)

        # Cập nhật State
        route = decision.get("route", "retrieval_worker")
        route_reason = decision.get("route_reason", "LLM Routing")
        needs_tool = decision.get("needs_tool", False)
        risk_high = decision.get("risk_high", False)

    except Exception as e:
        # Fallback an toàn: Nếu LLM lỗi (timeout, hết tiền, parse lỗi...), luôn đẩy về Retrieval
        print(f"⚠️ LLM Routing Error: {e}")
        route = "retrieval_worker"
        route_reason = "Fallback route due to LLM error"
        needs_tool = False
        risk_high = False

    # 5. Lưu vào state
    state["supervisor_route"] = route
    state["route_reason"] = route_reason
    state["needs_tool"] = needs_tool
    state["risk_high"] = risk_high
    state["history"].append(f"[supervisor_llm] route={route} reason={route_reason}")

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
from workers.retrieval import run as retrieval_run
from workers.policy_tool import run as policy_tool_run
from workers.synthesis import run as synthesis_run


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi retrieval worker."""
    # TODO Sprint 2: Thay bằng retrieval_run(state)
    state["workers_called"].append("retrieval_worker")
    state["history"].append("[retrieval_worker] called")

    # Placeholder output để test graph chạy được
    # state["retrieved_chunks"] = [
    #     {"text": "SLA P1: phản hồi 15 phút, xử lý 4 giờ.", "source": "sla_p1_2026.txt", "score": 0.92}
    # ]
    # state["retrieved_sources"] = ["sla_p1_2026.txt"]
    state = retrieval_run(state)
    state["history"].append(f"[retrieval_worker] retrieved {len(state['retrieved_chunks'])} chunks")
    return state


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker."""
    # TODO Sprint 2: Thay bằng policy_tool_run(state)
    state["workers_called"].append("policy_tool_worker")
    state["history"].append("[policy_tool_worker] called")

    # Placeholder output
    # state["policy_result"] = {
    #     "policy_applies": True,
    #     "policy_name": "refund_policy_v4",
    #     "exceptions_found": [],
    #     "source": "policy_refund_v4.txt",
    # }
    state = policy_tool_run(state)
    state["history"].append("[policy_tool_worker] policy check complete")
    return state


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker."""
    # TODO Sprint 2: Thay bằng synthesis_run(state)
    state["workers_called"].append("synthesis_worker")
    state["history"].append("[synthesis_worker] called")

    # Placeholder output
    # chunks = state.get("retrieved_chunks", [])
    # sources = state.get("retrieved_sources", [])
    # state["final_answer"] = f"[PLACEHOLDER] Câu trả lời được tổng hợp từ {len(chunks)} chunks."
    # state["sources"] = sources
    # state["confidence"] = 0.75
    state = synthesis_run(state)
    state["history"].append(f"[synthesis_worker] answer generated, confidence={state['confidence']}")
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
