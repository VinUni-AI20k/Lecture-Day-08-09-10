"""
Nguyễn Đức Hải - 2A202600149
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
import json

# Load .env for standalone execution
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


WORKER_NAME = "synthesis_worker"

SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk nội bộ.

Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context được cung cấp. KHÔNG dùng kiến thức ngoài.
2. Nếu context không đủ để trả lời → nói rõ "Không đủ thông tin trong tài liệu nội bộ".
3. Trích dẫn nguồn cuối mỗi câu quan trọng: [tên_file].
4. Trả lời súc tích, có cấu trúc. Không dài dòng.
5. Nếu có exceptions/ngoại lệ → nêu rõ ràng trước khi kết luận.
"""


def _try_call_llm(messages: list) -> str | None:
    """
    Gọi LLM để tổng hợp câu trả lời.
    TODO Sprint 2: Implement với OpenAI hoặc Gemini.
    """
    # Option A: OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1,  # Low temperature để grounded
                max_tokens=800,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[synthesis_worker] OpenAI Error: {e}")

    # Option B: Gemini
    gemini_key = os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            combined = "\\n".join([f"{m['role']}: {m['content']}" for m in messages])
            response = model.generate_content(combined)
            return response.text
        except Exception as e:
            print(f"[synthesis_worker] Gemini Error: {e}")

    return None


def _normalize_sources(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str):
        return [value]
    return []


def _collect_sources(chunks: list, policy_result: dict) -> list[str]:
    ordered = []

    def add(source):
        if source and source not in ordered:
            ordered.append(source)

    for chunk in chunks:
        add(chunk.get("source"))

    for source in _normalize_sources(policy_result.get("source")):
        add(source)

    for ex in policy_result.get("exceptions_found", []):
        add(ex.get("source"))

    tool_findings = policy_result.get("tool_findings", {}) or {}
    add(tool_findings.get("source"))
    ticket_info = tool_findings.get("ticket", {}) or {}
    add(ticket_info.get("source"))

    return ordered


def _format_citation(sources: list[str], fallback: str = "internal_docs") -> str:
    if not sources:
        return f"[{fallback}]"
    return " ".join(f"[{src}]" for src in sources[:2])


def _format_tool_findings(domain: str, tool_findings: dict) -> list[str]:
    lines = []
    if not tool_findings:
        return lines

    if domain in {"access", "incident_access"}:
        access_level = tool_findings.get("access_level")
        requester_role = tool_findings.get("requester_role")
        required_approvers = tool_findings.get("required_approvers", [])
        emergency_override = tool_findings.get("emergency_override")
        notes = tool_findings.get("notes", [])

        if access_level is not None:
            lines.append(f"- Access level: {access_level}")
        if requester_role:
            lines.append(f"- Requester role: {requester_role}")
        if required_approvers:
            lines.append(f"- Required approvers: {', '.join(required_approvers)}")
        if emergency_override is not None:
            lines.append(f"- Emergency override: {emergency_override}")
        if notes:
            lines.append(f"- Notes: {' | '.join(notes)}")

    if domain == "incident_access":
        ticket = tool_findings.get("ticket", {}) or {}
        if ticket:
            lines.append("- Ticket summary:")
            for key in ["ticket_id", "priority", "status", "assignee", "sla_deadline", "escalated"]:
                if ticket.get(key) is not None:
                    lines.append(f"  - {key}: {ticket[key]}")

    if tool_findings.get("has_mock_data"):
        lines.append("- Context included mock_data fallback")

    return lines


def _build_context(chunks: list, policy_result: dict) -> str:
    """Xây dựng context string từ chunks và policy result."""
    parts = []
    domain = policy_result.get("domain", "unknown")

    if chunks:
        parts.append("=== TÀI LIỆU THAM KHẢO ===")
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "unknown")
            text = chunk.get("text", "")
            score = chunk.get("score", 0)
            parts.append(f"[{i}] Nguồn: {source} (relevance: {score:.2f})\n{text}")

    if policy_result:
        parts.append("\n=== POLICY / TOOL ANALYSIS ===")
        parts.append(f"- Domain: {domain}")
        if policy_result.get("policy_name"):
            parts.append(f"- Policy name: {policy_result['policy_name']}")
        if policy_result.get("policy_applies") is not None:
            parts.append(f"- Policy applies: {policy_result.get('policy_applies')}")
        if policy_result.get("explanation"):
            parts.append(f"- Explanation: {policy_result['explanation']}")

    if policy_result and policy_result.get("exceptions_found"):
        parts.append("\n=== POLICY EXCEPTIONS ===")
        for ex in policy_result["exceptions_found"]:
            ex_source = ex.get("source", "unknown")
            parts.append(f"- {ex.get('rule', '')} [{ex_source}]")
            
    if policy_result and policy_result.get("policy_version_note"):
        parts.append(f"\n=== LƯU Ý CHÍNH SÁCH ===\n- {policy_result['policy_version_note']}")

    if policy_result and policy_result.get("tool_findings"):
        parts.append("\n=== TOOL FINDINGS ===")
        parts.extend(_format_tool_findings(domain, policy_result.get("tool_findings", {})))

    if policy_result and policy_result.get("error"):
        parts.append("\n=== POLICY ERROR ===")
        parts.append(f"- {policy_result['error']}")

    if domain == "unknown":
        parts.append("\n=== DOMAIN STATUS ===")
        parts.append("- Policy domain chưa xác định rõ; nếu context không đủ, hãy abstain.")

    if not parts:
        return "(Không có context)"

    return "\n\n".join(parts)


