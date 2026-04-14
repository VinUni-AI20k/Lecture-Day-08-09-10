"""
workers/policy_tool.py — Policy & Tool Worker
Sprint 2+3: Kiểm tra policy dựa vào context, gọi MCP tools khi cần.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: context từ retrieval_worker
    - needs_tool: True nếu supervisor quyết định cần tool call

Output (vào AgentState):
    - policy_result: {"policy_applies", "policy_name", "exceptions_found", "source", "rule"}
    - mcp_tools_used: list of tool calls đã thực hiện
    - worker_io_log: log

Gọi độc lập để test:
    python workers/policy_tool.py
"""

import os
import json
import re
from datetime import datetime

# Load .env for standalone execution
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

WORKER_NAME = "policy_tool_worker"

REFUND_KEYWORDS = [
    "hoàn tiền", "refund", "flash sale", "license", "subscription",
    "kỹ thuật số", "đã kích hoạt", "đã đăng ký", "đã sử dụng",
]
ACCESS_KEYWORDS = [
    "access", "cấp quyền", "level 1", "level 2", "level 3", "level 4",
    "admin access", "contractor", "approval", "security", "quyền truy cập",
]
INCIDENT_KEYWORDS = [
    "ticket", "p1", "jira", "incident", "escalation", "on-call",
    "khẩn cấp", "emergency", "2am", "ngoài giờ",
]
EMERGENCY_KEYWORDS = ["emergency", "khẩn cấp", "2am", "ngoài giờ", "on-call"]


# ─────────────────────────────────────────────
# MCP Client — Sprint 3
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool.

    Sprint 3 Standard: Import trực tiếp từ mcp_server.py (trong-process mock).
    """
    try:
        # Import dynamic để tránh vòng lặp nếu có
        from mcp_server import dispatch_tool
        result = dispatch_tool(tool_name, tool_input)
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": result,
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": None,
            "error": {"code": "MCP_CALL_FAILED", "reason": str(e)},
            "timestamp": datetime.now().isoformat(),
        }


# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────

def _build_base_policy_result(domain: str, policy_name: str, sources: list[str]) -> dict:
    return {
        "policy_applies": True,
        "policy_name": policy_name,
        "exceptions_found": [],
        "source": sources,
        "policy_version_note": "",
        "explanation": "",
        "domain": domain,
        "tool_findings": {},
    }


def _detect_domain(task: str, chunks: list) -> str:
    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks])
    context_lower = context_text.lower()

    has_refund = any(kw in task_lower or kw in context_lower for kw in REFUND_KEYWORDS)
    has_access = any(kw in task_lower or kw in context_lower for kw in ACCESS_KEYWORDS)
    has_incident = any(kw in task_lower or kw in context_lower for kw in INCIDENT_KEYWORDS)

    if has_access and has_incident:
        return "incident_access"
    if has_access:
        return "access"
    if has_refund:
        return "refund"
    return "unknown"


def _maybe_run_refund_llm(task: str, context_text: str, exceptions_found: list[dict], explanation: str) -> tuple[list[dict], str]:
    if not os.getenv("OPENAI_API_KEY"):
        return exceptions_found, explanation

    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt = f"""Bạn là Policy Analyst. Dựa vào context bên dưới, hãy xác định yêu cầu khách hàng có vi phạm chính sách hoàn tiền không.
Task: {task}
Context: {context_text}

