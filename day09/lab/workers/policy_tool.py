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
import json
import requests
from typing import Optional
from datetime import datetime

WORKER_NAME = "policy_tool_worker"


# ─────────────────────────────────────────────
# MCP Client — Sprint 3: Real HTTP MCP Call
# ─────────────────────────────────────────────

# Configure your actual MCP Server URL here

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool thông qua import trực tiếp (Option Standard trong Sprint 3).
    """
    from datetime import datetime
    try:
        # Import hàm dispatch_tool từ file mcp_server.py của project
        from mcp_server import dispatch_tool
        
        result = dispatch_tool(tool_name, tool_input)
        
        # Nếu mcp_server trả về lỗi nội bộ
        if isinstance(result, dict) and "error" in result:
            return {
                "tool": tool_name,
                "input": tool_input,
                "output": None,
                "error": {"code": "MCP_TOOL_ERROR", "reason": result["error"]},
                "timestamp": datetime.now().isoformat(),
            }

        return {
            "tool": tool_name,
            "input": tool_input,
            "output": result, 
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }

    except ImportError:
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": None,
            "error": {"code": "MCP_IMPORT_FAILED", "reason": "Không tìm thấy file mcp_server.py. Hãy đảm bảo nó nằm cùng thư mục hoặc trong PYTHONPATH."},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": None,
            "error": {"code": "MCP_SYSTEM_ERROR", "reason": str(e)},
            "timestamp": datetime.now().isoformat(),
        }

# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────

def analyze_policy(task: str, chunks: list) -> dict:
    """
    Phân tích policy dựa trên context chunks bằng phương pháp Hybrid (Rule-based + LLM).
    
    Returns:
        dict with: policy_applies, policy_name, exceptions_found, source, rule, policy_version_note, explanation
    """
    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks]).lower()

    # ─────────────────────────────────────────────
    # PHASE 1: Rule-Based Fast Pass
    # ─────────────────────────────────────────────
    exceptions_found = []

    if "flash sale" in task_lower or "flash sale" in context_text:
        exceptions_found.append({
            "type": "flash_sale_exception",
            "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
            "source": "rule_engine"
        })

    if any(kw in task_lower for kw in ["license key", "license", "subscription", "kỹ thuật số"]):
        exceptions_found.append({
            "type": "digital_product_exception",
            "rule": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền (Điều 3).",
            "source": "rule_engine"
        })

    if any(kw in task_lower for kw in ["đã kích hoạt", "đã đăng ký", "đã sử dụng"]):
        exceptions_found.append({
            "type": "activated_exception",
            "rule": "Sản phẩm đã kích hoạt hoặc đăng ký tài khoản không được hoàn tiền (Điều 3).",
            "source": "rule_engine"
        })

    # ─────────────────────────────────────────────
    # PHASE 2: LLM-Based Semantic Analysis
    # ─────────────────────────────────────────────
    llm_exceptions = []
    llm_reasoning = "LLM check skipped or failed."
    policy_name = "refund_policy_v4"
    policy_version_note = ""

    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI()

            current_date = "April 14, 2026"
            
            system_prompt = f"""
            Bạn là một Policy Analyst chuyên nghiệp. Trích xuất thông tin hoàn tiền dựa vào Task của người dùng và Context.
            Hôm nay là {current_date}. 
            Lưu ý quan trọng:
            - Nếu đơn hàng diễn ra trước ngày 01/02/2026, policy_name phải là 'refund_policy_v3'. Ngược lại là 'refund_policy_v4'.
            
            Trạng thái trả về BẮT BUỘC phải là JSON hợp lệ theo format sau:
            {{
                "policy_name": "tên policy (v3 hoặc v4)",
                "exceptions": [
                    {{
                        "type": "loại exception", 
                        "rule": "lý do vi phạm", 
                        "source": "llm_engine"
                    }}
                ],
                "reasoning": "Giải thích ngắn gọn tại sao"
            }}
            Nếu không có ngoại lệ nào, mảng 'exceptions' để rỗng [].
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Task: {task}\n\nContext:\n{context_text}"}
                ],
                temperature=0.0
            )

            llm_result = json.loads(response.choices[0].message.content)
            llm_exceptions = llm_result.get("exceptions", [])
            llm_reasoning = llm_result.get("reasoning", "")
            policy_name = llm_result.get("policy_name", "refund_policy_v4")

        except Exception as e:
            llm_reasoning = f"LLM error: {str(e)}"
    else:
        if any(kw in task_lower for kw in ["31/01", "30/01", "trước 01/02", "trước tháng 2"]):
            policy_name = "refund_policy_v3"

    # ─────────────────────────────────────────────
    # PHASE 3: Synthesis & Deduplication
    # ─────────────────────────────────────────────
    if "v3" in policy_name:
        policy_version_note = "Đơn hàng đặt trước 01/02/2026 áp dụng chính sách v3 (không có trong tài liệu hiện tại, cần escalate)."

    all_exceptions = exceptions_found + llm_exceptions
    merged_exceptions = []
    seen_types = set()
    
    for ex in all_exceptions:
        if ex["type"] not in seen_types:
            merged_exceptions.append(ex)
            seen_types.add(ex["type"])

    policy_applies = len(merged_exceptions) == 0
    sources_list = list({c.get("source", "unknown") for c in chunks if c})

    # Surface top-level rule and source to match strictly with AgentState schema
    if merged_exceptions:
        top_level_rule = merged_exceptions[0]["rule"]
        top_level_source = merged_exceptions[0]["source"]
    else:
        top_level_rule = "Thỏa mãn điều kiện hoàn tiền cơ bản."
        top_level_source = sources_list[0] if sources_list else "unknown"

    return {
        "policy_applies": policy_applies,
        "policy_name": policy_name,
        "exceptions_found": merged_exceptions,
        "source": top_level_source,
        "rule": top_level_rule,
        "all_sources": sources_list,
        "policy_version_note": policy_version_note,
        "explanation": f"Hybrid Analysis. Rule-engine flags: {len(exceptions_found)}. LLM Reasoning: {llm_reasoning}"
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

    # FIX: Append to singular 'worker_io_log' to match AgentState perfectly
    state.setdefault("worker_io_log", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Policy Tool Worker — Standalone Test (Hybrid Mode)")
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
        {
            "task": "Đơn hàng đặt ngày 15/01/2026, mã ABC, chưa bóc seal, muốn trả lại...",
            "retrieved_chunks": [
                {"text": "Chính sách v4 áp dụng từ 01/02/2026. Các đơn trước đó áp dụng v3.", "source": "policy_refund_v4.txt", "score": 0.95}
            ],
        },
        {
            "name": "3. Semantic Match (LLM Engine)",
            "task": "Tôi mua phần mềm diệt virus bản tải về, chưa nhập mã code, muốn trả lại.",
            "retrieved_chunks": [{"text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.88}],
            "needs_tool": False
        },
        {
            "name": "4. Time Expiration (LLM Engine)",
            "task": "Đơn hàng nhận ngày 01/04/2026. Sản phẩm bị lỗi, tôi muốn trả lại.",
            "retrieved_chunks": [{"text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất.", "source": "policy_refund_v4.txt", "score": 0.85}],
            "needs_tool": False
        },
        {
            "name": "5. Trigger MCP (search_kb)",
            "task": "Khách hàng muốn hoàn tiền áo thun mặc không vừa.",
            "retrieved_chunks": [], # Cố tình để trống để ép gọi tool
            "needs_tool": True      # Cờ báo cho phép gọi tool
        },
        {
            "name": "6. Trigger MCP (get_ticket_info)",
            "task": "Kiểm tra giúp tôi ticket P1-5432 về việc hoàn tiền đơn hàng bị hỏng.",
            "retrieved_chunks": [{"text": "Hoàn tiền cho sản phẩm hỏng được chấp nhận.", "source": "policy_refund_v4.txt", "score": 0.9}],
            "needs_tool": True      # Có chứa từ khóa 'ticket' và 'p1'
        }
    ]

    for tc in test_cases:
        print(f"\n▶ Task: {tc['task'][:70]}...")
        
        # Test full worker run to verify AgentState mutations
        state = {
            "task": tc["task"],
            "retrieved_chunks": tc["retrieved_chunks"],
            "needs_tool": False
        }
        
        final_state = run(state)
        pr = final_state.get("policy_result", {})
        
        print(f"  policy_applies: {pr.get('policy_applies')}")
        print(f"  policy_name: {pr.get('policy_name')}")
        print(f"  top_rule: {pr.get('rule')}")
        print(f"  top_source: {pr.get('source')}")
        
        if pr.get("policy_version_note"):
            print(f"  note: {pr.get('policy_version_note')}")
            
        print(f"  explanation: {pr.get('explanation')}")

    print("\n✅ policy_tool_worker test done.")