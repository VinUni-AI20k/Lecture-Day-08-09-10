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
    Gọi LLM để tổng hợp câu trả lời.
    Ưu tiên OpenAI, fallback sang Gemini nếu có GOOGLE_API_KEY.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                messages=messages,
                temperature=0.1,
                max_tokens=600,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            print(f"[synthesis] OpenAI error: {e}")

    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            model = genai.GenerativeModel(model_name)
            combined = "\n".join([m["content"] for m in messages])
            response = model.generate_content(combined)
            return (response.text or "").strip()
        except Exception as e:
            print(f"[synthesis] Gemini error: {e}")

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

    if policy_result and policy_result.get("exceptions_found"):
        parts.append("\n=== POLICY EXCEPTIONS ===")
        for ex in policy_result["exceptions_found"]:
            parts.append(f"- {ex.get('rule', '')}")

    if not parts:
        return "(Không có context)"

    return "\n\n".join(parts)


def _estimate_confidence(chunks: list, answer: str, policy_result: dict) -> float:
    """
    Sprint 2: Dùng LLM-as-Judge để đánh giá độ tin cậy của câu trả lời.

    Tiêu chí đánh giá:
    - Faithfulness: answer có bám sát context không?
    - Completeness: trả lời đủ các phần của câu hỏi không?
    - Anti-hallucination: không có claim nào ngoài context không?
    """
    # Short-circuit: rõ ràng là abstain hoặc error
    if not chunks:
        return 0.1
    if "[SYNTHESIS ERROR]" in answer:
        return 0.0
    if any(kw in answer for kw in [
        "Không đủ thông tin", "không có trong tài liệu", "not enough information"
    ]):
        return 0.3  # Abstain → moderate-low (bảo thủ nhưng đúng)

    # ── LLM-as-Judge ────────────────────────────────────────────────────────
    context_str = "\n".join([
        f"[{i+1}] {c.get('source', '?')}: {c.get('text', '')[:300]}"
        for i, c in enumerate(chunks[:5])
    ])
    exceptions_note = ""
    if policy_result.get("exceptions_found"):
        exceptions_note = "\nPolicy exceptions da phat hien: " + "; ".join(
            ex.get("rule", "") for ex in policy_result["exceptions_found"]
        )

    judge_prompt = f"""Ban la Quality Evaluator. Danh gia cau tra loi cua AI duoi day dua vao:
1. Faithfulness (0-1): Cau tra loi co chi dung thong tin tu context?
2. Completeness (0-1): Co tra loi du cau hoi khong?
3. Anti-hallucination (0-1): Khong co claim bia ngoai context?

Context:
{context_str}{exceptions_note}

Cau tra loi can danh gia:
{answer}

Tra loi dung 1 dong JSON:
{{"faithfulness": 0.0-1.0, "completeness": 0.0-1.0, "anti_hallucination": 0.0-1.0, "note": "..."}}"""

    try:
        raw = _call_llm([{"role": "user", "content": judge_prompt}])
        import re, json
        # Tìm JSON trong response
        json_match = re.search(r"\{[^\{\}]+\}", raw)
        if json_match:
            scores = json.loads(json_match.group(0))
            faithfulness = float(scores.get("faithfulness", 0.5))
            completeness = float(scores.get("completeness", 0.5))
            anti_halluc  = float(scores.get("anti_hallucination", 0.5))
            # Tính weighted average: anti-hallucination quan trọng nhất
            llm_score = 0.4 * faithfulness + 0.3 * completeness + 0.3 * anti_halluc
            # Penalty nếu có exceptions làm phức tạp
            exception_penalty = 0.03 * len(policy_result.get("exceptions_found", []))
            final = max(0.1, min(0.95, llm_score - exception_penalty))
            return round(final, 2)
    except Exception as e:
        print(f"[synthesis] LLM-as-Judge failed, falling back to heuristic: {e}")

    # Fallback: heuristic nếu LLM-as-Judge không khả dụng
    avg_score = sum(c.get("score", 0.5) for c in chunks) / len(chunks)
    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))
    return round(max(0.1, min(0.95, avg_score - exception_penalty)), 2)


def synthesize(task: str, chunks: list, policy_result: dict) -> dict:
    """
    Tổng hợp câu trả lời từ chunks và policy context.

    Returns:
        {"answer": str, "sources": list, "confidence": float}
    """
    context = _build_context(chunks, policy_result)

    # Build messages with multi-detail extraction emphasis
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Câu hỏi: {task}

{context}

QUAN TRỌNG: 
- Nếu câu hỏi yêu cầu NHIỀU thông tin (ví dụ: "ai nhận thông báo và qua kênh nào", "các bước", "điều kiện"), hãy liệt kê TẤT CẢ các thông tin tìm thấy trong context.
- KHÔNG bỏ sót bất kỳ chi tiết nào được nêu trong tài liệu.
- Nếu có nhiều kênh/người/bước → liệt kê đầy đủ.

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

        # Sprint 2: Kiểm tra nếu confidence quá thấp → trigger HITL
        confidence_threshold = float(os.getenv("HITL_CONFIDENCE_THRESHOLD", "0.4"))
        hitl_triggered = result["confidence"] < confidence_threshold
        state["hitl_triggered"] = hitl_triggered
        if hitl_triggered:
            state["history"].append(
                f"[{WORKER_NAME}] HITL triggered: confidence={result['confidence']} "
                f"< threshold={confidence_threshold}"
            )

        worker_io["output"] = {
            "answer_length": len(result["answer"]),
            "sources": result["sources"],
            "confidence": result["confidence"],
            "hitl_triggered": hitl_triggered,
        }
        state["history"].append(
            f"[{WORKER_NAME}] answer generated, confidence={result['confidence']}, "
            f"sources={result['sources']}, hitl={hitl_triggered}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "SYNTHESIS_FAILED", "reason": str(e)}
        state["final_answer"] = f"SYNTHESIS_ERROR: {e}"
        state["confidence"] = 0.0
        state["hitl_triggered"] = True  # Error → luôn trigger HITL
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Synthesis Worker - Standalone Test")
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
    print(f"HITL triggered: {result.get('hitl_triggered', False)}")

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
            "exceptions_found": [{"type": "flash_sale_exception", "rule": "Flash Sale khong duoc hoan tien."}],
        },
    }
    result2 = run(test_state2.copy())
    print(f"\nAnswer:\n{result2['final_answer']}")
    print(f"Confidence: {result2['confidence']}")
    print(f"HITL triggered: {result2.get('hitl_triggered', False)}")

    print("\n[OK] synthesis_worker test done.")
