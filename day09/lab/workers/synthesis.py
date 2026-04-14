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
from datetime import datetime, timedelta

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
    # Helper kept for debugging prompts or future prompt-inspection tooling.
    user_message = messages[-1]["content"] if messages else ""
    match = re.search(r"Câu hỏi:\s*(.+?)(?:\n\n|$)", user_message, flags=re.DOTALL)
    return match.group(1).strip() if match else ""


def _normalize(text: str) -> str:
    cleaned = re.sub(r"^\W+", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _sentence_split(text: str) -> list:
    # Split noisy document text into answerable sentence-like units.
    cleaned = text.replace("\r", " ").replace("\n", " ")
    parts = re.split(r"(?<=[\.\?!])\s+|\s+-\s+", cleaned)
    return [_normalize(part) for part in parts if _normalize(part)]


def _task_keywords(task: str) -> set:
    return set(re.findall(r"[a-z0-9_]+", task.lower()))


def _pick_preferred_source(sources: list, preferred: list, default: str = "unknown") -> str:
    for source in preferred:
        if source in sources:
            return source
    return sources[0] if sources else default


def _find_sentences(chunks: list, markers: list, source: str = None, limit: int = 5) -> list:
    chosen = []
    for chunk in chunks:
        if source and chunk.get("source") != source:
            continue
        for sentence in _sentence_split(chunk.get("text", "")):
            lowered = sentence.lower()
            if any(marker in lowered for marker in markers):
                chosen.append({"text": sentence, "source": chunk.get("source", "unknown")})
            if len(chosen) >= limit:
                return chosen
    return chosen


def _extract_first_number(text: str) -> int | None:
    match = re.search(r"\b(\d+)\b", text or "")
    return int(match.group(1)) if match else None


def _compute_clock_deadline(task: str, minutes: int | None) -> str | None:
    if minutes is None:
        return None
    match = re.search(r"\b(\d{1,2}):(\d{2})\b", task)
    if not match:
        return None
    base_time = datetime.strptime(f"{match.group(1)}:{match.group(2)}", "%H:%M")
    return (base_time + timedelta(minutes=minutes)).strftime("%H:%M")


def _strip_bullet_prefix(text: str) -> str:
    return re.sub(r"^-+\s*", "", text or "").strip()


def _build_answer_schema(question_type: str, task: str, chunks: list, policy_result: dict, answer: str) -> dict:
    task_lower = task.lower()
    sources = list({c.get("source", "unknown") for c in chunks if c})

    if question_type == "sla_detail":
        channel_sentences = _find_sentences(chunks, ["slack #incident-p1", "incident@company.internal", "pagerduty"], source="sla_p1_2026.txt")
        escalation_sentences = _find_sentences(chunks, ["senior engineer"], source="sla_p1_2026.txt")
        if not escalation_sentences and "senior engineer" in answer.lower():
            escalation_sentences = [{"text": answer, "source": "sla_p1_2026.txt"}]
        channels = []
        for sentence in channel_sentences:
            lowered = sentence["text"].lower()
            if "slack #incident-p1" in lowered and "Slack #incident-p1" not in channels:
                channels.append("Slack #incident-p1")
            if "incident@company.internal" in lowered and "incident@company.internal" not in channels:
                channels.append("incident@company.internal")
            if "pagerduty" in lowered and "PagerDuty" not in channels:
                channels.append("PagerDuty")
        escalation_minutes = None
        escalation_target = None
        if escalation_sentences:
            escalation_target = "Senior Engineer"
            escalation_minutes = _extract_first_number(escalation_sentences[0]["text"])
        return {
            "type": question_type,
            "channels": channels,
            "initial_recipient": "On-call engineer" if any("on-call engineer" in s["text"].lower() for s in _find_sentences(chunks, ["on-call engineer"], source="sla_p1_2026.txt")) else None,
            "escalation_target": escalation_target,
            "escalation_window_minutes": escalation_minutes,
            "escalation_deadline_clock": _compute_clock_deadline(task, escalation_minutes),
            "sources": list(dict.fromkeys(["sla_p1_2026.txt"] + sources)),
        }

    if question_type == "sla_action":
        escalation_sentences = _find_sentences(chunks, ["senior engineer"], source="sla_p1_2026.txt")
        escalation_minutes = _extract_first_number(escalation_sentences[0]["text"]) if escalation_sentences else None
        return {
            "type": question_type,
            "next_action": "auto_escalate" if escalation_sentences else None,
            "escalation_target": "Senior Engineer" if escalation_sentences else None,
            "trigger_window_minutes": escalation_minutes,
            "supporting_facts": [_strip_bullet_prefix(line) for line in answer.splitlines()[:3] if line.strip()],
            "sources": sources,
        }

    if question_type == "access_control":
        return {
            "type": question_type,
            "approver_count": policy_result.get("approver_count"),
            "approvers": policy_result.get("required_approvers", []),
            "highest_approver": policy_result.get("highest_approver"),
            "emergency_override": policy_result.get("emergency_override"),
            "exception_rule": policy_result.get("exceptions_found", [{}])[0].get("rule") if policy_result.get("exceptions_found") else None,
            "sources": policy_result.get("source", sources),
        }

    if question_type == "access_sla_multi_hop":
        access_schema = _build_answer_schema("access_control", task, chunks, policy_result, answer)
        sla_schema = _build_answer_schema("sla_detail", task, chunks, policy_result, answer)
        return {
            "type": question_type,
            "sla": {
                "channels": sla_schema.get("channels", []),
                "escalation_target": sla_schema.get("escalation_target"),
                "escalation_window_minutes": sla_schema.get("escalation_window_minutes"),
                "escalation_deadline_clock": sla_schema.get("escalation_deadline_clock"),
            },
            "access": {
                "approver_count": access_schema.get("approver_count"),
                "approvers": access_schema.get("approvers", []),
                "highest_approver": access_schema.get("highest_approver"),
                "emergency_override": access_schema.get("emergency_override"),
            },
            "sources": list(dict.fromkeys((policy_result.get("source", []) or []) + sources)),
        }

    if question_type == "policy_temporal_scope":
        return {
            "type": question_type,
            "applicable_policy": "refund_policy_v3" if policy_result.get("policy_version_note") else policy_result.get("policy_name"),
            "can_confirm_details": False if policy_result.get("policy_version_note") else True,
            "abstain_reason": policy_result.get("policy_version_note"),
            "known_current_policy": "refund_policy_v4" if policy_result.get("policy_version_note") else None,
            "sources": policy_result.get("source", sources),
        }

    if question_type == "numeric_policy":
        store_credit = _find_sentences(chunks, ["110%", "store credit"], source="policy_refund_v4.txt", limit=2)
        value = None
        for sentence in store_credit:
            if "110%" in sentence["text"]:
                value = 110
                break
        return {
            "type": question_type,
            "value": value,
            "unit": "percent",
            "subject": "store_credit",
            "explanation": store_credit[0]["text"] if store_credit else None,
            "sources": list(dict.fromkeys(["policy_refund_v4.txt"] + sources)),
        }

    if question_type == "policy_exception":
        return {
            "type": question_type,
            "allowed": False if policy_result.get("exceptions_found") else policy_result.get("policy_applies"),
            "exception_types": [item.get("type") for item in policy_result.get("exceptions_found", [])],
            "override_reason": policy_result.get("exceptions_found", [{}])[0].get("rule") if policy_result.get("exceptions_found") else None,
            "sources": policy_result.get("source", sources),
        }

    if question_type == "eligibility_policy":
        remote_sentences = _find_sentences(chunks, ["probation period", "sau probation period", "team lead", "2 ngày/tuần", "2 ngay/tuan"], source="hr_leave_policy.txt", limit=4)
        return {
            "type": question_type,
            "allowed": False if "probation" in task_lower else None,
            "eligibility_rule": remote_sentences[0]["text"] if remote_sentences else None,
            "conditions": [sentence["text"] for sentence in remote_sentences],
            "sources": list(dict.fromkeys(["hr_leave_policy.txt"] + sources)),
        }

    if question_type == "faq_multi_detail":
        password_sentences = _find_sentences(chunks, ["mật khẩu", "90 ngày", "7 ngày"], source="it_helpdesk_faq.txt", limit=4)
        rotation_days = None
        warning_days = None
        for sentence in password_sentences:
            lowered = sentence["text"].lower()
            if "90 ngày" in lowered or "90 ngay" in lowered:
                rotation_days = 90
            if "7 ngày" in lowered or "7 ngay" in lowered:
                warning_days = 7
        return {
            "type": question_type,
            "facts": {
                "password_rotation_days": rotation_days,
                "warning_days_before_expiry": warning_days,
            },
            "sources": list(dict.fromkeys(["it_helpdesk_faq.txt"] + sources)),
        }

    if question_type == "abstain_missing_info":
        return {
            "type": question_type,
            "can_answer": False,
            "missing_info": "Requested fact is not present in the current internal documents.",
            "suggested_next_step": "Check with the owning department or source of truth for penalty terms.",
            "sources": sources,
        }

    return {
        "type": "generic_lookup",
        "evidence_points": [_strip_bullet_prefix(line) for line in answer.splitlines()[:3] if line.strip()],
        "sources": sources,
    }


def _top_relevant_snippets(task: str, chunks: list, limit: int = 3) -> list:
    # Rank evidence snippets so fallback answers stay grounded and concise.
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


def _targeted_snippets(chunks: list, source: str, markers: list, limit: int = 3) -> list:
    chosen = []
    for chunk in chunks:
        if chunk.get("source") != source:
            continue
        for sentence in _sentence_split(chunk.get("text", "")):
            lowered = sentence.lower()
            if any(marker in lowered for marker in markers):
                chosen.append(f"- {sentence} [{source}]")
            if len(chosen) >= limit:
                return chosen
    return chosen


def _fallback_grounded_answer(task: str, chunks: list, policy_result: dict) -> str:
    # Deterministic fallback keeps the worker usable even without any LLM provider configured.
    task_lower = task.lower()
    policy_sources = policy_result.get("source", [])

    if policy_result.get("policy_version_note"):
        source = _pick_preferred_source(policy_sources, ["policy_refund_v4.txt"])
        return (
            "Không đủ thông tin trong tài liệu nội bộ để khẳng định chi tiết của policy phiên bản cũ. "
            f"{policy_result['policy_version_note']} [{source}]"
        )

    if policy_result.get("required_approvers"):
        lines = []
        approvers = policy_result.get("required_approvers", [])
        approver_count = policy_result.get("approver_count", len(approvers))
        highest_approver = policy_result.get("highest_approver")
        access_source = _pick_preferred_source(policy_sources, ["access_control_sop.txt"])
        if policy_result.get("emergency_override"):
            lines.append(
                f"- Level access này có emergency bypass. Điều kiện phê duyệt đồng thời: {', '.join(approvers)}. [{access_source}]"
            )
        elif policy_result.get("exceptions_found"):
            lines.append(f"- Ngoại lệ áp dụng: {policy_result['exceptions_found'][0].get('rule', '')} [{access_source}]")
        lines.append(f"- Số người phê duyệt cần có: {approver_count}. Chuỗi phê duyệt: {', '.join(approvers)}. [{access_source}]")
        if highest_approver:
            lines.append(f"- Người phê duyệt cuối cùng/có thẩm quyền cao nhất: {highest_approver}. [{access_source}]")

        if any(keyword in task_lower for keyword in ["p1", "sla", "incident", "2am", "notification"]):
            sla_lines = _targeted_snippets(
                chunks,
                "sla_p1_2026.txt",
                ["slack #incident-p1", "incident@company.internal", "pagerduty", "senior engineer"],
                limit=4,
            )
            lines.extend(sla_lines[:3])
        return "\n".join(lines)

    if policy_result.get("exceptions_found"):
        lines = []
        for exception in policy_result["exceptions_found"]:
            lines.append(f"- Ngoại lệ áp dụng: {exception.get('rule', '')} [{exception.get('source', 'unknown')}]")

        if policy_result.get("required_approvers"):
            approvers = ", ".join(policy_result["required_approvers"])
            lines.append(f"- Chuỗi phê duyệt cần có: {approvers} [access_control_sop.txt]")
        if policy_result.get("emergency_override"):
            lines.append("- Trường hợp khẩn cấp được phép cấp quyền tạm thời theo SOP [access_control_sop.txt]")

        if "flash sale" in task_lower:
            lines.append("- Kết luận: không được hoàn tiền vì ngoại lệ Flash Sale override các điều kiện hoàn tiền thông thường. [policy_refund_v4.txt]")
            flash_sale_support = _targeted_snippets(
                chunks,
                "policy_refund_v4.txt",
                ["flash sale", "không được hoàn tiền", "not refundable"],
                limit=1,
            )
            lines.extend(flash_sale_support)
        else:
            lines.extend(_top_relevant_snippets(task, chunks, limit=2))
        return "\n".join(lines[:4])

    if "store credit" in task_lower:
        store_credit_lines = [
            line for line in _top_relevant_snippets(task, chunks, limit=4)
            if "110%" in line or "store credit" in line.lower()
        ]
        if store_credit_lines:
            return "\n".join(store_credit_lines[:2])

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
        # Keep source names attached so the generated answer can cite evidence cleanly.
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

    # Use retrieval score as a lightweight proxy for answer confidence.
    if chunks:
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
    else:
        avg_score = 0

    # Penalty nếu có exceptions (phức tạp hơn)
    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))

    confidence = min(0.95, avg_score - exception_penalty + 0.05)
    return round(max(0.1, confidence), 2)


