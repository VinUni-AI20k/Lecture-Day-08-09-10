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
import sys
from typing import Optional
from pathlib import Path

# Ensure parent directory (day09/lab) is importable when running this file directly.
LAB_ROOT = str(Path(__file__).resolve().parent.parent)
if LAB_ROOT not in sys.path:
    sys.path.insert(0, LAB_ROOT)

WORKER_NAME = "policy_tool_worker"


# ─────────────────────────────────────────────
# MCP Client — Sprint 3: Thay bằng real MCP call
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict, retry: int = 1) -> dict:
    """
    Gọi MCP tool.

    Sprint 3 TODO: Implement bằng cách import mcp_server hoặc gọi HTTP.

    Hiện tại: Import trực tiếp từ mcp_server.py (trong-process mock).
    """
    from datetime import datetime

    last_error = None
    for attempt in range(retry + 1):
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
            last_error = e
            if attempt < retry:
                continue

    return {
        "tool": tool_name,
        "input": tool_input,
        "output": None,
        "error": {"code": "MCP_CALL_FAILED", "reason": str(last_error)},
        "timestamp": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────


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
    from dotenv import load_dotenv

    load_dotenv()

    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks]).lower()

    # --- Rule-based exception detection ---
    exceptions_found = []

    # Exception 1: Flash Sale
    if "flash sale" in task_lower or "flash sale" in context_text:
        exceptions_found.append(
            {
                "type": "flash_sale_exception",
                "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
                "source": "policy_refund_v4.txt",
            }
        )

    # Exception 2: Digital product
    if any(
        kw in task_lower
        for kw in ["license key", "license", "subscription", "kỹ thuật số"]
    ):
        exceptions_found.append(
            {
                "type": "digital_product_exception",
                "rule": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền (Điều 3).",
                "source": "policy_refund_v4.txt",
            }
        )

    # Exception 3: Activated product
    if any(kw in task_lower for kw in ["đã kích hoạt", "đã đăng ký", "đã sử dụng"]):
        exceptions_found.append(
            {
                "type": "activated_exception",
                "rule": "Sản phẩm đã kích hoạt hoặc đăng ký tài khoản không được hoàn tiền (Điều 3).",
                "source": "policy_refund_v4.txt",
            }
        )

    # Determine policy_applies
    policy_applies = len(exceptions_found) == 0

    # Determine which policy version applies (temporal scoping)
    # TODO: Check nếu đơn hàng trước 01/02/2026 → v3 applies (không có docs, nên flag cho synthesis)
    policy_name = "refund_policy_v4"
    policy_version_note = ""
    if "31/01" in task_lower or "30/01" in task_lower or "trước 01/02" in task_lower:
        policy_version_note = "Đơn hàng đặt trước 01/02/2026 áp dụng chính sách v3 (không có trong tài liệu hiện tại)."

    # Optional: LLM-based explanation (Gemini)
    explanation = "Analyzed via rule-based policy check."
    gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            from google import genai

            client = genai.Client(api_key=gemini_key)
            prompt = (
                "Bạn là policy analyst. Dựa vào context, xác định policy áp dụng và các exceptions.\n\n"
                f"Task: {task}\n\nContext:\n"
                + "\n".join([c.get("text", "") for c in chunks])
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            analysis = response.text
            if analysis:
                explanation = analysis
        except Exception as e:
            explanation += f" (LLM analysis skipped: {e})"

    sources = list({c.get("source", "unknown") for c in chunks if c})

    return {
        "policy_applies": policy_applies,
        "policy_name": policy_name,
        "exceptions_found": exceptions_found,
        "source": sources,
        "policy_version_note": policy_version_note,
        "explanation": explanation,
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
    state.setdefault("mcp_result", [])
    state.setdefault("mcp_tool_called", False)

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
        task_lower = task.lower()
        is_ticket_task = any(
            kw in task_lower for kw in ["ticket", "p1", "jira", "escalation"]
        )
        is_access_task = any(
            kw in task_lower
            for kw in [
                "access",
                "cấp quyền",
                "cap quyen",
                "level 1",
                "level 2",
                "level 3",
                "level 4",
            ]
        )

        # Step 1: Nếu chưa có chunks, gọi MCP search_kb để mở rộng evidence
        if not chunks and needs_tool:
            mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_result)
            state["mcp_result"].append(mcp_result)
            state["mcp_tool_called"] = True
            state["history"].append(f"[{WORKER_NAME}] called MCP search_kb")

            if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                chunks = mcp_result["output"]["chunks"]
                state["retrieved_chunks"] = chunks

        # Step 1b: Với access requests, gọi thêm access permission tool để lấy approvers.
        if needs_tool and is_access_task:
            access_level = (
                3 if "level 3" in task_lower else 2 if "level 2" in task_lower else 1
            )
            mcp_result = _call_mcp_tool(
                "check_access_permission",
                {
                    "access_level": access_level,
                    "requester_role": (
                        "contractor" if "contractor" in task_lower else "employee"
                    ),
                    "is_emergency": "emergency" in task_lower
                    or "khẩn cấp" in task_lower,
                },
            )
            state["mcp_tools_used"].append(mcp_result)
            state["mcp_result"].append(mcp_result)
            state["mcp_tool_called"] = True
            state["history"].append(
                f"[{WORKER_NAME}] called MCP check_access_permission"
            )

        # Step 2: Phân tích policy
        policy_result = analyze_policy(task, chunks)
        state["policy_result"] = policy_result

        # Step 3: Nếu cần thêm info từ MCP (e.g., ticket status), gọi get_ticket_info
        if needs_tool and is_ticket_task:
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
            state["mcp_tools_used"].append(mcp_result)
            state["mcp_result"].append(mcp_result)
            state["mcp_tool_called"] = True
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
                {
                    "text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền.",
                    "source": "policy_refund_v4.txt",
                    "score": 0.9,
                }
            ],
        },
        {
            "task": "Khách hàng muốn hoàn tiền license key đã kích hoạt.",
            "retrieved_chunks": [
                {
                    "text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền.",
                    "source": "policy_refund_v4.txt",
                    "score": 0.88,
                }
            ],
        },
        {
            "task": "Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạt.",
            "retrieved_chunks": [
                {
                    "text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất, chưa dùng.",
                    "source": "policy_refund_v4.txt",
                    "score": 0.85,
                }
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
