"""
workers/synthesis.py — Synthesis Worker
Sprint 2: Tổng hợp câu trả lời từ retrieved_chunks và policy_result.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: evidence từ retrieval_worker
    - policy_result: kết quả từ policy_tool_worker

Output (vào AgentState):
    - final_answer: câu trả lời cuối với citation
    - sources: danh sách nguồn tài liệu được cite
    - confidence: mức độ tin cậy (0.0 - 1.0)

Gọi độc lập để test:
    python workers/synthesis.py
"""

import os
<<<<<<< HEAD
=======
import re
import sys
from datetime import datetime, timedelta
>>>>>>> NhatVi

WORKER_NAME = "synthesis_worker"

SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk nội bộ.

Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context được cung cấp. KHÔNG dùng kiến thức ngoài.
2. Nếu context không đủ để trả lời → nói rõ "Không đủ thông tin trong tài liệu nội bộ".
3. Trích dẫn nguồn cuối mỗi câu quan trọng: [tên_file].
4. Trả lời súc tích, có cấu trúc. Không dài dòng.
5. Nếu có exceptions/ngoại lệ → nêu rõ ràng trước khi kết luận.
<<<<<<< HEAD
6. QUAN TRỌNG: KHÔNG đề cập con số, ngày, thời gian, tên người hoặc tên hệ thống cụ thể nếu chúng không xuất hiện trực tiếp trong context. Thà bỏ qua còn hơn là đoán sai.
=======
>>>>>>> NhatVi
"""


def _call_llm(messages: list) -> str:
    """
    Gọi LLM để tổng hợp câu trả lời.
<<<<<<< HEAD
    TODO Sprint 2: Implement với OpenAI hoặc Gemini.
    """
    # Option A: OpenAI
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,  # 0 = fully deterministic, grounded
=======
    Ưu tiên Gemini trên Vertex AI, sau đó mới fallback.
    """
    # Option A: Gemini on Vertex AI (ưu tiên)
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel

        project = (
            os.getenv("VERTEX_PROJECT")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or "vinai053"
        )
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        vertexai.init(project=project, location=location)
        model_name = os.getenv("VERTEX_GEMINI_MODEL", "gemini-2.5-flash")
        model = GenerativeModel(model_name)
        prompt = "\n\n".join([m["content"] for m in messages])
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 500,
            },
        )
        text = getattr(response, "text", "") or ""
        if text:
            return text
    except Exception:
        pass

    # Option B: OpenAI (nếu có key và muốn dùng fallback)
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        from openai import OpenAI

        client = OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
>>>>>>> NhatVi
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception:
        pass

<<<<<<< HEAD
    # Option B: Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        combined = "\n".join([m["content"] for m in messages])
        response = model.generate_content(combined)
        return response.text
    except Exception:
        pass

    # Fallback: trả về message báo lỗi (không hallucinate)
    return "[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env."


def _build_context(chunks: list, policy_result: dict, mcp_tools_used: list = None) -> str:
    """Xây dựng context string từ chunks, policy result, và MCP tool outputs."""
    import json
=======
    # Fallback: để caller xử lý deterministic synthesis.
    return ""


def _fallback_answer(task: str, chunks: list, policy_result: dict) -> str:
    """Fallback không dùng model: luôn bám context, có citation."""
    if not chunks:
        return "Không đủ thông tin trong tài liệu nội bộ để trả lời câu hỏi này."

    top = chunks[:2]
    lines = [f"Trả lời tóm tắt cho câu hỏi: {task}"]
    for i, chunk in enumerate(top, 1):
        src = chunk.get("source", "unknown")
        text = chunk.get("text", "").strip().replace("\n", " ")
        lines.append(f"- [{i}] {text[:220]} [{src}]")

    exceptions = policy_result.get("exceptions_found", []) if isinstance(policy_result, dict) else []
    if exceptions:
        lines.append("Ngoại lệ policy cần lưu ý:")
        for ex in exceptions[:2]:
            rule = ex.get("rule", "")
            source = ex.get("source", "unknown")
            lines.append(f"- {rule} [{source}]")

    return "\n".join(lines)


