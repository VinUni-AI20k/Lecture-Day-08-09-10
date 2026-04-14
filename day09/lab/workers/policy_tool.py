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

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

WORKER_NAME = "policy_tool_worker"

REFUND_KEYWORDS = ["hoàn tiền", "refund", "flash sale", "license", "digital", "subscription", "activated"]
ACCESS_KEYWORDS = ["cấp quyền", "access", "level 1", "level 2", "level 3", "admin", "emergency", "khẩn cấp"]
TICKET_ID_PATTERN = re.compile(r"\b(?:IT-\d+|P1-LATEST)\b", re.IGNORECASE)


def _is_access_intent(task_lower: str) -> bool:
    return any(kw in task_lower for kw in ACCESS_KEYWORDS) and not any(kw in task_lower for kw in REFUND_KEYWORDS)


def _extract_ticket_id(task: str) -> str | None:
    match = TICKET_ID_PATTERN.search(task or "")
    if not match:
        return None
    return match.group(0).upper()


def _infer_access_level(task: str) -> int:
    task_lower = task.lower()
    if "level 3" in task_lower or "l3" in task_lower:
        return 3
    if "level 2" in task_lower or "l2" in task_lower:
        return 2
    if "level 1" in task_lower or "l1" in task_lower:
        return 1
    return 2 if "access" in task_lower or "cấp quyền" in task_lower else 1


