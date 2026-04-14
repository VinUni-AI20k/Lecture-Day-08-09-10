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

Sprint 3 changes:
    - _call_mcp_tool now uses MCPClient (mcp_client.py) instead of direct
      `from mcp_server import dispatch_tool` — proper client-server boundary.
    - MCPRequest/MCPContext envelope added: every call now has request_id + caller.
    - Dynamic ticket ID extraction: no more hardcoded 'P1-LATEST'.
"""

import os
import re
"""

import os
import sys
from typing import Optional

WORKER_NAME = "policy_tool_worker"


# ─────────────────────────────────────────────
# Ensure project root is on sys.path so that
# mcp_client / mcp_protocol imports work when
# running this file directly (python workers/policy_tool.py)
# ─────────────────────────────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)


# ─────────────────────────────────────────────
# MCP Client — Sprint 3: Use MCPClient (not direct import)
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict, run_id: str = "") -> dict:
    """
    Sprint 3: Gọi MCP tool thông qua MCPClient — không import mcp_server trực tiếp.

    Thay vì:
        from mcp_server import dispatch_tool
        result = dispatch_tool(tool_name, tool_input)

    Sprint 3 dùng:
        from mcp_client import get_client
        response = client.dispatch(MCPRequest(...))

    Benefits:
        - Transport độc lập: InProcess (default) hoặc HTTP (MCP_TRANSPORT=http)
        - Formal envelope: request_id, caller, latency_ms được log rõ ràng
        - Never raises: MCPClient luôn trả về MCPResponse, không throw exception
    """
    try:
        from mcp_client import get_client          # Sprint 3 client abstraction
        from mcp_protocol import MCPRequest, MCPContext  # Protocol envelope

        client = get_client()
        request = MCPRequest(
            tool_name=tool_name,
            tool_input=tool_input,
            context=MCPContext(
                run_id=run_id or None,
                caller=WORKER_NAME,
            ),
        )
        response = client.dispatch(request)

        return {
            "tool": tool_name,
            "input": tool_input,
            "output": response.output if response.is_ok() else None,
            "error": {
                "code": response.error.code,
                "reason": response.error.message,
            } if response.error else None,
            "request_id": response.request_id,   # traceable!
            "latency_ms": response.latency_ms,
            "timestamp": request.context.timestamp if request.context else None,
        }

    except ImportError:
        # Fallback: direct dispatch if mcp_client.py not yet available
        from datetime import datetime
        try:
            from mcp_server import dispatch_tool  # type: ignore
            result = dispatch_tool(tool_name, tool_input)
            return {
                "tool": tool_name, "input": tool_input,
                "output": result, "error": None,
                "request_id": None, "latency_ms": None,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "tool": tool_name, "input": tool_input,
                "output": None,
                "error": {"code": "MCP_CALL_FAILED", "reason": str(e)},
                "request_id": None, "latency_ms": None,
                "timestamp": datetime.now().isoformat(),
            }


def _extract_ticket_id(task: str) -> str:
    """
    Sprint 3: Dynamically extract ticket ID from task text.

    Fixes hardcoded 'P1-LATEST' in Sprint 2.
    Matches patterns like: IT-1234, P1-LATEST, P2-5678.

    Falls back to 'P1-LATEST' if no ticket ID found in task.
    """
    match = re.search(r"\b(P\d-\w+|IT-\d{3,6})\b", task, re.IGNORECASE)
    return match.group().upper() if match else "P1-LATEST"
