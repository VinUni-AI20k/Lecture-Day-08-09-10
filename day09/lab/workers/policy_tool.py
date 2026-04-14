import os
import sys
from typing import Optional

WORKER_NAME = "policy_tool_worker"


# ─────────────────────────────────────────────
# MCP Client
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool (in-process mock hoặc HTTP sau này)
    """
    from datetime import datetime

    try:
        # fallback: local dispatch
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
# LLM Helper (NEW)
# ─────────────────────────────────────────────

def _llm_policy_analysis(task: str, chunks: list) -> dict:
    """
    Fallback LLM-based policy analysis (nâng cấp từ rule-based)
    """
    # Guard: không có API key → không call, fallback conservative (không override rule-based)
    if not os.getenv("OPENAI_API_KEY"):
        return {
            "policy_applies": None,
            "exceptions_found": [],
            "explanation": "LLM skipped: OPENAI_API_KEY not set",
        }

    try:
        from openai import OpenAI
        client = OpenAI()

        context = "\n".join([c.get("text", "") for c in chunks])

        prompt = f"""
Bạn là policy analyst.

Task: {task}

Context:
{context}

Trả về JSON đúng schema contract:
{{
  "policy_applies": true/false,
  "exceptions_found": [{{"type": "...", "rule": "...", "source": "..."}}],
  "explanation": "..."
}}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Return JSON only matching the requested schema."},
                {"role": "user", "content": prompt},
            ],
        )

        import json
        parsed = json.loads(response.choices[0].message.content)
        # Map fields về đúng contract nếu LLM trả lệch (reason → rule)
        normalized_exceptions = []
        for ex in parsed.get("exceptions_found", []) or []:
            normalized_exceptions.append({
                "type": ex.get("type", "llm_detected"),
                "rule": ex.get("rule") or ex.get("reason", ""),
                "source": ex.get("source", "llm"),
            })
        return {
            "policy_applies": parsed.get("policy_applies"),
            "exceptions_found": normalized_exceptions,
            "explanation": parsed.get("explanation", ""),
        }

    except Exception as e:
        # Conservative: không set policy_applies=True để tránh "allow" sai
        return {
            "policy_applies": None,
            "exceptions_found": [],
            "explanation": f"LLM fallback failed: {e}",
        }

# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────

def analyze_policy(task: str, chunks: list) -> dict:
    """
    Rule-based + LLM hybrid
    """
    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks]).lower()

    exceptions_found = []

    # ───────── RULE 1: Flash Sale ─────────
    if "flash sale" in task_lower or "flash sale" in context_text:
        exceptions_found.append({
            "type": "flash_sale_exception",
            "rule": "Flash Sale không được hoàn tiền",
            "source": "policy_refund_v4.txt",
        })

    # ───────── RULE 2: Digital product ─────────
    digital_keywords = ["license", "subscription", "key", "kỹ thuật số"]
    if any(kw in task_lower for kw in digital_keywords):
        exceptions_found.append({
            "type": "digital_product_exception",
            "rule": "Sản phẩm digital không được hoàn tiền",
            "source": "policy_refund_v4.txt",
        })

    # ───────── RULE 3: Activated ─────────
    activated_keywords = ["đã kích hoạt", "đã dùng", "đã sử dụng"]
    if any(kw in task_lower for kw in activated_keywords):
        exceptions_found.append({
            "type": "activated_exception",
            "rule": "Sản phẩm đã kích hoạt không được hoàn tiền",
            "source": "policy_refund_v4.txt",
        })

    # ───────── RULE 4: Valid refund case ─────────
    # Lỗi/hỏng + trong time window → refund explicitly valid (không exception)
    valid_refund_case = (
        any(kw in task_lower for kw in ["lỗi", "hỏng"]) and
        any(kw in task_lower for kw in ["5 ngày", "7 ngày", "trong 7"])
    )

    # ───────── POLICY APPLY ─────────
    policy_applies = len(exceptions_found) == 0

    # LLM chỉ gọi khi rule-based thực sự uncertain:
    # - không có chunks để evidence, hoặc
    # - không match rule nào VÀ không phải valid-case đã xác định
    rule_based_uncertain = not chunks or (not exceptions_found and not valid_refund_case)
    if rule_based_uncertain:
        llm_result = _llm_policy_analysis(task, chunks)
        # Chỉ override policy_applies khi LLM trả về quyết định rõ ràng (không None)
        if llm_result.get("policy_applies") is not None:
            policy_applies = llm_result["policy_applies"]
        if llm_result.get("exceptions_found"):
            exceptions_found.extend(llm_result["exceptions_found"])

    # ───────── VERSION CHECK ─────────
    policy_name = "refund_policy_v4"
    policy_version_note = ""

    if any(kw in task_lower for kw in ["trước 01/02", "30/01", "31/01"]):
        policy_name = "refund_policy_v3"
        policy_version_note = "Order trước 01/02/2026 → dùng policy v3"

    sources = list({c.get("source", "unknown") for c in chunks if c})

    return {
        "policy_applies": policy_applies,
        "policy_name": policy_name,
        "exceptions_found": exceptions_found,
        "source": sources,
        "policy_version_note": policy_version_note,
        "explanation": "Hybrid rule-based + LLM analysis",
    }


# ─────────────────────────────────────────────
# Worker Entry Point
# ─────────────────────────────────────────────

def run(state: dict) -> dict:

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
        # ───────── STEP 1: KB SEARCH ─────────
        if not chunks and needs_tool:
            mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called search_kb")

            if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                chunks = mcp_result["output"]["chunks"]
                state["retrieved_chunks"] = chunks

        # ───────── STEP 2: POLICY ─────────
        policy_result = analyze_policy(task, chunks)
        state["policy_result"] = policy_result

        # ───────── STEP 3: EXTRA TOOL ─────────
        if needs_tool and any(kw in task.lower() for kw in ["ticket", "jira", "p1"]):
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called get_ticket_info")

        # ───────── LOG ─────────
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
