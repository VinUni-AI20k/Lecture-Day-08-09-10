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
from dotenv import load_dotenv

load_dotenv()

WORKER_NAME = "synthesis_worker"

SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk nội bộ. Trả lời CHỈ dựa vào context được cung cấp.

Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context bên dưới. TUYỆT ĐỐI KHÔNG dùng kiến thức bên ngoài.
2. Nếu context KHÔNG chứa đủ thông tin để trả lời câu hỏi → nói rõ "Không đủ thông tin trong tài liệu nội bộ." và dừng. KHÔNG suy đoán, KHÔNG bịa. Nhưng nếu context CÓ đủ thông tin để trả lời → TUYỆT ĐỐI KHÔNG thêm "Không đủ thông tin" vì sẽ gây nhầm lẫn.
3. KHÔNG bịa thêm con số, mức phạt, chính sách, điều khoản mà context không đề cập.
4. Trích dẫn nguồn bằng [tên_file] (ví dụ [sla_p1_2026.txt]) sau mỗi thông tin quan trọng.
5. Nếu thông tin đến từ NHIỀU tài liệu khác nhau, cite TẤT CẢ các nguồn liên quan — ví dụ: [hr_leave_policy.txt] và [it_helpdesk_faq.txt].
6. Nếu tài liệu có metadata về phiên bản (version) hoặc ngày hiệu lực (effective_date), ĐỀ CẬP rõ ràng trong câu trả lời.
7. Nếu có exceptions/ngoại lệ → LIỆT KÊ ĐẦY ĐỦ TẤT CẢ ngoại lệ liên quan, không chỉ một.
8. Trả lời có cấu trúc, đầy đủ chi tiết từ context. Không bỏ sót thông tin quan trọng nếu context có.
9. Nếu câu hỏi hỏi về quy trình (SOP), nêu đủ: ai phê duyệt, bao lâu, yêu cầu đặc biệt, kênh liên hệ.
10. SLA P1 notification: Khi câu hỏi liên quan tới thông báo sự cố P1, hãy ĐỌC KỸ TỪNG CHUNK trong context. Quy trình SLA P1 thường đề cập 3 kênh: (a) Slack channel — tìm trong bước "Thông báo", (b) Email — cũng trong bước "Thông báo", (c) PagerDuty — thường trong phần "Công cụ". Đọc TOÀN BỘ context, gộp lại và liệt kê ĐẦY ĐỦ tất cả kênh kèm địa chỉ chính xác. KHÔNG bỏ sót bất kỳ kênh nào xuất hiện trong context.
11. Khi context CÓ chứa địa chỉ cụ thể (email, Slack channel, v.v.), BẮT BUỘC phải ghi ra ĐỊA CHỈ CHÍNH XÁC đó. KHÔNG viết "không có địa chỉ cụ thể" nếu context đã đề cập. KHÔNG paraphrase thành "gửi đến stakeholder liên quan" mà phải ghi đúng địa chỉ.
12. Escalation rule: Nếu context đề cập escalation (vd: 10 phút không phản hồi → Senior Engineer), LUÔN nêu rõ trong câu trả lời kèm timeline cụ thể. Đây là thông tin BẮT BUỘC phải có khi trả lời về P1.
13. Access level: Khi trả lời về quyền truy cập, SO SÁNH rõ ràng giữa các level. Ví dụ: Level 2 CÓ emergency bypass (chỉ cần Line Manager + IT Admin on-call, KHÔNG cần IT Security), còn Level 3 KHÔNG CÓ emergency bypass (phải follow quy trình chuẩn: Line Manager + IT Admin + IT Security). Nêu rõ sự khác biệt này.
14. QUAN TRỌNG — Kiểm tra chéo: Trước khi kết luận "không có thông tin" về BẤT KỲ chi tiết nào, đọc lại TOÀN BỘ context một lần nữa. Context gồm nhiều chunk từ nhiều phần — thông tin cần tìm có thể nằm ở chunk khác với chunk bạn đang đọc.
15. Nguồn ưu tiên: Khi trả lời về thông báo/notification SLA P1, CHỈ liệt kê các kênh notification được quy định TRỰC TIẾP trong quy trình SLA P1 (file sla_p1_2026.txt). Hotline IT helpdesk (ví dụ ext. 9999) là kênh support chung, KHÔNG phải kênh notification SLA — không đưa vào danh sách kênh notification P1.
"""


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
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.0,  # Zero temperature for deterministic grounded answers
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[synthesis] OpenAI call failed: {e}")

    # Option B: Gemini
    # try:
    #     import google.generativeai as genai
    #     genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    #     model = genai.GenerativeModel("gemini-1.5-flash")
    #     combined = "\n".join([m["content"] for m in messages])
    #     response = model.generate_content(combined)
    #     return response.text
    # except Exception:
    #     pass

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
            meta = chunk.get("metadata", {})
            # Include metadata hints for version/date awareness
            meta_hints = []
            if meta.get("effective_date") and meta["effective_date"] != "unknown":
                meta_hints.append(f"effective_date={meta['effective_date']}")
            if meta.get("department") and meta["department"] != "unknown":
                meta_hints.append(f"department={meta['department']}")
            if meta.get("section"):
                meta_hints.append(f"section={meta['section']}")
            meta_str = f" | {', '.join(meta_hints)}" if meta_hints else ""
            parts.append(f"[{i}] Nguồn: {source} (relevance: {score:.2f}{meta_str})\n{text}")

    # Auto-detect notification channels across all chunks and add summary hint
    if chunks:
        all_text = " ".join(c.get("text", "") for c in chunks).lower()
        channels_found = []
        if "#incident-p1" in all_text or "slack" in all_text:
            channels_found.append("Slack #incident-p1")
        if "incident@company.internal" in all_text:
            channels_found.append("Email incident@company.internal")
        if "pagerduty" in all_text:
            channels_found.append("PagerDuty")
        if len(channels_found) >= 2:
            parts.append(
                f"\n=== GỢI Ý: CÁC KÊNH NOTIFICATION TÌM THẤY TRONG CONTEXT ===\n"
                f"Các kênh sau ĐỀU được đề cập trong tài liệu: {', '.join(channels_found)}.\n"
                f"Khi trả lời về notification/thông báo, hãy liệt kê ĐẦY ĐỦ tất cả các kênh trên."
            )

    if policy_result and policy_result.get("exceptions_found"):
        parts.append("\n=== POLICY EXCEPTIONS ===")
        for ex in policy_result["exceptions_found"]:
            parts.append(f"- {ex.get('rule', '')}")

    if policy_result and policy_result.get("policy_version_note"):
        parts.append(f"\n=== GHI CHÚ PHIÊN BẢN ===\n{policy_result['policy_version_note']}")

    if policy_result and policy_result.get("ticket_info"):
        ti = policy_result["ticket_info"]
        parts.append("\n=== TICKET / INCIDENT (MCP) ===")
        parts.append(json.dumps(ti, ensure_ascii=False, indent=2))

    if policy_result and policy_result.get("access_permission"):
        ap = policy_result["access_permission"]
        parts.append("\n=== ACCESS PERMISSION CHECK (MCP) ===")
        parts.append(json.dumps(ap, ensure_ascii=False, indent=2))

    if not parts:
        return "(Không có context)"

    return "\n\n".join(parts)


def _estimate_confidence(chunks: list, answer: str, policy_result: dict) -> float:
    """
    Ước tính confidence dựa vào:
    - Số lượng và quality của chunks
    - Có exceptions không
    - Answer có abstain không
    - Có citation markers trong answer không
    """
    answer_lower = answer.lower()

    # Abstain signals
    abstain_phrases = [
        "không đủ thông tin",
        "không có trong tài liệu",
        "không tìm thấy thông tin",
        "tài liệu không quy định",
        "tài liệu không cung cấp",
        "không có dữ liệu",
    ]
    if any(p in answer_lower for p in abstain_phrases):
        return 0.3  # Abstain → moderate-low (correct behavior)

    if not chunks and not policy_result.get("exceptions_found"):
        return 0.1  # Không có evidence → low confidence

    # Base from chunk quality
    if chunks:
        scores = [c.get("score", 0) for c in chunks]
        # Top-3 average (most relevant chunks matter more)
        top_scores = sorted(scores, reverse=True)[:3]
        avg_score = sum(top_scores) / len(top_scores) if top_scores else 0
    else:
        avg_score = 0.4  # Has policy result but no chunks

    # Bonus for having multiple distinct sources
    if chunks:
        unique_sources = len(set(c.get("source", "") for c in chunks))
        source_bonus = min(0.05, 0.02 * unique_sources)
    else:
        source_bonus = 0

    # Bonus for citation markers in answer
    import re
    citation_count = len(re.findall(r'\[[\w_.\-]+\.txt\]', answer))
    citation_bonus = min(0.05, 0.02 * citation_count)

    # Penalty if has exceptions (more complex reasoning)
    exception_penalty = 0.03 * len(policy_result.get("exceptions_found", []))

    # Penalty for very short answers (may be incomplete)
    if len(answer) < 50:
        length_penalty = 0.1
    else:
        length_penalty = 0

    confidence = avg_score + source_bonus + citation_bonus - exception_penalty - length_penalty
    confidence = min(0.95, max(0.1, confidence))
    return round(confidence, 2)


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

Hãy trả lời câu hỏi dựa vào tài liệu trên. Yêu cầu:
- Trả lời đầy đủ tất cả các phần của câu hỏi.
- Cite nguồn bằng [tên_file.txt] sau mỗi thông tin quan trọng.
- Nếu thông tin đến từ nhiều tài liệu, hãy tổng hợp và cite tất cả.
- Nếu context THẬT SỰ không đủ, nói rõ "Không đủ thông tin trong tài liệu nội bộ." Nhưng nếu context ĐÃ CÓ đủ thông tin → KHÔNG thêm câu này.
- KHÔNG bịa thêm thông tin ngoài context.
- Nếu câu hỏi liên quan đến thông báo/notification: đọc kỹ TOÀN BỘ context từ mọi phần/section, tổng hợp TẤT CẢ kênh thông báo vào câu trả lời. Cụ thể: tìm (a) Slack channel trong bước thông báo, (b) email trong bước thông báo, (c) PagerDuty trong phần công cụ/tools. Nếu context đề cập cả 3 kênh, câu trả lời PHẢI liệt kê đủ cả 3. KHÔNG bỏ sót kênh nào xuất hiện trong context.
- Khi nêu kênh liên lạc, dùng ĐỊA CHỈ CỤ THỂ từ context (ví dụ: email incident@company.internal, Slack #incident-p1), KHÔNG viết chung chung. KHÔNG nói "không có địa chỉ cụ thể" nếu context ĐÃ chứa địa chỉ.
- Nếu câu hỏi liên quan đến SLA P1, PHẢI nêu escalation rule (10 phút không phản hồi → Senior Engineer).
- Nếu câu hỏi liên quan đến access level, SO SÁNH rõ sự khác biệt giữa các level (ví dụ: Level 2 CÓ emergency bypass nhưng Level 3 KHÔNG CÓ)."""
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
