"""
workers/synthesis.py — Synthesis Worker
Sprint 2: Tổng hợp câu trả lời từ retrieved_chunks và policy_result.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: evidence từ retrieval_worker
    - policy_result: kết quả từ policy_tool_worker

Output (vào AgentState):
    - final_answer: câu trả lời cuối với citation [1], [2], ...
    - sources: danh sách nguồn tài liệu được cite
    - confidence: mức độ tin cậy (0.0 - 1.0)
    - hitl_triggered: True nếu confidence < HITL_THRESHOLD

Gọi độc lập để test:
    python workers/synthesis.py
"""

import os
from datetime import datetime, timezone

WORKER_NAME = "synthesis_worker"
HITL_THRESHOLD = 0.4
ABSTAIN_MESSAGE = "Không đủ thông tin trong tài liệu nội bộ."
LLM_ERROR_SENTINEL = "__LLM_CALL_FAILED__"

SYSTEM_PROMPT = f"""Bạn là trợ lý IT Helpdesk nội bộ.

Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context được cung cấp. KHÔNG dùng kiến thức ngoài.
2. Nếu context không đủ để trả lời → trả lời CHÍNH XÁC: "{ABSTAIN_MESSAGE}".
3. Trích dẫn nguồn bằng số chunk tương ứng ở cuối mỗi câu quan trọng: [1], [2], ... (KHÔNG ghi tên file).
4. Nếu có Policy Exceptions → nêu rõ ràng TRƯỚC khi kết luận.
5. Trả lời súc tích, có cấu trúc, tiếng Việt. Không lặp lại câu hỏi.
6. Không suy đoán, không thêm khuyến nghị ngoài context.
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _call_llm(messages: list) -> str:
    """Gọi LLM với fallback chain: OpenAI → Gemini → `LLM_ERROR_SENTINEL` (caller map thành abstain)."""
    # Option A: OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[synthesis] OpenAI failed: {e}")

    # Option B: Gemini
    if os.getenv("GOOGLE_API_KEY"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-flash")
            combined = "\n\n".join([m["content"] for m in messages])
            response = model.generate_content(combined)
            return response.text.strip()
        except Exception as e:
            print(f"[synthesis] Gemini failed: {e}")

    # Trả về sentinel thay vì string-answer → synthesize() sẽ map thành abstain + HITL
    return LLM_ERROR_SENTINEL


def _build_context(chunks: list, policy_result: dict) -> str:
    """Context string với chunks đánh số [1], [2] khớp với citation format."""
    parts = []

    if chunks:
        parts.append("=== TÀI LIỆU THAM KHẢO ===")
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "unknown")
            text = chunk.get("text", "")
            score = chunk.get("score", 0)
            parts.append(f"[{i}] Nguồn: {source} (relevance: {score:.2f})\n{text}")

    if policy_result and policy_result.get("exceptions_found"):
        parts.append("\n=== POLICY EXCEPTIONS (bắt buộc nêu rõ) ===")
        for ex in policy_result["exceptions_found"]:
            rule = ex.get("rule") or ex.get("type", "")
            parts.append(f"- {rule}")

    if policy_result and policy_result.get("policy_version_note"):
        parts.append(f"\n=== LƯU Ý VERSION ===\n{policy_result['policy_version_note']}")

    return "\n\n".join(parts) if parts else "(Không có context)"


def _is_abstain(answer: str) -> bool:
    """Phát hiện câu trả lời từ chối/không đủ thông tin."""
    low = answer.lower()
    markers = [
        "không đủ thông tin",
        "không có trong tài liệu",
        "không tìm thấy",
        "tài liệu không đề cập",
    ]
    return any(m in low for m in markers)


def _estimate_confidence(chunks: list, answer: str, policy_result: dict) -> float:
    """
    Heuristic confidence:
    - No chunks → 0.1 (abstain bắt buộc)
    - Answer abstain → 0.3
    - Có chunks: base = avg(top-k retrieval score), scale về [0.4, 0.9]
    - Trừ 0.05 mỗi exception (tăng độ phức tạp → giảm tin cậy)
    - Nếu answer có citation [n] → +0.05 (có grounding rõ)
    """
    if not chunks:
        return 0.1

    if _is_abstain(answer):
        return 0.3

    scores = [c.get("score", 0) for c in chunks]
    avg_score = sum(scores) / len(scores) if scores else 0
    # Scale: score 0.5 → 0.55, score 0.9 → 0.87
    base = 0.4 + 0.55 * avg_score

    has_citation = any(f"[{i}]" in answer for i in range(1, len(chunks) + 1))
    if has_citation:
        base += 0.05

    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []) if policy_result else [])
    confidence = base - exception_penalty

    return round(max(0.1, min(0.95, confidence)), 2)


def synthesize(task: str, chunks: list, policy_result: dict) -> dict:
    """
    Tổng hợp câu trả lời. Abstain sớm nếu không có evidence (tiết kiệm LLM call).

    Returns:
        {"answer": str, "sources": list, "confidence": float, "abstained": bool}
    """
    # Early abstain: không có chunks → không gọi LLM, tránh hallucinate
    if not chunks:
        return {
            "answer": ABSTAIN_MESSAGE,
            "sources": [],
            "confidence": 0.1,
            "abstained": True,
        }

    context = _build_context(chunks, policy_result)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Câu hỏi: {task}\n\n"
                f"{context}\n\n"
                f"Hãy trả lời câu hỏi dựa VÀO CONTEXT TRÊN. "
                f"Nhớ trích dẫn [1], [2], ... theo số chunk."
            ),
        },
    ]

    answer = _call_llm(messages)

    # LLM call thất bại → map thành abstain + confidence thấp (đảm bảo HITL trigger)
    if answer == LLM_ERROR_SENTINEL:
        return {
            "answer": f"{ABSTAIN_MESSAGE} (LLM call failed — kiểm tra API key)",
            "sources": [],
            "confidence": 0.1,
            "abstained": True,
            "llm_error": True,
        }

    # Chỉ cite source của chunk thực sự được tham chiếu trong answer
    cited_sources = []
    for i, chunk in enumerate(chunks, 1):
        if f"[{i}]" in answer:
            src = chunk.get("source", "unknown")
            if src not in cited_sources:
                cited_sources.append(src)
    # Nếu LLM quên cite dù có chunks → vi phạm contract → hạ confidence, trigger HITL
    missing_citation = not cited_sources
    if missing_citation:
        cited_sources = list({c.get("source", "unknown") for c in chunks})

    confidence = _estimate_confidence(chunks, answer, policy_result)
    if missing_citation:
        confidence = min(confidence, 0.35)  # dưới HITL_THRESHOLD → buộc review

    return {
        "answer": answer,
        "sources": cited_sources,
        "confidence": confidence,
        "abstained": _is_abstain(answer),
        "llm_error": False,
        "missing_citation": missing_citation,
    }


def run(state: dict) -> dict:
    """Worker entry point — gọi từ graph.py."""
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    policy_result = state.get("policy_result", {})

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("worker_io_logs", [])
    state["workers_called"].append(WORKER_NAME)
    # Chỉ khởi tạo nếu chưa có; không ghi đè True đã set từ worker trước trong cùng run
    state.setdefault("hitl_triggered", False)

    worker_io = {
        "worker": WORKER_NAME,
        "timestamp": _now_iso(),
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "has_policy": bool(policy_result),
            "exceptions_count": len(policy_result.get("exceptions_found", []) if policy_result else []),
        },
        "output": None,
        "error": None,
    }

    try:
        result = synthesize(task, chunks, policy_result)
        state["final_answer"] = result["answer"]
        state["sources"] = result["sources"]
        state["confidence"] = result["confidence"]

        # HITL trigger khi confidence thấp hoặc LLM lỗi
        if result["confidence"] < HITL_THRESHOLD or result.get("llm_error"):
            state["hitl_triggered"] = True
            reason = "llm_error" if result.get("llm_error") else f"confidence={result['confidence']} < {HITL_THRESHOLD}"
            state["history"].append(f"[{WORKER_NAME}] HITL triggered ({reason})")

        worker_io["output"] = {
            "answer_length": len(result["answer"]),
            "sources": result["sources"],
            "sources_count": len(result["sources"]),
            "confidence": result["confidence"],
            "abstained": result["abstained"],
            "hitl_triggered": state.get("hitl_triggered", False),
        }
        state["history"].append(
            f"[{WORKER_NAME}] answer_len={len(result['answer'])}, "
            f"confidence={result['confidence']}, sources={result['sources']}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "SYNTHESIS_FAILED", "reason": str(e)}
        state["final_answer"] = f"SYNTHESIS_ERROR: {e}"
        state["sources"] = []
        state["confidence"] = 0.0
        state["hitl_triggered"] = True
        worker_io["output"] = {
            "answer_length": len(state["final_answer"]),
            "sources": [],
            "sources_count": 0,
            "confidence": 0.0,
            "abstained": False,
            "hitl_triggered": True,
        }
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state["worker_io_logs"].append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Synthesis Worker — Standalone Test")
    print("=" * 60)

    # Test 1: Single chunk, straightforward
    print("\n--- Test 1: Single chunk (SLA P1) ---")
    s1 = run({
        "task": "SLA ticket P1 là bao lâu?",
        "retrieved_chunks": [{
            "text": "Ticket P1: Phản hồi ban đầu 15 phút. Xử lý và khắc phục 4 giờ. "
                    "Escalation: tự động escalate lên Senior Engineer nếu không phản hồi trong 10 phút.",
            "source": "sla_p1_2026.txt",
            "score": 0.92,
        }],
        "policy_result": {},
    })
    print(f"Answer:\n{s1['final_answer']}")
    print(f"Sources: {s1['sources']} | Confidence: {s1['confidence']} | HITL: {s1.get('hitl_triggered')}")

    # Test 2: Exception case
    print("\n--- Test 2: Flash Sale exception ---")
    s2 = run({
        "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì lỗi nhà sản xuất.",
        "retrieved_chunks": [{
            "text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền theo Điều 3 chính sách v4.",
            "source": "policy_refund_v4.txt",
            "score": 0.88,
        }],
        "policy_result": {
            "policy_applies": False,
            "exceptions_found": [
                {"type": "flash_sale_exception", "rule": "Flash Sale không được hoàn tiền."}
            ],
        },
    })
    print(f"Answer:\n{s2['final_answer']}")
    print(f"Sources: {s2['sources']} | Confidence: {s2['confidence']}")

    # Test 3: No chunks → early abstain (không gọi LLM)
    print("\n--- Test 3: No chunks (abstain) ---")
    s3 = run({
        "task": "ERR-403-AUTH là lỗi gì?",
        "retrieved_chunks": [],
        "policy_result": {},
    })
    print(f"Answer: {s3['final_answer']}")
    print(f"Confidence: {s3['confidence']} | HITL: {s3.get('hitl_triggered')}")
    assert s3["confidence"] == 0.1, "Expected low confidence for abstain"
    assert s3.get("hitl_triggered") is True, "Expected HITL for no-chunks abstain"

    # Test 4: Multi-chunk (citation test)
    print("\n--- Test 4: Multi-chunk (P1 2am + Level 2 emergency) ---")
    s4 = run({
        "task": "P1 lúc 2am cần cấp quyền Level 2 emergency — quy trình thế nào?",
        "retrieved_chunks": [
            {"text": "P1 notification: Slack + email + PagerDuty. Auto-escalate sau 10 phút không phản hồi.",
             "source": "sla_p1_2026.txt", "score": 0.85},
            {"text": "Level 2 access: yêu cầu Line Manager + IT Admin. Emergency bypass được phép cho Level 2.",
             "source": "access_control_sop.txt", "score": 0.80},
        ],
        "policy_result": {},
    })
    print(f"Answer:\n{s4['final_answer']}")
    print(f"Sources: {s4['sources']} | Confidence: {s4['confidence']}")

    print("\n✅ synthesis_worker test done.")