# MCP Client — Sprint 3: Thay bằng real MCP call
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool.

    Sprint 3 TODO: Implement bằng cách import mcp_server hoặc gọi HTTP.

    Hiện tại: Import trực tiếp từ mcp_server.py (trong-process mock).
    """
    from datetime import datetime

    try:
        # TODO Sprint 3: Thay bằng real MCP client nếu dùng HTTP server
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

_REFUND_KEYWORDS = ("hoàn tiền", "refund", "store credit", "flash sale", "license")
_ACCESS_KEYWORDS = ("access level", "cấp quyền", "level 1", "level 2", "level 3",
                    "admin access", "elevated access", "emergency access", "sod")
_SLA_KEYWORDS = ("sla", "p1", "ticket", "escalation", "incident", "on-call", "pagerduty")
_HR_KEYWORDS = ("remote", "probation", "nghỉ phép", "leave", "wfh")
_IT_KEYWORDS = ("mật khẩu", "password", "vpn", "2fa", "đăng nhập sai", "helpdesk")


def _detect_domain(task: str, chunks: list) -> str:
    """
    Phân loại domain của task dựa vào keyword trong task + source của chunks.
    Domain quyết định policy_name trả về.
    """
    t = task.lower()
    sources = {c.get("source", "") for c in chunks if c}

    if any(kw in t for kw in _REFUND_KEYWORDS) or "policy_refund_v4.txt" in sources:
        return "refund"
    if any(kw in t for kw in _ACCESS_KEYWORDS) or "access_control_sop.txt" in sources:
        return "access_control"
    if any(kw in t for kw in _SLA_KEYWORDS) or "sla_p1_2026.txt" in sources:
        return "sla"
    if any(kw in t for kw in _HR_KEYWORDS) or "hr_leave_policy.txt" in sources:
        return "hr"
    if any(kw in t for kw in _IT_KEYWORDS) or "it_helpdesk_faq.txt" in sources:
        return "it_helpdesk"
    return "unknown"


_POLICY_NAME_BY_DOMAIN = {
    "refund": "refund_policy_v4",
    "access_control": "access_control_sop",
    "sla": "sla_p1_2026",
    "hr": "hr_leave_policy",
    "it_helpdesk": "it_helpdesk_faq",
    "unknown": "unknown_policy",
}


def _detect_refund_exceptions(task: str, chunks: list) -> list:
    """Rule-based exception detection cho refund domain."""
    exceptions = []
    t = task.lower()
    ctx = " ".join(c.get("text", "") for c in chunks).lower()

    if "flash sale" in t or "flash sale" in ctx:
        exceptions.append({
            "type": "flash_sale_exception",
            "rule": "Đơn hàng áp dụng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
            "source": "policy_refund_v4.txt",
        })
    if any(kw in t for kw in ["license key", "license", "subscription", "kỹ thuật số", "digital"]):
        exceptions.append({
def analyze_policy(task: str, chunks: list) -> dict:
    """
    Phân tích policy dựa trên context chunks.

    TODO Sprint 2: Implement logic này với LLM call hoặc rule-based check.

    Cần xử lý các exceptions:
    - Flash Sale → không được hoàn tiền
    - Digital product / license key / subscription → không được hoàn tiền
    - Sản phẩm đã kích hoạt → không được hoàn tiền
    - Đơn hàng trước 01/02/2026 → áp dụng policy v3 (không có trong docs)

    Returns:
        dict with: policy_applies, policy_name, exceptions_found, source, rule, explanation
    """
    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks]).lower()

    # --- Rule-based exception detection ---
    exceptions_found = []

    # Exception 1: Flash Sale
    if "flash sale" in task_lower or "flash sale" in context_text:
        exceptions_found.append({
            "type": "flash_sale_exception",
            "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
            "source": "policy_refund_v4.txt",
        })

    # Exception 2: Digital product
    if any(kw in task_lower for kw in ["license key", "license", "subscription", "kỹ thuật số"]):
        exceptions_found.append({
            "type": "digital_product_exception",
            "rule": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })
    if any(kw in t for kw in ["đã kích hoạt", "đã đăng ký", "đã sử dụng", "kích hoạt tài khoản"]):
        exceptions.append({
            "type": "activated_exception",
            "rule": "Sản phẩm đã kích hoạt / đăng ký tài khoản không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })
    return exceptions


def _detect_access_exceptions(task: str, chunks: list) -> list:
    """Rule-based exception detection cho access_control domain."""
    exceptions = []
    t = task.lower()

    is_emergency = any(kw in t for kw in ["emergency", "khẩn cấp", "p1", "2am", "sự cố"])
    mentions_l3 = "level 3" in t or "admin access" in t
    mentions_l2 = "level 2" in t or "elevated" in t

    if is_emergency and mentions_l3:
        exceptions.append({
            "type": "no_emergency_bypass_level3",
            "rule": (
                "Level 3 (Admin Access) KHÔNG có emergency bypass: vẫn cần đủ 3 approvers "
                "(Line Manager + IT Admin + IT Security) kể cả trong sự cố P1."
            ),
            "source": "access_control_sop.txt",
        })
    if is_emergency and mentions_l2:
        exceptions.append({
            "type": "emergency_bypass_level2",
            "rule": (
                "Level 2 có emergency bypass: cấp tạm thời với approval đồng thời "
                "của Line Manager và IT Admin on-call (không cần IT Security)."
            ),
            "source": "access_control_sop.txt",
        })
    return exceptions


def _check_temporal_scoping(task: str) -> str:
    """Phát hiện các trường hợp temporal scoping cho refund policy (v3 vs v4)."""
    t = task.lower()
    pre_v4_markers = ["31/01", "30/01", "29/01", "trước 01/02", "trước 1/02", "trước ngày 01/02"]
    if any(m in t for m in pre_v4_markers):
        return (
            "Đơn hàng đặt trước 01/02/2026 áp dụng chính sách hoàn tiền v3 "
            "(không có trong tài liệu hiện tại). Cần xác nhận với CS Team."
        )
    return ""


def analyze_policy(task: str, chunks: list) -> dict:
    """
    Phân tích policy dựa trên task + retrieved chunks.

    Flow:
      1. Detect domain (refund / access_control / sla / hr / it / unknown)
      2. Chọn policy_name theo domain (không mặc định là refund nữa)
      3. Detect exceptions per-domain (rule-based, grounded vào chunks)
      4. Temporal scoping check cho refund

    Returns:
        dict khớp contract: policy_applies, policy_name, exceptions_found,
        source, policy_version_note, explanation, domain
    """
    domain = _detect_domain(task, chunks)
    policy_name = _POLICY_NAME_BY_DOMAIN.get(domain, "unknown_policy")

    exceptions_found = []
    if domain == "refund":
        exceptions_found = _detect_refund_exceptions(task, chunks)
    elif domain == "access_control":
        exceptions_found = _detect_access_exceptions(task, chunks)

    policy_version_note = _check_temporal_scoping(task) if domain == "refund" else ""

    has_blocking_exception = any(
        ex["type"] in {
            "flash_sale_exception",
            "digital_product_exception",
            "activated_exception",
            "no_emergency_bypass_level3",
        }
        for ex in exceptions_found
    )
    policy_applies = not has_blocking_exception

    # Exception 3: Activated product
    if any(kw in task_lower for kw in ["đã kích hoạt", "đã đăng ký", "đã sử dụng"]):
        exceptions_found.append({
            "type": "activated_exception",
            "rule": "Sản phẩm đã kích hoạt hoặc đăng ký tài khoản không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })

    # Determine policy_applies
    policy_applies = len(exceptions_found) == 0

    # Determine which policy version applies (temporal scoping)
    # TODO: Check nếu đơn hàng trước 01/02/2026 → v3 applies (không có docs, nên flag cho synthesis)
    policy_name = "refund_policy_v4"
    policy_version_note = ""
    if "31/01" in task_lower or "30/01" in task_lower or "trước 01/02" in task_lower:
        policy_version_note = "Đơn hàng đặt trước 01/02/2026 áp dụng chính sách v3 (không có trong tài liệu hiện tại)."

    # TODO Sprint 2: Gọi LLM để phân tích phức tạp hơn
    # Ví dụ:
    # from openai import OpenAI
    # client = OpenAI()
    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[
    #         {"role": "system", "content": "Bạn là policy analyst. Dựa vào context, xác định policy áp dụng và các exceptions."},
    #         {"role": "user", "content": f"Task: {task}\n\nContext:\n" + "\n".join([c['text'] for c in chunks])}
    #     ]
    # )
    # analysis = response.choices[0].message.content

    sources = list({c.get("source", "unknown") for c in chunks if c})

    return {
        "policy_applies": policy_applies,
        "policy_name": policy_name,
        "domain": domain,
        "exceptions_found": exceptions_found,
        "source": sources,
        "policy_version_note": policy_version_note,
        "explanation": (
            f"Rule-based policy check trên domain='{domain}'. "
            f"Found {len(exceptions_found)} exception(s)."
        ),
        "exceptions_found": exceptions_found,
        "source": sources,
        "policy_version_note": policy_version_note,
        "explanation": "Analyzed via rule-based policy check. TODO: upgrade to LLM-based analysis.",
    }


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
        },
        "output": None,
        "error": None,
    }

    try:
        # Step 1: Nếu chưa có chunks, gọi MCP search_kb
        if not chunks and needs_tool:
            mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP search_kb")

            if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                chunks = mcp_result["output"]["chunks"]
                state["retrieved_chunks"] = chunks

        # Step 2: Phân tích policy
        policy_result = analyze_policy(task, chunks)
        state["policy_result"] = policy_result

        # Step 3: Nếu cần thêm info từ MCP (e.g., ticket status), gọi get_ticket_info
        if needs_tool and any(kw in task.lower() for kw in ["ticket", "p1", "jira"]):
            # Sprint 3: Extract ticket ID dynamically from task (not hardcoded)
            ticket_id = _extract_ticket_id(task)
            mcp_result = _call_mcp_tool(
                "get_ticket_info",
                {"ticket_id": ticket_id},
                run_id=state.get("run_id", ""),
            )
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(
                f"[{WORKER_NAME}] called MCP get_ticket_info (ticket_id={ticket_id})"
            )
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP get_ticket_info")

        worker_io["output"] = {
            "policy_applies": policy_result["policy_applies"],
            "exceptions_count": len(policy_result.get("exceptions_found", [])),
            "mcp_calls": len(state["mcp_tools_used"]),
        }
        state["history"].append(
            f"[{WORKER_NAME}] policy_applies={policy_result['policy_applies']}, "
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