Chỉ trả về JSON format:
{{
  "policy_applies": boolean,
  "detected_exceptions": [{{"type": "string", "rule": "string"}}],
  "reason": "string"
}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn phân tích chính sách công ty."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        analysis = json.loads(response.choices[0].message.content)
        llm_exceptions = analysis.get("detected_exceptions", [])
        for ex in llm_exceptions:
            if not any(e["type"] == ex["type"] for e in exceptions_found):
                exceptions_found.append({
                    "type": ex["type"],
                    "rule": ex["rule"],
                    "source": "llm_analysis",
                })
        return exceptions_found, analysis.get("reason", explanation)
    except Exception as e:
        return exceptions_found, f"{explanation} (LLM check skipped: {e})"


def analyze_refund_policy(task: str, chunks: list) -> dict:
    """Phân tích policy hoàn tiền dựa trên context chunks kết hợp rule-based và optional LLM."""
    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks])
    context_lower = context_text.lower()
    sources = list({c.get("source", "unknown") for c in chunks if c})
    policy_result = _build_base_policy_result("refund", "refund_policy_v4", sources)

    exceptions_found = []

    if "flash sale" in task_lower or "flash sale" in context_lower:
        exceptions_found.append({
            "type": "flash_sale_exception",
            "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
            "source": "policy_refund_v4.txt",
        })

    if any(kw in task_lower for kw in ["license key", "license", "subscription", "kỹ thuật số"]):
        exceptions_found.append({
            "type": "digital_product_exception",
            "rule": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })

    if any(kw in task_lower for kw in ["đã kích hoạt", "đã đăng ký", "đã sử dụng"]):
        exceptions_found.append({
            "type": "activated_exception",
            "rule": "Sản phẩm đã kích hoạt hoặc đăng ký tài khoản không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })

    if any(kw in task_lower for kw in ["31/01", "30/01", "trước 01/02", "năm 2025"]):
        policy_result["policy_version_note"] = (
            "Đơn hàng đặt trước 01/02/2026 áp dụng chính sách v3 (không có trong tài liệu hiện tại)."
        )

    explanation = "Analyzed via rule-based checks."
    exceptions_found, explanation = _maybe_run_refund_llm(task, context_text, exceptions_found, explanation)

    if any(src == "mock_data" for src in sources):
        explanation += " Retrieved context included mock_data fallback, so policy conclusion is conservative."

    policy_result["policy_applies"] = len(exceptions_found) == 0
    policy_result["exceptions_found"] = exceptions_found
    policy_result["explanation"] = explanation
    policy_result["tool_findings"] = {
        "has_mock_data": any(src == "mock_data" for src in sources),
    }
    return policy_result


def _parse_access_level(task: str, chunks: list) -> int | None:
    combined = " ".join([task] + [c.get("text", "") for c in chunks]).lower()
    match = re.search(r"level\s*([1-4])", combined)
    if match:
        return int(match.group(1))
    if "admin access" in combined:
        return 3
    return None


def _parse_requester_role(task: str, chunks: list) -> str:
    combined = " ".join([task] + [c.get("text", "") for c in chunks]).lower()
    if "contractor" in combined:
        return "contractor"
    if "on-call" in combined:
        return "on-call"
    if "admin" in combined:
        return "admin"
    return "employee"


def _is_emergency_request(task: str, chunks: list) -> bool:
    combined = " ".join([task] + [c.get("text", "") for c in chunks]).lower()
    return any(kw in combined for kw in EMERGENCY_KEYWORDS)


def _summarize_ticket_info(ticket_output: dict) -> dict:
    if not ticket_output or ticket_output.get("error"):
        return {"available": False, "error": ticket_output.get("error", "unknown error")}
    return {
        "available": True,
        "ticket_id": ticket_output.get("ticket_id"),
        "priority": ticket_output.get("priority"),
        "status": ticket_output.get("status"),
        "assignee": ticket_output.get("assignee"),
        "sla_deadline": ticket_output.get("sla_deadline"),
        "escalated": ticket_output.get("escalated"),
    }


def analyze_access_policy(task: str, chunks: list, access_tool_output: dict | None, domain: str) -> dict:
    """Phân tích policy access/security dựa trên context và MCP tool result."""
    sources = list({c.get("source", "unknown") for c in chunks if c})
    policy_name = "incident_access_composite" if domain == "incident_access" else "access_control_sop"
    policy_result = _build_base_policy_result(domain, policy_name, sources)
    explanation_parts = ["Analyzed via access policy rules and MCP tools."]
    exceptions_found = []

    access_level = _parse_access_level(task, chunks)
    requester_role = _parse_requester_role(task, chunks)
    is_emergency = _is_emergency_request(task, chunks)
    tool_findings = {
        "access_level": access_level,
        "requester_role": requester_role,
        "is_emergency": is_emergency,
    }

    if access_tool_output:
        tool_findings.update({
            "can_grant": access_tool_output.get("can_grant"),
            "required_approvers": access_tool_output.get("required_approvers", []),
            "emergency_override": access_tool_output.get("emergency_override"),
            "notes": access_tool_output.get("notes", []),
            "source": access_tool_output.get("source"),
        })
        if access_tool_output.get("error"):
            explanation_parts.append(f"Access tool returned error: {access_tool_output['error']}")
            policy_result["policy_applies"] = False
        else:
            policy_result["policy_applies"] = bool(access_tool_output.get("can_grant", True))
            if is_emergency and not access_tool_output.get("emergency_override", False):
                exceptions_found.append({
                    "type": "no_emergency_bypass",
                    "rule": "Mức quyền này không có emergency bypass; phải follow quy trình chuẩn.",
                    "source": access_tool_output.get("source", "access_control_sop.txt"),
                })
    else:
        explanation_parts.append("Access level could not be validated via MCP.")
        if access_level is None:
            explanation_parts.append("Could not parse access level from task/context.")

    if any(src == "mock_data" for src in sources):
        explanation_parts.append("Retrieved context included mock_data fallback, so access conclusion is conservative.")

    policy_result["exceptions_found"] = exceptions_found
    policy_result["tool_findings"] = tool_findings
    policy_result["explanation"] = " ".join(explanation_parts)
    return policy_result


def analyze_unknown_policy(task: str, chunks: list) -> dict:
    sources = list({c.get("source", "unknown") for c in chunks if c})
    policy_result = _build_base_policy_result("unknown", "unknown_policy", sources)
    policy_result["explanation"] = "Không xác định được domain policy rõ ràng từ task/context."
    policy_result["tool_findings"] = {"has_mock_data": any(src == "mock_data" for src in sources)}
    return policy_result


# ─────────────────────────────────────────────
# Worker Entry Point
# ─────────────────────────────────────────────

def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với policy_result và mcp_tools_used
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    needs_tool = state.get("needs_tool", False)
    risk_high = state.get("risk_high", False)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("mcp_tools_used", [])

    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "needs_tool": needs_tool,
            "risk_high": risk_high,
        },
        "output": None,
        "error": None,
    }

    try:
        domain = _detect_domain(task, chunks)
        state["history"].append(f"[{WORKER_NAME}] detected domain={domain}")

        # Step 1: Nếu chưa có chunks, gọi MCP search_kb
        if not chunks and needs_tool:
            mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP search_kb")

            if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                chunks = mcp_result["output"]["chunks"]
                state["retrieved_chunks"] = chunks
                state["retrieved_sources"] = mcp_result["output"].get("sources", [])

            if domain == "unknown":
                domain = _detect_domain(task, chunks)
                state["history"].append(f"[{WORKER_NAME}] redetected domain={domain} after search_kb")

        access_tool_output = None
        if domain in {"access", "incident_access"}:
            access_level = _parse_access_level(task, chunks)
            requester_role = _parse_requester_role(task, chunks)
            is_emergency = _is_emergency_request(task, chunks)

            if access_level is not None:
                mcp_result = _call_mcp_tool(
                    "check_access_permission",
                    {
                        "access_level": access_level,
                        "requester_role": requester_role,
                        "is_emergency": is_emergency,
                    },
                )
                state["mcp_tools_used"].append(mcp_result)
                state["history"].append(f"[{WORKER_NAME}] called MCP check_access_permission")
                access_tool_output = mcp_result.get("output")
            else:
                state["history"].append(f"[{WORKER_NAME}] access_level not found; skip check_access_permission")

        # Step 2: Phân tích policy
        if domain == "refund":
            policy_result = analyze_refund_policy(task, chunks)
        elif domain in {"access", "incident_access"}:
            policy_result = analyze_access_policy(task, chunks, access_tool_output, domain)
        else:
            policy_result = analyze_unknown_policy(task, chunks)

        state["policy_result"] = policy_result

        # Step 3: Nếu cần thêm info từ MCP (e.g., ticket id), gọi get_ticket_info
        if domain == "incident_access" and any(kw in task.lower() for kw in ["ticket", "p1", "jira"]):
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP get_ticket_info")
            state["policy_result"].setdefault("tool_findings", {})["ticket"] = _summarize_ticket_info(
                mcp_result.get("output", {})
            )

        worker_io["output"] = {
            "domain": policy_result.get("domain"),
            "policy_name": policy_result.get("policy_name"),
            "policy_applies": policy_result["policy_applies"],
            "exceptions_count": len(policy_result.get("exceptions_found", [])),
            "mcp_calls": len(state["mcp_tools_used"]),
        }
        state["history"].append(
            f"[{WORKER_NAME}] domain={policy_result.get('domain')}, "
            f"policy_applies={policy_result['policy_applies']}, "
            f"exceptions={len(policy_result.get('exceptions_found', []))}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "POLICY_CHECK_FAILED", "reason": str(e)}
        state["policy_result"] = {"error": str(e)}
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Policy Tool Worker — Standalone Test")
    print("=" * 50)

    test_cases = [
        {
            "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
            "retrieved_chunks": [
                {"text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.9}
            ],
        },
        {
            "task": "Khách hàng muốn hoàn tiền license key đã kích hoạt.",
            "retrieved_chunks": [
                {"text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.88}
            ],
        },
        {
            "task": "Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạt.",
            "retrieved_chunks": [
                {"text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất, chưa dùng.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
        },
    ]

    for tc in test_cases:
        print(f"\n▶ Task: {tc['task'][:70]}...")
        result = run(tc.copy())
        pr = result.get("policy_result", {})
        print(f"  policy_applies: {pr.get('policy_applies')}")
        if pr.get("exceptions_found"):
            for ex in pr["exceptions_found"]:
                print(f"  exception: {ex['type']} — {ex['rule'][:60]}...")
        print(f"  MCP calls: {len(result.get('mcp_tools_used', []))}")

    print("\n✅ policy_tool_worker test done.")
