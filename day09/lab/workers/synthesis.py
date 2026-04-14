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

import json
import os
import re
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

WORKER_NAME = "synthesis_worker"

SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk nội bộ.

Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context được cung cấp. KHÔNG dùng kiến thức ngoài.
2. Nếu context không đủ để trả lời → nói rõ "Không đủ thông tin trong tài liệu nội bộ".
3. Trích dẫn nguồn cuối mỗi câu quan trọng: [tên_file].
4. Trả lời súc tích, có cấu trúc. Không dài dòng.
5. Nếu có exceptions/ngoại lệ → nêu rõ ràng trước khi kết luận.
"""


def _call_llm(messages: list) -> str:
    """
    Gọi Groq chat completion API để tổng hợp câu trả lời.
    """
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

    if not api_key:
        return "[SYNTHESIS ERROR] Không tìm thấy GROQ_API_KEY trong .env."

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 500,
        "stream": False,
    }

    request = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError) as exc:
        return f"[SYNTHESIS ERROR] Không thể gọi Groq API: {exc}"


def _build_fallback_answer(task: str, chunks: list, policy_result: dict) -> str:
    """Local grounded fallback nếu Groq không khả dụng."""
    lines = []

    if policy_result and policy_result.get("exceptions_found"):
        lines.append("Theo chính sách nội bộ, yêu cầu này bị ảnh hưởng bởi các ngoại lệ sau:")
        for ex in policy_result["exceptions_found"]:
            lines.append(f"- {ex.get('rule', '')} [{ex.get('source', 'unknown')}]")
    elif policy_result and policy_result.get("policy_name") == "access_control_sop":
        lines.append(policy_result.get("summary", "Access Control SOP áp dụng."))
        approvers = policy_result.get("required_approvers", [])
        if approvers:
            lines.append(f"Yêu cầu phê duyệt: {', '.join(approvers)}.")
    elif chunks:
        lines.append("Dưới đây là bằng chứng trích từ tài liệu nội bộ:")
    else:
        lines.append("Không đủ thông tin trong tài liệu nội bộ để trả lời câu hỏi này.")

    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "unknown")
        text = chunk.get("text", "").strip()
        if text:
            lines.append(f"[{i}] {source}: {text}")

    return "\n".join(lines)


def _build_context(chunks: list, policy_result: dict) -> str:
    """Xây dựng context string từ chunks và policy result."""
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

    if not parts:
        return "(Không có context)"

    return "\n\n".join(parts)


def _contains_citation(text: str) -> bool:
    return bool(re.search(r"\[[^\]]+\]", text))


def _is_abstain_answer(text: str) -> bool:
    lower = (text or "").lower()
    return (
        "không đủ thông tin" in lower
        or "không có trong tài liệu" in lower
        or "không thể tìm thấy" in lower
        or "tôi không biết" in lower
        or "insufficient" in lower
    )


def _ensure_citations(answer: str, sources: list[str]) -> str:
    """Ensure answer includes citation markers when evidence exists."""
    if not sources:
        return answer
    if _contains_citation(answer):
        return answer
    citation_tail = " ".join([f"[{i + 1}] {src}" for i, src in enumerate(sources)])
    return f"{answer}\n\nNguồn tham chiếu: {citation_tail}".strip()


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

    scores = sorted([float(c.get("score", 0.0)) for c in chunks], reverse=True)
    top1 = scores[0] if scores else 0.0
    top2 = scores[1] if len(scores) > 1 else 0.0

    # Ưu tiên evidence mạnh nhất để tránh dilution bởi chunk yếu.
    evidence_core = (0.75 * top1) + (0.25 * top2)

    evidence_bonus = min(0.12, 0.02 * max(0, len(chunks) - 1))
    citation_bonus = 0.05 if _contains_citation(answer) else 0.0
    policy_bonus = 0.0
    if policy_result.get("required_approvers"):
        policy_bonus += 0.04
    if policy_result.get("exceptions_found"):
        policy_bonus += 0.02

    exception_penalty = 0.03 * len(policy_result.get("exceptions_found", []))

    if _is_abstain_answer(answer):
        abstain_conf = 0.3 + (0.35 * evidence_core) + (0.5 * citation_bonus)
        return round(max(0.2, min(0.75, abstain_conf)), 2)

    confidence = evidence_core + evidence_bonus + citation_bonus + policy_bonus - exception_penalty
    return round(max(0.1, min(0.95, confidence)), 2)


def synthesize(task: str, chunks: list, policy_result: dict) -> dict:
    """
    Tổng hợp câu trả lời từ chunks và policy context.

    Returns:
        {"answer": str, "sources": list, "confidence": float}
    """
    sources = list(dict.fromkeys([c.get("source", "unknown") for c in chunks if c]))

    # Contract rule: if no evidence chunks, abstain and avoid hallucination.
    if not chunks:
        return {
            "answer": "Không đủ thông tin trong tài liệu nội bộ để trả lời câu hỏi này.",
            "sources": [],
            "confidence": 0.1,
        }

    context = _build_context(chunks, policy_result)

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

    answer = _call_llm(messages)
    if answer.startswith("[SYNTHESIS ERROR]"):
        answer = _build_fallback_answer(task, chunks, policy_result)
    answer = _ensure_citations(answer, sources)
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

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("worker_io_logs", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "has_policy": bool(policy_result),
        },
        "output": None,
        "error": None,
    }

    try:
        result = synthesize(task, chunks, policy_result)
        state["final_answer"] = result["answer"]
        state["sources"] = result["sources"]
        state["confidence"] = result["confidence"]
        if state["confidence"] < 0.4:
            state["hitl_triggered"] = True
            state["history"].append(f"[{WORKER_NAME}] low confidence -> hitl_triggered=True")

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

    state["worker_io_logs"].append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
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

    print("\n✅ synthesis_worker test done.")