# ─────────────────────────────────────────────
# MCP Client — Sprint 3: Thay bằng real MCP call
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool.

    Sprint 3 TODO: Implement bằng cách import mcp_server hoặc gọi HTTP.

    Hiện tại: Import trực tiếp từ mcp_server.py (trong-process mock).
    """
    mode_raw = os.getenv("MCP_SERVER_MODE", "http")
    mode = mode_raw.split("#", 1)[0].strip().lower()
    server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8080").rstrip("/")

    def _record(output: dict | None, error: dict | None, transport: str) -> dict:
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": output,
            "error": error,
            "transport": transport,
            "timestamp": datetime.now().isoformat(),
        }

    def _http_call() -> dict:
        payload = {
            "tool": tool_name,
            "input": tool_input,
            "metadata": {
                "requested_by": WORKER_NAME,
                "allow_side_effects": False,
            },
        }
        request = urllib.request.Request(
            f"{server_url}/tools/call",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
            if body.get("ok"):
                return _record(body.get("output", {}), None, "http")
            return _record(None, body.get("error") or {"code": "MCP_HTTP_ERROR", "reason": "unknown"}, "http")

    # HTTP path only when explicitly requested
    if mode in {"http", "hybrid", "real"}:
        try:
            return _http_call()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError) as exc:
            # Fallback 1: in-process real MCP dispatch (still guarded)
            try:
                from mcp_server import dispatch_tool

                output = dispatch_tool(
                    tool_name,
                    tool_input,
                    metadata={"requested_by": WORKER_NAME, "allow_side_effects": False},
                )
                if isinstance(output, dict) and "error" in output:
                    return _record(None, output["error"] if isinstance(output["error"], dict) else {"code": "MCP_ERROR", "reason": str(output["error"])}, "inprocess-real")
                return _record(output, None, "inprocess-real")
            except Exception as real_exc:
                # Fallback 2: separated mock server (hybrid compatibility)
                if mode in {"hybrid"}:
                    try:
                        from mcp_mock_server import dispatch_tool as dispatch_mock

                        out = dispatch_mock(tool_name, tool_input)
                        if isinstance(out, dict) and "error" in out:
                            return _record(None, out["error"] if isinstance(out["error"], dict) else {"code": "MCP_ERROR", "reason": str(out["error"])}, "inprocess-mock")
                        return _record(out, None, "inprocess-mock")
                    except Exception as mock_exc:
                        return _record(
                            None,
                            {
                                "code": "MCP_CALL_FAILED",
                                "reason": f"http={exc}; real_fallback={real_exc}; mock_fallback={mock_exc}",
                            },
                            "failed",
                        )
                return _record(
                    None,
                    {"code": "MCP_CALL_FAILED", "reason": f"http={exc}; real_fallback={real_exc}"},
                    "failed",
                )

    # Explicit mock-only mode (fast path, skip HTTP attempt)
    try:
        from mcp_mock_server import dispatch_tool as dispatch_mock

        out = dispatch_mock(tool_name, tool_input)
        if isinstance(out, dict) and "error" in out:
            return _record(None, out["error"] if isinstance(out["error"], dict) else {"code": "MCP_ERROR", "reason": str(out["error"])}, "inprocess-mock")
        return _record(out, None, "inprocess-mock")
    except Exception as exc:
        return _record(None, {"code": "MCP_CALL_FAILED", "reason": str(exc)}, "failed")


# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────

def analyze_policy(task: str, chunks: list, access_check: dict | None = None) -> dict:
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

    def _negated(*phrases: str) -> bool:
        return any(phrase in task_lower for phrase in phrases)

    # --- Rule-based exception detection ---
    exceptions_found = []

    # Exception 1: Flash Sale
    if "flash sale" in task_lower and not _negated("không phải flash sale", "khong phai flash sale", "not flash sale"):
        exceptions_found.append({
            "type": "flash_sale_exception",
            "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
            "source": "policy_refund_v4.txt",
        })

    # Exception 2: Digital product
    if any(kw in task_lower for kw in ["license key", "license", "subscription", "kỹ thuật số", "digital"]):
        exceptions_found.append({
            "type": "digital_product_exception",
            "rule": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })

    # Exception 3: Activated product
    if any(kw in task_lower for kw in ["đã kích hoạt", "đã đăng ký", "đã sử dụng", "activated"]) and not any(
        kw in task_lower for kw in ["chưa kích hoạt", "không kích hoạt", "not activated", "chua kich hoat"]
    ):
        exceptions_found.append({
            "type": "activated_exception",
            "rule": "Sản phẩm đã kích hoạt hoặc đăng ký tài khoản không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })

    # Determine policy_applies
    policy_applies = len(exceptions_found) == 0

    # Determine policy domain from task first (avoid context contamination)
    is_refund_task = any(kw in task_lower for kw in REFUND_KEYWORDS)
    is_access_task = any(kw in task_lower for kw in ACCESS_KEYWORDS)

    if not is_refund_task and not is_access_task:
        # fallback to context only when task itself is ambiguous
        is_refund_task = any(kw in context_text for kw in REFUND_KEYWORDS)
        is_access_task = any(kw in context_text for kw in ACCESS_KEYWORDS)

    policy_name = "refund_policy_v4" if is_refund_task else "access_control_sop" if is_access_task else "refund_policy_v4"
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

    sources = list(dict.fromkeys([c.get("source", "unknown") for c in chunks if c]))

    if is_access_task and not is_refund_task:
        approvers = []
        emergency_override = False
        notes = []
        if access_check and not access_check.get("error"):
            approvers = access_check.get("required_approvers", [])
            emergency_override = bool(access_check.get("emergency_override", False))
            notes = access_check.get("notes", [])
            if access_check.get("source") and access_check.get("source") not in sources:
                sources.append(access_check.get("source"))

        return {
            "policy_applies": not (access_check or {}).get("error", False),
            "policy_name": "access_control_sop",
            "exceptions_found": [],
            "source": sources or ["access_control_sop.txt"],
            "policy_version_note": "",
            "required_approvers": approvers,
            "emergency_override": emergency_override,
            "notes": notes,
            "summary": "Access policy evaluated using Access Control SOP and MCP tool check.",
            "explanation": "Rule-based access policy analysis with MCP validation.",
        }

    return {
        "policy_applies": False if policy_version_note else policy_applies,
        "policy_name": "refund_policy_v4",
        "exceptions_found": exceptions_found,
        "source": sources or ["policy_refund_v4.txt"],
        "policy_version_note": policy_version_note,
        "summary": (
            "Temporal scoping requires manual confirmation for pre-01/02 orders."
            if policy_version_note and not exceptions_found
            else "Refund policy evaluated using policy_refund_v4 with exception detection."
        ),
        "explanation": "Analyzed via rule-based policy check.",
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
    state.setdefault("worker_io_logs", [])

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
        access_intent = _is_access_intent(task_lower)
        explicit_ticket_id = _extract_ticket_id(task)

        # Step 1: lấy chunks nếu chưa có
        if not chunks and needs_tool:
            if access_intent:
                # Latency optimization: access intents can use local retrieval directly,
                # reserve MCP calls for policy checks where needed.
                from workers.retrieval import retrieve_dense

                chunks = retrieve_dense(task, top_k=3)
                state["retrieved_chunks"] = chunks
                state["history"].append(f"[{WORKER_NAME}] used local retrieval for access intent")
            else:
                mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
                state["mcp_tools_used"].append(mcp_result)
                state["history"].append(f"[{WORKER_NAME}] called MCP search_kb")

                if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                    chunks = mcp_result["output"]["chunks"]
                    state["retrieved_chunks"] = chunks

        if not chunks:
            # Fallback retrieval without MCP
            from workers.retrieval import retrieve_dense
            chunks = retrieve_dense(task, top_k=3)
            state["retrieved_chunks"] = chunks

        state["retrieved_sources"] = list(dict.fromkeys([c.get("source", "unknown") for c in chunks]))

        access_check = None
        if access_intent:
            access_level = _infer_access_level(task)
            access_input = {
                "access_level": access_level,
                "requester_role": "contractor" if "contractor" in task_lower else "employee",
                "is_emergency": any(kw in task_lower for kw in ["emergency", "khẩn cấp", "p1"]),
            }
            access_mcp = _call_mcp_tool("check_access_permission", access_input)
            state["mcp_tools_used"].append(access_mcp)
            state["history"].append(f"[{WORKER_NAME}] called MCP check_access_permission")
            access_check = access_mcp.get("output")

        # Step 2: Phân tích policy
        policy_result = analyze_policy(task, chunks, access_check=access_check)
        state["policy_result"] = policy_result

        # Step 3: optional ticket lookup only when explicit ticket id is provided.
        if needs_tool and explicit_ticket_id:
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": explicit_ticket_id})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP get_ticket_info")

        worker_io["output"] = {
            "policy_applies": policy_result["policy_applies"],
            "policy_name": policy_result.get("policy_name"),
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

    state["worker_io_logs"].append(worker_io)
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
