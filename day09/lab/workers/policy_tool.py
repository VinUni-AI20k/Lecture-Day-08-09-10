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
from datetime import datetime
from typing import Optional

WORKER_NAME = "policy_tool_worker"


# ─────────────────────────────────────────────
# MCP Client — Sprint 3: Thay bằng real MCP call
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool via HTTP để chứng minh External Capability (Sprint 3 Advanced).
    Sử dụng httpx để gửi REST request đến FastAPI/MCP server đang chạy.
    Fallback về mock cục bộ (dispatch_tool) nếu server HTTP chưa bật.
    """
    from datetime import datetime
    import httpx
    
    SERVER_URL = "http://localhost:8000/call"

    try:
        # Gọi HTTP server externe cho MCP tool
        payload = {"tool_name": tool_name, "tool_input": tool_input}
        response = httpx.post(SERVER_URL, json=payload, timeout=2.0)
        response.raise_for_status()
        
        result = response.json()
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": result,
            "error": None,
            "timestamp": datetime.now().isoformat(),
            "source": "http_mcp_server"
        }
    except Exception as e:
        # Fallback về mock class nếu ko có HTTP server để test không lỗi
        try:
            import os, sys
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from mcp_server import dispatch_tool
            
            result = dispatch_tool(tool_name, tool_input)
            return {
                "tool": tool_name,
                "input": tool_input,
                "output": result,
                "error": None,
                "timestamp": datetime.now().isoformat(),
                "source": "local_mock_fallback"
            }
        except Exception as inner_e:
            return {
                "tool": tool_name,
                "input": tool_input,
                "output": None,
                "error": {"code": "MCP_CALL_FAILED", "reason": f"HTTP Failed: {e} | Fallback Failed: {inner_e}"},
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

    # Initialize state fields if not exist
    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("mcp_tools_used", [])
    state.setdefault("worker_io_logs", [])

    state["workers_called"].append(WORKER_NAME)

    # Contract-compliant worker_io log
    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "retrieved_chunks": chunks,  # Include full context
            "needs_tool": needs_tool,
        },
        "output": {},
        "error": None,
        "timestamp": datetime.now().isoformat(),
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
        
        # Contract-compliant policy_result format
        contract_compliant_result = {
            "policy_applies": policy_result["policy_applies"],
            "policy_name": policy_result["policy_name"],
            "exceptions_found": policy_result.get("exceptions_found", []),
            "source": policy_result.get("source", []),
            "policy_version_note": policy_result.get("policy_version_note", ""),
        }
        
        state["policy_result"] = contract_compliant_result

        # Step 3: Nếu cần thêm info từ MCP (e.g., ticket status), gọi get_ticket_info
        if needs_tool and any(kw in task.lower() for kw in ["ticket", "p1", "jira"]):
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP get_ticket_info")

        # Contract-compliant worker_io output
        worker_io["output"] = {
            "policy_result": contract_compliant_result,
            "mcp_tools_used": state["mcp_tools_used"].copy(),
            "policy_applies": contract_compliant_result["policy_applies"],
            "exceptions_count": len(contract_compliant_result["exceptions_found"]),
        }
        
        state["history"].append(
            f"[{WORKER_NAME}] policy_applies={contract_compliant_result['policy_applies']}, "
            f"exceptions={len(contract_compliant_result['exceptions_found'])}, "
            f"mcp_calls={len(state['mcp_tools_used'])}"
        )

    except Exception as e:
        # Contract-compliant error handling
        error_obj = {"code": "POLICY_CHECK_FAILED", "reason": str(e)}
        worker_io["error"] = error_obj
        
        # Fallback policy_result on error
        state["policy_result"] = {
            "policy_applies": False,
            "policy_name": "error_fallback",
            "exceptions_found": [],
            "source": [],
            "policy_version_note": f"Policy check failed: {str(e)}",
        }
        
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state["worker_io_logs"].append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Policy Tool Worker — Contract Compliance Test")
    print("=" * 60)

    test_cases = [
        {
            "name": "Flash Sale Exception",
            "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
            "retrieved_chunks": [
                {"text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền theo Điều 3 chính sách v4.", "source": "policy_refund_v4.txt", "score": 0.9}
            ],
            "expected_policy_applies": False,
            "expected_exception_types": ["flash_sale_exception"],
        },
        {
            "name": "License Key Exception",
            "task": "Khách hàng muốn hoàn tiền license key đã kích hoạt.",
            "retrieved_chunks": [
                {"text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền theo Điều 3.", "source": "policy_refund_v4.txt", "score": 0.88}
            ],
            "expected_policy_applies": False,
            "expected_exception_types": ["digital_product_exception", "activated_exception"],
        },
        {
            "name": "Activated Product Exception",
            "task": "Khách hàng yêu cầu hoàn tiền sản phẩm đã đăng ký và kích hoạt.",
            "retrieved_chunks": [
                {"text": "Sản phẩm đã kích hoạt hoặc đăng ký tài khoản không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
            "expected_policy_applies": False,
            "expected_exception_types": ["activated_exception"],
        },
        {
            "name": "Valid Refund Case",
            "task": "Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạt.",
            "retrieved_chunks": [
                {"text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất, chưa dùng.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
            "expected_policy_applies": True,
            "expected_exception_types": [],
        },
        {
            "name": "No Evidence Case",
            "task": "Khách hàng yêu cầu hoàn tiền nhưng không có tài liệu.",
            "retrieved_chunks": [],
            "expected_policy_applies": True,  # Default allow when no evidence
            "expected_exception_types": [],
        },
        {
            "name": "MCP Tool Case",
            "task": "Kiểm tra policy cho ticket P1 khẩn cấp",
            "retrieved_chunks": [],
            "needs_tool": True,
            "expected_policy_applies": True,
            "expected_exception_types": [],
            "expected_mcp_calls": ["search_kb", "get_ticket_info"],
        },
    ]

    all_passed = True

    for tc in test_cases:
        print(f"\n[TEST] {tc['name']}")
        print(f"Task: {tc['task'][:70]}...")
        
        # Prepare test state
        test_state = {
            "task": tc["task"],
            "retrieved_chunks": tc.get("retrieved_chunks", []),
            "needs_tool": tc.get("needs_tool", False),
        }
        
        # Run policy tool worker
        result = run(test_state.copy())
        
        # Validate contract compliance
        pr = result.get("policy_result", {})
        
        # Check 1: policy_result structure
        required_fields = ["policy_applies", "policy_name", "exceptions_found", "source"]
        for field in required_fields:
            if field not in pr:
                print(f"  ❌ FAIL: Missing field '{field}' in policy_result")
                all_passed = False
                continue
        
        # Check 2: policy_applies value
        expected_applies = tc["expected_policy_applies"]
        actual_applies = pr.get("policy_applies")
        if actual_applies != expected_applies:
            print(f"  ❌ FAIL: policy_applies expected {expected_applies}, got {actual_applies}")
            all_passed = False
        else:
            print(f"  ✅ policy_applies: {actual_applies}")
        
        # Check 3: exception types
        expected_exceptions = tc["expected_exception_types"]
        actual_exceptions = [ex["type"] for ex in pr.get("exceptions_found", [])]
        if set(actual_exceptions) != set(expected_exceptions):
            print(f"  ❌ FAIL: exceptions expected {expected_exceptions}, got {actual_exceptions}")
            all_passed = False
        else:
            for ex in pr.get("exceptions_found", []):
                print(f"  ✅ exception: {ex['type']} — {ex['rule'][:60]}...")
        
        # Check 4: MCP tool calls
        expected_mcp = tc.get("expected_mcp_calls", [])
        actual_mcp = [call["tool"] for call in result.get("mcp_tools_used", [])]
        if set(actual_mcp) != set(expected_mcp):
            print(f"  ❌ FAIL: MCP calls expected {expected_mcp}, got {actual_mcp}")
            all_passed = False
        else:
            for call in result.get("mcp_tools_used", []):
                print(f"  ✅ MCP call: {call['tool']}")
        
        # Check 5: worker_io_logs format
        worker_logs = result.get("worker_io_logs", [])
        policy_logs = [log for log in worker_logs if log.get("worker") == WORKER_NAME]
        if not policy_logs:
            print(f"  ❌ FAIL: No worker_io_log found for {WORKER_NAME}")
            all_passed = False
        else:
            latest_log = policy_logs[-1]
            if "input" not in latest_log or "output" not in latest_log:
                print(f"  ❌ FAIL: worker_io_log missing required fields")
                all_passed = False
            else:
                print(f"  ✅ worker_io_log format compliant")
        
        # Check 6: history logging
        history = result.get("history", [])
        policy_entries = [h for h in history if WORKER_NAME in h]
        if not policy_entries:
            print(f"  ❌ FAIL: No history entries found for {WORKER_NAME}")
            all_passed = False
        else:
            print(f"  ✅ history entries: {len(policy_entries)}")

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED — Contract compliance validated!")
        print("✅ Policy Tool Worker ready for integration")
    else:
        print("❌ SOME TESTS FAILED — Check implementation")
    print("=" * 60)