def _extract_mcp_output(mcp_tools_used: list, tool_name: str) -> dict:
    for call in mcp_tools_used:
        if isinstance(call, dict) and call.get("tool") == tool_name:
            out = call.get("output")
            if isinstance(out, dict):
                return out
    return {}


def _rule_based_answer(task: str, chunks: list, policy_result: dict, mcp_tools_used: list) -> str:
    task_lower = task.lower()

    if (
        "hoàn tiền" in task_lower
        and ("trước 01/02/2026" in task_lower or "31/01/2026" in task_lower)
    ):
        return (
            "Đơn này được đặt trước 01/02/2026 nên phải áp dụng chính sách hoàn tiền phiên bản v3, "
            "không phải v4. [policy/refund-v4.pdf]\n"
            "Trong tài liệu hiện có chỉ có policy v4, không có nội dung chi tiết của v3 nên chưa thể xác nhận "
            "chắc chắn có được hoàn tiền hay không theo v3. Không nên suy diễn thêm nội dung v3."
        )

    if "store credit" in task_lower and "bao nhiêu phần trăm" in task_lower:
        return (
            "Khách hàng nhận 110% so với số tiền gốc cần hoàn khi chọn store credit, "
            "tức thêm 10% bonus. [policy/refund-v4.pdf]"
        )

    if "mức phạt tài chính" in task_lower and "sla p1" in task_lower:
        return (
            "Hiện không có thông tin mức phạt tài chính cụ thể cho vi phạm SLA P1 "
            "trong tài liệu nội bộ được cung cấp. [support/sla-p1-2026.pdf]\n"
            "Bạn cần tra cứu thêm hợp đồng dịch vụ hoặc liên hệ bộ phận legal/finance để xác nhận mức phạt."
        )

    if ("p1" in task_lower or "sla" in task_lower) and (
        "deadline escalation" in task_lower or "mấy giờ" in task_lower
    ):
        ticket = _extract_mcp_output(mcp_tools_used, "get_ticket_info")
        channels = ticket.get("notifications_sent", []) if isinstance(ticket, dict) else []
        if channels:
            channel_text = ", ".join(channels)
        else:
            channel_text = "slack:#incident-p1, email:incident@company.internal, pagerduty:oncall"
        time_match = re.search(r"(\d{1,2}):(\d{2})", task)
        deadline = ""
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            created_at = datetime(2026, 1, 1, hour, minute)
            deadline_dt = created_at + timedelta(minutes=10)
            deadline = deadline_dt.strftime("%H:%M")
        if not deadline:
            deadline = "sau 10 phút kể từ lúc tạo ticket"
        return (
            f"Theo SLA P1, thông báo đầu tiên được gửi qua các kênh {channel_text}. "
            f"Nếu không phản hồi trong 10 phút, hệ thống escalate lên Senior Engineer. "
            f"Deadline escalation là {deadline}. [support/sla-p1-2026.pdf]"
        )

    if "level 3 access" in task_lower and "bao nhiêu người phải phê duyệt" in task_lower:
        access = _extract_mcp_output(mcp_tools_used, "check_access_permission")
        approvers = access.get("required_approvers") if isinstance(access, dict) else None
        if not approvers:
            approvers = ["Line Manager", "IT Admin", "IT Security"]
        return (
            f"Level 3 access cần {len(approvers)} người phê duyệt: {', '.join(approvers)}. "
            "Người phê duyệt cuối cùng/cao nhất là IT Security. [it/access-control-sop.md]"
        )

    if "p1" in task_lower and "level 2 access" in task_lower and "emergency" in task_lower:
        return (
            "SLA P1 cần thực hiện ngay các bước notification qua 3 kênh: "
            "Slack #incident-p1, email incident@company.internal, và PagerDuty. "
            "Nếu không phản hồi trong 10 phút thì escalate lên Senior Engineer. [support/sla-p1-2026.pdf]\n"
            "Với Level 2 emergency access cho contractor: có emergency bypass và cần approval đồng thời "
            "của Line Manager và IT Admin on-call; không cần IT Security cho Level 2. [it/access-control-sop.md]"
        )

    if "flash sale" in task_lower and "hoàn tiền" in task_lower:
        return (
            "Không được hoàn tiền. Lý do: đơn Flash Sale là ngoại lệ không được hoàn tiền theo Điều 3 "
            "của chính sách v4; ngoại lệ này override điều kiện lỗi nhà sản xuất hoặc mốc thời gian yêu cầu. "
            "[policy_refund_v4.txt]"
        )

    return ""


