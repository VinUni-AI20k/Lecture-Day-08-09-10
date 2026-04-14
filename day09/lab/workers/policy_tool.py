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

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional

WORKER_NAME = "policy_tool_worker"


# ————————————————————————————————————————————————
# MCP Client — Sprint 3: Thay bằng real MCP call
# ————————————————————————————————————————————————

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Call the real MCP server over stdio and normalize the tool result for tracing.
    """
    async def _call() -> dict:
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server_path = os.path.join(base_dir, "mcp_server.py")
        # Spin up the local MCP server as a subprocess so this worker stays decoupled from server internals.
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[server_path, "--stdio-server"],
            cwd=base_dir,
            env=dict(os.environ),
            encoding="utf-8",
            encoding_error_handler="replace",
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, tool_input)

        output = result.structuredContent
        if isinstance(output, dict) and isinstance(output.get("result"), str):
            try:
                output = json.loads(output["result"])
            except Exception:
                output = {"text": output["result"]}

        if output is None:
            text_parts = []
            for item in result.content:
                text_value = getattr(item, "text", None)
                if text_value is not None:
                    text_parts.append(text_value)
            if text_parts:
                try:
                    output = json.loads("\n".join(text_parts))
                except Exception:
                    output = {"text": "\n".join(text_parts)}

        return {
            "tool": tool_name,
            "input": tool_input,
            "output": output,
            "error": None if not result.isError else {"code": "MCP_TOOL_ERROR", "reason": str(output)},
            "transport": "stdio_mcp",
            "timestamp": datetime.now().isoformat(),
        }

    try:
        # asyncio.run keeps the public worker API synchronous for the graph.
        return asyncio.run(_call())
    except Exception as e:
        try:
            from mcp_server import dispatch_tool

            output = dispatch_tool(tool_name, tool_input)
            return {
                "tool": tool_name,
                "input": tool_input,
                "output": output,
                "error": output.get("error") if isinstance(output, dict) and output.get("error") else None,
                "transport": "local_dispatch_fallback",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as fallback_error:
            return {
                "tool": tool_name,
                "input": tool_input,
                "output": None,
                "error": {
                    "code": "MCP_CALL_FAILED",
                    "reason": f"stdio_error={e}; fallback_error={fallback_error}",
                },
                "transport": "failed",
                "timestamp": datetime.now().isoformat(),
            }


# ————————————————————————————————————————————————
# Policy Analysis Logic
# ————————————————————————————————————————————————

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
    import re

    task_lower = task.lower()

    def has_phrase(phrase: str) -> bool:
        return phrase in task_lower

    def has_negated_phrase(phrase: str) -> bool:
        return any(
            marker in task_lower
            for marker in [
                f"không phải {phrase}",
                f"khong phai {phrase}",
                f"không phải là {phrase}",
                f"khong phai la {phrase}",
                f"not {phrase}",
            ]
        )

    # Start with cheap, explainable rules before reaching for an LLM classifier.
    exceptions_found = []

    # Exception 1: Flash Sale
    if has_phrase("flash sale") and not has_negated_phrase("flash sale"):
        exceptions_found.append({
            "type": "flash_sale_exception",
            "rule": "Orders purchased under Flash Sale promotions are not refundable.",
            "source": "policy_refund_v4.txt",
        })

    # Exception 2: Digital product
    if any(has_phrase(kw) and not has_negated_phrase(kw) for kw in ["license key", "license", "subscription", "digital product", "kỹ thuật số", "ky thuat so"]):
        exceptions_found.append({
            "type": "digital_product_exception",
            "rule": "Digital products such as license keys and subscriptions are not refundable.",
            "source": "policy_refund_v4.txt",
        })

    # Exception 3: Activated product
    if any(has_phrase(kw) and not has_negated_phrase(kw) for kw in ["đã kích hoạt", "da kich hoat", "activated", "đã đăng ký", "da dang ky"]):
        exceptions_found.append({
            "type": "activated_exception",
            "rule": "Activated or account-registered products are not refundable.",
            "source": "policy_refund_v4.txt",
        })

    # If we hit any hard exception, the normal refund path no longer applies.
    policy_applies = len(exceptions_found) == 0

    # Temporal scoping matters because old orders may fall under a policy version we do not have.
    policy_name = "refund_policy_v4"
    policy_version_note = ""
    order_dates = re.findall(r"(\d{2})/(\d{2})/(\d{4})", task)
    cutoff_date = datetime.strptime("01/02/2026", "%d/%m/%Y").date()
    for day_text, month_text, year_text in order_dates:
        try:
            order_date = datetime.strptime(f"{day_text}/{month_text}/{year_text}", "%d/%m/%Y").date()
        except ValueError:
            continue
        if order_date < cutoff_date:
            policy_version_note = (
                "Order date is before 01/02/2026, so refund policy v3 applies. "
                "The current document set only contains v4, so the answer should abstain from claiming v3 details."
            )
            policy_applies = False
            break

    if "trước 01/02/2026" in task_lower or "truoc 01/02/2026" in task_lower:
        policy_version_note = (
            "Order date is before 01/02/2026, so refund policy v3 applies. "
            "The current document set only contains v4, so the answer should abstain from claiming v3 details."
        )
        policy_applies = False

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
        "exceptions_found": exceptions_found,
        "source": sources or ["policy_refund_v4.txt"],
        "policy_version_note": policy_version_note,
        "rule": exceptions_found[0]["rule"] if exceptions_found else (
            "Refund is allowed only when the product is manufacturer-defective, requested within 7 working days, and has not been used or activated."
        ),
        "explanation": "Analyzed via rule-based policy check. TODO: upgrade to LLM-based analysis.",
    }


# ————————————————————————————————————————————————
# Worker Entry Point
# ————————————————————————————————————————————————

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
    state.setdefault("mcp_tool_called", [])
    state.setdefault("mcp_result", [])

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
        # Step 1: Backfill missing evidence through MCP if supervisor marked this task as tool-worthy.
        if not chunks and needs_tool:
            mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_result)
            state["mcp_tool_called"].append("search_kb")
            state["mcp_result"].append(mcp_result.get("output"))
            state["history"].append(f"[{WORKER_NAME}] called MCP search_kb")

            if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                chunks = mcp_result["output"]["chunks"]
                state["retrieved_chunks"] = chunks
                state["retrieved_sources"] = mcp_result["output"].get(
                    "sources",
                    list({chunk.get("source", "unknown") for chunk in chunks if chunk}),
                )

        # Step 2: Run the local rule-based policy analysis on the gathered evidence.
        policy_result = analyze_policy(task, chunks)

        # Access questions need a second pass because approvals/emergency bypass come from the SOP tool logic.
        if any(kw in task.lower() for kw in ["cấp quyền", "cap quyen", "access", "level 2", "level 3", "level 4", "admin access"]):
            import re

            level_match = re.search(r"level\s*(\d)", task.lower())
            access_level = int(level_match.group(1)) if level_match else 3
            is_emergency = any(kw in task.lower() for kw in ["emergency", "khẩn cấp", "khan cap", "p1", "2am"])
            requester_role = "contractor" if "contractor" in task.lower() else "employee"

            access_mcp_result = _call_mcp_tool(
                "check_access_permission",
                {
                    "access_level": access_level,
                    "requester_role": requester_role,
                    "is_emergency": is_emergency,
                },
            )
            state["mcp_tools_used"].append(access_mcp_result)
            state["mcp_tool_called"].append("check_access_permission")
            state["mcp_result"].append(access_mcp_result.get("output"))
            state["history"].append(f"[{WORKER_NAME}] called MCP check_access_permission")

            if access_mcp_result.get("output") and not access_mcp_result["output"].get("error"):
                access_output = access_mcp_result["output"]
                policy_result.update({
                    "policy_name": "access_control_sop",
                    "policy_applies": bool(access_output.get("can_grant", False)),
                    "source": list(set(policy_result.get("source", []) + ["access_control_sop.txt"])),
                    "required_approvers": access_output.get("required_approvers", []),
                    "approver_count": access_output.get("approver_count", len(access_output.get("required_approvers", []))),
                    "highest_approver": (access_output.get("required_approvers", []) or [None])[-1],
                    "emergency_override": access_output.get("emergency_override", False),
                    "rule": (
                        "Temporary emergency access can be granted only when the SOP explicitly allows emergency override."
                        if access_output.get("emergency_override", False)
                        else f"Standard approval chain applies: {', '.join(access_output.get('required_approvers', []))}."
                    ),
                    "explanation": "Analyzed via MCP access permission check plus rule-based policy logic.",
                })

                if is_emergency and not access_output.get("emergency_override", False):
                    # Make the emergency restriction explicit so synthesis can surface it clearly.
                    policy_result["exceptions_found"] = [{
                        "type": "no_emergency_bypass",
                        "rule": f"Level {access_level} does not support emergency bypass. Standard approval chain still applies.",
                        "source": "access_control_sop.txt",
                    }]
                    policy_result["policy_applies"] = False
                    policy_result["rule"] = policy_result["exceptions_found"][0]["rule"]

        state["policy_result"] = policy_result

        # Step 3: Optionally enrich the trace with ticket metadata for incident-style tasks.
        if needs_tool and any(kw in task.lower() for kw in ["ticket", "p1", "jira"]):
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
            state["mcp_tools_used"].append(mcp_result)
            state["mcp_tool_called"].append("get_ticket_info")
            state["mcp_result"].append(mcp_result.get("output"))
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


# ————————————————————————————————————————————————
# Test độc lập
# ————————————————————————————————————————————————

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