def _build_template_answer(task: str, chunks: list, policy_result: dict, sources: list[str]) -> str:
    domain = policy_result.get("domain", "unknown")
    exceptions = policy_result.get("exceptions_found", []) or []
    tool_findings = policy_result.get("tool_findings", {}) or {}
    citation = _format_citation(sources)

    if policy_result.get("error"):
        return f"Không đủ thông tin trong tài liệu nội bộ. {citation}"

    if domain == "refund":
        if exceptions:
            rules = "; ".join(ex.get("rule", "") for ex in exceptions if ex.get("rule"))
            return f"Theo chính sách hoàn tiền, yêu cầu này không được áp dụng vì: {rules}. {citation}"
        if policy_result.get("policy_version_note"):
            return (
                f"Theo chính sách hoàn tiền hiện có, không thấy ngoại lệ chặn yêu cầu này. "
                f"Lưu ý: {policy_result['policy_version_note']}. {citation}"
            )
        return f"Theo chính sách hoàn tiền hiện có, không thấy ngoại lệ chặn yêu cầu này. {citation}"

    if domain in {"access", "incident_access"}:
        lines = []
        access_level = tool_findings.get("access_level")
        if access_level is not None:
            lines.append(f"Yêu cầu đang ở mức quyền Level {access_level}.")

        approvers = tool_findings.get("required_approvers", [])
        if approvers:
            lines.append(f"Cần phê duyệt bởi: {', '.join(approvers)}.")

        if "can_grant" in tool_findings:
            if tool_findings.get("can_grant"):
                lines.append("Theo rule hiện tại, quyền này có thể được cấp nếu đáp ứng đúng quy trình.")
            else:
                lines.append("Theo rule hiện tại, yêu cầu này không thể được cấp theo điều kiện hiện có.")

        if tool_findings.get("is_emergency") is True:
            if tool_findings.get("emergency_override"):
                lines.append("Có emergency override cho trường hợp khẩn cấp.")
            else:
                lines.append("Không có emergency override cho trường hợp này.")

        notes = tool_findings.get("notes", [])
        if notes:
            lines.append("Ghi chú: " + " ".join(notes))

        if domain == "incident_access":
            ticket = tool_findings.get("ticket", {}) or {}
            if ticket.get("available"):
                ticket_parts = []
                if ticket.get("ticket_id"):
                    ticket_parts.append(f"ticket {ticket['ticket_id']}")
                if ticket.get("priority"):
                    ticket_parts.append(f"priority {ticket['priority']}")
                if ticket.get("status"):
                    ticket_parts.append(f"status {ticket['status']}")
                if ticket_parts:
                    lines.append("Thông tin ticket liên quan: " + ", ".join(ticket_parts) + ".")

        if lines:
            return " ".join(lines) + f" {citation}"

    if chunks:
        snippet_lines = []
        for chunk in chunks[:2]:
            text = (chunk.get("text", "") or "").strip().replace("\n", " ")
            if text:
                snippet_lines.append(text[:180])
        if snippet_lines:
            return f"Theo tài liệu hiện có: {' '.join(snippet_lines)} {citation}"

    return "Không đủ thông tin trong tài liệu nội bộ."


def _estimate_confidence(chunks: list, answer: str, policy_result: dict, generation_mode: str) -> float:
    """
    Ước tính confidence dựa vào:
    - Số lượng và quality của chunks
    - Có exceptions không
    - Answer có abstain không

    TODO Sprint 2: Có thể dùng LLM-as-Judge để tính confidence chính xác hơn.
    """
    tool_findings = policy_result.get("tool_findings", {}) or {}
    domain = policy_result.get("domain", "unknown")
    has_structured_tool_evidence = bool(
        tool_findings.get("required_approvers")
        or tool_findings.get("can_grant") is not None
        or tool_findings.get("ticket")
    )

    if "không đủ thông tin" in answer.lower() or "không có trong tài liệu" in answer.lower() or "abstain" in answer.lower():
        return 0.3  # Abstain → moderate-low

    # LLM-as-Judge Implementation
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and generation_mode == "llm" and chunks:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            context_text = " ".join([c.get("text", "") for c in chunks])
            
            prompt = f"""Đánh giá mức độ tự tin (confidence score) từ 0.0 đến 1.0 cho câu trả lời sau dựa trên tài liệu.
            Tài liệu: {context_text}
            Câu trả lời: {answer}
            
            Chỉ trả về JSON định dạng:
            {{"confidence": 0.85}}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            result = json.loads(response.choices[0].message.content)
            llm_conf = float(result.get("confidence", 0.0))
            if llm_conf > 0.0:
                exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))
                return round(max(0.1, min(0.95, llm_conf - exception_penalty)), 2)
        except Exception:
            pass

    avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks) if chunks else 0.0
    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))
    mock_penalty = 0.2 if tool_findings.get("has_mock_data") else 0.0
    domain_penalty = 0.15 if domain == "unknown" else 0.0
    fallback_penalty = 0.05 if generation_mode == "template_fallback" else 0.0

    base = avg_score
    if has_structured_tool_evidence:
        base = max(base, 0.72 if domain in {"access", "incident_access"} else 0.55)
    elif not chunks:
        base = 0.1

    confidence = min(0.95, base - exception_penalty - mock_penalty - domain_penalty - fallback_penalty)
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

    sources = _collect_sources(chunks, policy_result)
    answer = _try_call_llm(messages)
    generation_mode = "llm"
    if not answer:
        answer = _build_template_answer(task, chunks, policy_result, sources)
        generation_mode = "template_fallback"

    confidence = _estimate_confidence(chunks, answer, policy_result, generation_mode)

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "generation_mode": generation_mode,
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
            "generation_mode": result["generation_mode"],
        }
        state["history"].append(
            f"[{WORKER_NAME}] answer generated via {result['generation_mode']}, "
            f"confidence={result['confidence']}, sources={result['sources']}"
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