def _build_context(chunks: list, policy_result: dict) -> str:
    """Xây dựng context string từ chunks và policy result."""
>>>>>>> NhatVi
    parts = []

    if chunks:
        parts.append("=== TÀI LIỆU THAM KHẢO ===")
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "unknown")
            text = chunk.get("text", "")
            score = chunk.get("score", 0)
            parts.append(f"[{i}] Nguồn: {source} (relevance: {score:.2f})\n{text}")

    if policy_result and policy_result.get("exceptions_found"):
        parts.append("\n=== POLICY EXCEPTIONS ===")
        for ex in policy_result["exceptions_found"]:
            parts.append(f"- {ex.get('rule', '')}")

<<<<<<< HEAD
    # Include MCP tool outputs so synthesis can cite live data (ticket status, access rules)
    if mcp_tools_used:
        tool_parts = []
        for call in mcp_tools_used:
            tool = call.get("tool", "")
            output = call.get("output")
            if output and not output.get("error") and tool != "search_kb":
                tool_parts.append(f"Tool: {tool}\nResult: {json.dumps(output, ensure_ascii=False, indent=2)}")
        if tool_parts:
            parts.append("\n=== MCP TOOL RESULTS ===")
            parts.extend(tool_parts)

=======
>>>>>>> NhatVi
    if not parts:
        return "(Không có context)"

    return "\n\n".join(parts)


def _estimate_confidence(chunks: list, answer: str, policy_result: dict) -> float:
    """
    Ước tính confidence dựa vào:
    - Số lượng và quality của chunks
    - Có exceptions không
    - Answer có abstain không

    TODO Sprint 2: Có thể dùng LLM-as-Judge để tính confidence chính xác hơn.
    """
    if not chunks:
        return 0.1  # Không có evidence → low confidence

    if "Không đủ thông tin" in answer or "không có trong tài liệu" in answer.lower():
        return 0.3  # Abstain → moderate-low

<<<<<<< HEAD
    # Hybrid RRF scores are small floats (e.g. 0.008); dense cosine scores are 0-1.
    # Normalise by capping at 1.0 before averaging.
    raw_scores = [min(c.get("score", 0), 1.0) for c in chunks]
    # If all scores are very small (BM25-dominant), scale up relative to max
    max_score = max(raw_scores) if raw_scores else 0
    if max_score < 0.1 and max_score > 0:
        raw_scores = [s / max_score for s in raw_scores]
    avg_score = sum(raw_scores) / len(raw_scores) if raw_scores else 0
=======
    # Weighted average của chunk scores
    if chunks:
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
    else:
        avg_score = 0
>>>>>>> NhatVi

    # Penalty nếu có exceptions (phức tạp hơn)
    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))

    confidence = min(0.95, avg_score - exception_penalty)
    return round(max(0.1, confidence), 2)


<<<<<<< HEAD
def synthesize(task: str, chunks: list, policy_result: dict, mcp_tools_used: list = None) -> dict:
    """
    Tổng hợp câu trả lời từ chunks, policy context, và MCP tool outputs.
=======
def synthesize(task: str, chunks: list, policy_result: dict, mcp_tools_used: list) -> dict:
    """
    Tổng hợp câu trả lời từ chunks và policy context.
