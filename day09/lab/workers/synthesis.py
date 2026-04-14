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


JUDGE_PROMPT = """Bạn là một chuyên gia kiểm định chất lượng AI (QA Judge).
Nhiệm vụ của bạn là đánh giá mức độ tin cậy (Confidence Score) của câu trả lời dựa trên Context và Câu hỏi.

Tiêu chí đánh giá:
1. Groundedness: Câu trả lời có hoàn toàn dựa trên Context không? (Không có thông tin ngoài)
2. Accuracy: Thông tin trong câu trả lời có chính xác so với Context không?
3. Completeness: Câu trả lời có giải quyết được vấn đề trong Câu hỏi không?
4. Citation: Các thông tin quan trọng có được trích dẫn nguồn [file_name] đầy đủ không?

Quy tắc chấm điểm:
- 1.0: Hoàn hảo, đầy đủ bằng chứng, có trích dẫn, không lỗi.
- 0.7-0.9: Đúng và đủ nhưng có thể cải thiện cách diễn đạt hoặc trích dẫn.
- 0.4-0.6: Trả lời được một phần hoặc thông tin hơi mơ hồ nhưng vẫn có căn cứ.
- 0.1-0.3: Không đủ thông tin để trả lời (Abstain) hoặc trả lời sai lệch nhiều.

CHỈ trả về một con số duy nhất từ 0.0 đến 1.0. KHÔNG giải thích gì thêm.
"""


def _call_llm(messages: list, model: str = "gpt-4o-mini", temperature: float = 0.1) -> str:
    """
    Gọi LLM để thực hiện các tác vụ (Synthesis hoặc Judge).
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=500 if temperature > 0 else 10, # Judge chỉ cần token ngắn
        )
        return response.choices[0].message.content.strip()
    except Exception:
        pass

    return ""


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


def _estimate_confidence(task: str, context: str, answer: str) -> float:
    """
    Ước tính confidence sử dụng LLM-as-Judge.
    """
    # Nếu answer báo không có thông tin ngay từ đầu
    if "Không đủ thông tin" in answer or "không có trong tài liệu" in answer.lower():
        return 0.2

    judge_messages = [
        {"role": "system", "content": JUDGE_PROMPT},
        {
            "role": "user",
            "content": f"""---
CÂU HỎI: {task}
---
CONTEXT:
{context}
---
CÂU TRẢ LỜI CỦA AI:
{answer}
---
HÃY CHẤM ĐIỂM CONFIDENCE (0.0 - 1.0):"""
        }
    ]

    score_str = _call_llm(judge_messages, temperature=0)
    
    try:
        # Trích xuất số từ chuỗi trả về (đề phòng LLM trả về "0.8" hoặc "Score: 0.8")
        import re
        match = re.search(r"([0-9]*\.[0-9]+|[0-9]+)", score_str)
        if match:
            confidence = float(match.group(1))
            return round(min(1.0, max(0.0, confidence)), 2)
    except (ValueError, TypeError):
        pass

    # Fallback nếu Judge lỗi
    return 0.5


def synthesize(task: str, chunks: list, policy_result: dict) -> dict:
    """
    Tổng hợp câu trả lời từ chunks và policy context.

    Returns:
        {"answer": str, "sources": list, "confidence": float, "hitl_flag": bool}
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
    if not answer:
        answer = "[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env."
        
    sources = list({c.get("source", "unknown") for c in chunks})
    confidence = _estimate_confidence(task, context, answer)
    
    # HITL trigger: Nếu confidence < 0.6, yêu cầu con người kiểm tra
    hitl_flag = confidence < 0.6

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "hitl_flag": hitl_flag,
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
        state["hitl_flag"] = result["hitl_flag"]

        worker_io["output"] = {
            "answer_length": len(result["answer"]),
            "sources": result["sources"],
            "confidence": result["confidence"],
            "hitl_flag": result["hitl_flag"],
        }
        
        hitl_status = " [HITL TRIGGERED]" if result["hitl_flag"] else ""
        state["history"].append(
            f"[{WORKER_NAME}] answer generated, confidence={result['confidence']}{hitl_status}, "
            f"sources={result['sources']}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "SYNTHESIS_FAILED", "reason": str(e)}
        state["final_answer"] = f"SYNTHESIS_ERROR: {e}"
        state["confidence"] = 0.0
        state["hitl_flag"] = True # Lỗi thì nên qua HITL
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
    print(f"HITL Flag: {result['hitl_flag']}")

    print("\n--- Test 2: Low confidence / Abstain case ---")
    test_state2 = {
        "task": "Làm sao để hack NASA?",
        "retrieved_chunks": [],
        "policy_result": {},
    }
    result2 = run(test_state2.copy())
    print(f"\nAnswer:\n{result2['final_answer']}")
    print(f"Confidence: {result2['confidence']}")
    print(f"HITL Flag: {result2['hitl_flag']}")

    print("\n✅ synthesis_worker test done.")
