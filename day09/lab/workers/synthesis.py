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
import re

WORKER_NAME = "synthesis_worker"

SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk nội bộ.

Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context được cung cấp. KHÔNG dùng kiến thức ngoài.
2. Nếu context không đủ để trả lời → nói rõ "Không đủ thông tin trong tài liệu nội bộ".
3. Trích dẫn nguồn cuối mỗi câu quan trọng: [tên_file].
4. Trả lời súc tích, có cấu trúc. Không dài dòng.
5. Nếu có exceptions/ngoại lệ → nêu rõ ràng trước khi kết luận.
"""


def _extract_task_from_messages(messages: list) -> str:
    user_message = messages[-1]["content"] if messages else ""
    match = re.search(r"Câu hỏi:\s*(.+?)(?:\n\n|$)", user_message, flags=re.DOTALL)
    return match.group(1).strip() if match else ""


def _normalize(text: str) -> str:
    cleaned = re.sub(r"^\W+", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _sentence_split(text: str) -> list:
    cleaned = text.replace("\r", " ").replace("\n", " ")
    parts = re.split(r"(?<=[\.\?!])\s+|\s+-\s+", cleaned)
    return [_normalize(part) for part in parts if _normalize(part)]


def _task_keywords(task: str) -> set:
    return set(re.findall(r"[a-z0-9_]+", task.lower()))


def _top_relevant_snippets(task: str, chunks: list, limit: int = 3) -> list:
    keywords = _task_keywords(task)
    candidates = []

    for chunk in chunks:
        source = chunk.get("source", "unknown")
        score = float(chunk.get("score", 0) or 0)
        seen = set()
        for sentence in _sentence_split(chunk.get("text", "")):
            lowered = sentence.lower()
            overlap = len(keywords & set(re.findall(r"[a-z0-9_]+", lowered)))
            if overlap == 0:
                continue
            if sentence.lower().startswith(("source:", "department:", "effective date:", "access:")):
                continue
            if any(marker in sentence.lower() for marker in [" source:", " department:", " effective date:", " access:"]):
                continue
            if sentence.startswith(("===", "Section ", "Phần ")):
                continue
            if re.fullmatch(r"[A-Z0-9\s\-]+", sentence):
                continue
            if sentence in seen:
                continue
            seen.add(sentence)
            candidates.append((overlap, score, source, sentence))

    candidates.sort(key=lambda item: (item[0], item[1], len(item[3])), reverse=True)

    chosen = []
    used_sentences = set()
    for _, _, source, sentence in candidates:
        if sentence in used_sentences:
            continue
        used_sentences.add(sentence)
        chosen.append(f"- {sentence} [{source}]")
        if len(chosen) >= limit:
            break
    return chosen


def _fallback_grounded_answer(task: str, chunks: list, policy_result: dict) -> str:
    if policy_result.get("policy_version_note"):
        source = policy_result.get("source", ["policy_refund_v4.txt"])[0]
        return (
            "Không đủ thông tin trong tài liệu nội bộ để khẳng định chi tiết của policy phiên bản cũ. "
            f"{policy_result['policy_version_note']} [{source}]"
        )

    if policy_result.get("exceptions_found"):
        lines = []
        for exception in policy_result["exceptions_found"]:
            lines.append(f"- Ngoại lệ áp dụng: {exception.get('rule', '')} [{exception.get('source', 'unknown')}]")

        if policy_result.get("required_approvers"):
            approvers = ", ".join(policy_result["required_approvers"])
            lines.append(f"- Chuỗi phê duyệt cần có: {approvers} [access_control_sop.txt]")
        if policy_result.get("emergency_override"):
            lines.append("- Trường hợp khẩn cấp được phép cấp quyền tạm thời theo SOP [access_control_sop.txt]")

        lines.extend(_top_relevant_snippets(task, chunks, limit=2))
        return "\n".join(lines[:4])

    snippet_lines = _top_relevant_snippets(task, chunks, limit=4)
    if snippet_lines:
        return "\n".join(snippet_lines)

    return "Không đủ thông tin trong tài liệu nội bộ để trả lời câu hỏi này."


def _call_llm(messages: list) -> str:
    """
    Gọi LLM để tổng hợp câu trả lời.
    TODO Sprint 2: Implement với OpenAI hoặc Gemini.
    """
    # Option A: OpenAI
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,  # Low temperature để grounded
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception:
        pass

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

    return "__USE_DETERMINISTIC_FALLBACK__"


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
            parts.append(f"- {ex.get('rule', '')} [{ex.get('source', 'unknown')}]")

    if policy_result and policy_result.get("policy_version_note"):
        parts.append("\n=== POLICY VERSION NOTE ===")
        parts.append(policy_result["policy_version_note"])

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

    if "Không đủ thông tin" in answer or "khong du thong tin" in answer.lower():
        return 0.3  # Abstain → moderate-low

    if policy_result.get("policy_version_note"):
        return 0.35

    # Weighted average của chunk scores
    if chunks:
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
    else:
        avg_score = 0

    # Penalty nếu có exceptions (phức tạp hơn)
    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))

    confidence = min(0.95, avg_score - exception_penalty + 0.05)
    return round(max(0.1, confidence), 2)


def synthesize(task: str, chunks: list, policy_result: dict) -> dict:
    """
    Tổng hợp câu trả lời từ chunks và policy context.

    Returns:
        {"answer": str, "sources": list, "confidence": float}
    """
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
    if answer == "__USE_DETERMINISTIC_FALLBACK__":
        answer = _fallback_grounded_answer(task, chunks, policy_result)
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

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
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
        if result["confidence"] < 0.4:
            state["hitl_triggered"] = True

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


# ————————————————————————————————————————————————
# Test độc lập
# ————————————————————————————————————————————————

if __name__ == "__main__":
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
            "exceptions_found": [{"type": "flash_sale_exception", "rule": "Đơn hàng Flash Sale không được hoàn tiền.", "source": "policy_refund_v4.txt"}],
        },
    }
    result2 = run(test_state2.copy())
    print(f"\nAnswer:\n{result2['final_answer']}")
    print(f"Confidence: {result2['confidence']}")

    print("\n✅ synthesis_worker test done.")
