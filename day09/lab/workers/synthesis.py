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

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

WORKER_NAME = "synthesis_worker"
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk + CS nội bộ.

Quy tắc nghiêm ngặt (grounded answering):
1. CHỈ trả lời dựa vào "TÀI LIỆU THAM KHẢO" được cung cấp. TUYỆT ĐỐI KHÔNG dùng kiến thức ngoài.
2. Nếu tài liệu không đủ để trả lời → trả lời đúng cụm: "Không đủ thông tin trong tài liệu nội bộ" và đề xuất liên hệ team phụ trách.
3. Trích dẫn bằng số thứ tự chunk: dùng `[1]`, `[2]`, ... ngay sau mỗi câu có fact từ chunk đó. Ví dụ: "SLA P1 là 15 phút [1]."
4. Ở cuối câu trả lời, thêm dòng "Nguồn:" liệt kê mapping `[n] tên_file`.
5. Trả lời súc tích, có cấu trúc (bullet nếu nhiều ý). Không lặp câu hỏi.
6. Nếu "POLICY EXCEPTIONS" xuất hiện → nêu rõ exception TRƯỚC khi kết luận policy_applies.
7. Nếu có "policy_version_note" → nhắc rõ vấn đề temporal scoping và đề xuất xác nhận với team liên quan.
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
    """Gọi LLM (ưu tiên provider có API key trong env) để tổng hợp câu trả lời."""
    errors = []

    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.1,
                max_tokens=600,
            )
            return response.choices[0].message.content
        except Exception as e:
            errors.append(f"openai: {e}")

    if os.getenv("GOOGLE_API_KEY"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-flash")
            combined = "\n".join([m["content"] for m in messages])
            response = model.generate_content(combined)
            return response.text
        except Exception as e:
            errors.append(f"gemini: {e}")

    err_str = "; ".join(errors) if errors else "no LLM provider configured in .env"
    return f"[SYNTHESIS ERROR] Không thể gọi LLM ({err_str})."
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

    # Fallback: trả về message báo lỗi (không hallucinate)
    return "[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env."


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

    if policy_result:
        if policy_result.get("exceptions_found"):
            parts.append("\n=== POLICY EXCEPTIONS ===")
            for ex in policy_result["exceptions_found"]:
                parts.append(
                    f"- ({ex.get('type', 'exception')}) {ex.get('rule', '')} "
                    f"[src: {ex.get('source', 'n/a')}]"
                )
        if policy_result.get("policy_version_note"):
            parts.append(
                "\n=== POLICY VERSION NOTE ===\n"
                f"{policy_result['policy_version_note']}"
            )

    if not parts:
        return "(Không có tài liệu tham khảo — hãy abstain theo quy tắc 2.)"
    if policy_result and policy_result.get("exceptions_found"):
        parts.append("\n=== POLICY EXCEPTIONS ===")
        for ex in policy_result["exceptions_found"]:
            parts.append(f"- {ex.get('rule', '')}")

    if not parts:
        return "(Không có context)"

    return "\n\n".join(parts)


def _estimate_confidence(chunks: list, answer: str, policy_result: dict) -> float:
    """
    Ước tính confidence (không hard-code) dựa trên các tín hiệu thực:
      - Không có chunks → 0.1
      - Abstain keywords → 0.3
      - Max/avg retrieval score của chunks (cosine similarity)
      - Citation present trong answer → boost nhẹ
      - Exceptions found → penalty nhẹ (tăng độ phức tạp)
      - policy_version_note → penalty (temporal ambiguity)
    """
    if not chunks:
        return 0.1

    answer_lc = (answer or "").lower()
    abstain_markers = [
        "không đủ thông tin",
        "không có trong tài liệu",
        "không tìm thấy",
    ]
    if any(m in answer_lc for m in abstain_markers):
        return 0.3

    scores = [float(c.get("score", 0.0)) for c in chunks]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0
    base = 0.6 * max_score + 0.4 * avg_score

    if any(tag in (answer or "") for tag in ["[1]", "[2]", "[3]"]):
        base += 0.05

    exceptions = policy_result.get("exceptions_found", []) if policy_result else []
    base -= 0.05 * len(exceptions)

    if policy_result and policy_result.get("policy_version_note"):
        base -= 0.1

    return round(max(0.1, min(0.95, base)), 2)
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

    # Weighted average của chunk scores
    if chunks:
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
    else:
        avg_score = 0

    # Penalty nếu có exceptions (phức tạp hơn)
    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))

    confidence = min(0.95, avg_score - exception_penalty)
    return round(max(0.1, confidence), 2)


def synthesize(task: str, chunks: list, policy_result: dict) -> dict:
    """
    Tổng hợp câu trả lời từ chunks và policy context.

    Returns:
        {"answer": str, "sources": list, "confidence": float}
    """
    if not chunks:
        answer = (
            "Không đủ thông tin trong tài liệu nội bộ để trả lời câu hỏi này. "
            "Vui lòng liên hệ team phụ trách (CS / IT Helpdesk) để được hỗ trợ trực tiếp."
        )
        return {
            "answer": answer,
            "sources": [],
            "confidence": _estimate_confidence([], answer, policy_result),
        }

    context = _build_context(chunks, policy_result)

    user_prompt = (
        f"Câu hỏi: {task}\n\n"
        f"{context}\n\n"
        "Yêu cầu format:\n"
        "- Trả lời ngắn gọn, dùng `[n]` sau mỗi fact để cite chunk tương ứng.\n"
        "- Cuối câu trả lời thêm dòng `Nguồn:` liệt kê mapping `[n] tên_file`.\n"
        "- Nếu context không đủ → abstain theo quy tắc 2."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
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