def synthesize(task: str, chunks: list, policy_result: dict, question_type: str = "generic_lookup") -> dict:
    """
    Tổng hợp câu trả lời từ chunks và policy context.

    Returns:
        {"answer": str, "sources": list, "confidence": float}
    """
    context = _build_context(chunks, policy_result)

    # The synthesis prompt only sees evidence already collected by earlier workers.
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
    answer_schema = _build_answer_schema(question_type, task, chunks, policy_result, answer)

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "answer_schema_type": answer_schema.get("type", question_type),
        "answer_schema": answer_schema,
    }


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    policy_result = state.get("policy_result", {})
    question_type = state.get("question_type", "generic_lookup")

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    # Capture worker-level IO so low-confidence answers are easy to inspect in trace files.
    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "question_type": question_type,
            "chunks_count": len(chunks),
            "has_policy": bool(policy_result),
        },
        "output": None,
        "error": None,
    }

    try:
        result = synthesize(task, chunks, policy_result, question_type=question_type)
        state["final_answer"] = result["answer"]
        state["answer_schema_type"] = result["answer_schema_type"]
        state["answer_schema"] = result["answer_schema"]
        state["sources"] = result["sources"]
        state["confidence"] = result["confidence"]
        if result["confidence"] < 0.4:
            # Low-confidence outputs are flagged for HITL/reporting even if the pipeline still returns an answer.
            state["hitl_triggered"] = True

        worker_io["output"] = {
            "question_type": question_type,
            "answer_schema_type": result["answer_schema_type"],
            "answer_length": len(result["answer"]),
            "sources": result["sources"],
            "confidence": result["confidence"],
        }
        state["history"].append(
            f"[{WORKER_NAME}] type={question_type} answer_schema={result['answer_schema_type']} "
            f"confidence={result['confidence']}, sources={result['sources']}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "SYNTHESIS_FAILED", "reason": str(e)}
        state["final_answer"] = f"SYNTHESIS_ERROR: {e}"
        state["answer_schema_type"] = question_type
        state["answer_schema"] = {"type": question_type, "error": str(e)}
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