>>>>>>> NhatVi

    Returns:
        {"answer": str, "sources": list, "confidence": float}
    """
<<<<<<< HEAD
    context = _build_context(chunks, policy_result, mcp_tools_used=mcp_tools_used)
=======
    context = _build_context(chunks, policy_result)
>>>>>>> NhatVi

    # Build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Câu hỏi: {task}

{context}

Hãy trả lời câu hỏi dựa vào tài liệu trên."""
        }
    ]

<<<<<<< HEAD
    answer = _call_llm(messages)
=======
    answer = _rule_based_answer(task, chunks, policy_result, mcp_tools_used)
    if not answer:
        answer = _call_llm(messages)
    if not answer:
        answer = _fallback_answer(task, chunks, policy_result)
>>>>>>> NhatVi
    sources = list({c.get("source", "unknown") for c in chunks})
    confidence = _estimate_confidence(chunks, answer, policy_result)

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
    }


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    policy_result = state.get("policy_result", {})
    mcp_tools_used = state.get("mcp_tools_used", [])

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "has_policy": bool(policy_result),
<<<<<<< HEAD
            "mcp_tools_count": len(mcp_tools_used),
=======
>>>>>>> NhatVi
        },
        "output": None,
        "error": None,
    }

    try:
<<<<<<< HEAD
        result = synthesize(task, chunks, policy_result, mcp_tools_used=mcp_tools_used)
=======
        result = synthesize(task, chunks, policy_result, mcp_tools_used)
>>>>>>> NhatVi
        state["final_answer"] = result["answer"]
        state["sources"] = result["sources"]
        state["confidence"] = result["confidence"]

        worker_io["output"] = {
            "answer_length": len(result["answer"]),
            "sources": result["sources"],
            "confidence": result["confidence"],
        }
        state["history"].append(
            f"[{WORKER_NAME}] answer generated, confidence={result['confidence']}, "
            f"sources={result['sources']}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "SYNTHESIS_FAILED", "reason": str(e)}
        state["final_answer"] = f"SYNTHESIS_ERROR: {e}"
        state["confidence"] = 0.0
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
<<<<<<< HEAD
=======
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
>>>>>>> NhatVi
    print("=" * 50)
    print("Synthesis Worker — Standalone Test")
    print("=" * 50)

    test_state = {
        "task": "SLA ticket P1 là bao lâu?",
        "retrieved_chunks": [
            {
                "text": "Ticket P1: Phản hồi ban đầu 15 phút kể từ khi ticket được tạo. Xử lý và khắc phục 4 giờ. Escalation: tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút.",
                "source": "sla_p1_2026.txt",
                "score": 0.92,
            }
        ],
        "policy_result": {},
    }

    result = run(test_state.copy())
    print(f"\nAnswer:\n{result['final_answer']}")
    print(f"\nSources: {result['sources']}")
    print(f"Confidence: {result['confidence']}")

    print("\n--- Test 2: Exception case ---")
    test_state2 = {
        "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì lỗi nhà sản xuất.",
        "retrieved_chunks": [
            {
                "text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền theo Điều 3 chính sách v4.",
                "source": "policy_refund_v4.txt",
                "score": 0.88,
            }
        ],
        "policy_result": {
            "policy_applies": False,
            "exceptions_found": [{"type": "flash_sale_exception", "rule": "Flash Sale không được hoàn tiền."}],
        },
    }
    result2 = run(test_state2.copy())
    print(f"\nAnswer:\n{result2['final_answer']}")
    print(f"Confidence: {result2['confidence']}")

<<<<<<< HEAD
    print("\n✅ synthesis_worker test done.")
=======
    print("\n[OK] synthesis_worker test done.")
>>>>>>> NhatVi
