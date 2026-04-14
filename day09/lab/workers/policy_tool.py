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
import re
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

WORKER_NAME = "policy_tool_worker"


# ─────────────────────────────────────────────
# LLM Helper
# ─────────────────────────────────────────────

def _call_llm(messages: list) -> str:
    """
    Gọi LLM để phân tích policy.
    Ưu tiên OpenAI, fallback sang Gemini.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                messages=messages,
                temperature=0,
                max_tokens=600,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            print(f"[policy_tool] OpenAI error: {e}")

    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            model = genai.GenerativeModel(model_name)
            combined = "\n".join([m["content"] for m in messages])
            response = model.generate_content(combined)
            return (response.text or "").strip()
        except Exception as e:
            print(f"[policy_tool] Gemini error: {e}")

    return ""


# ─────────────────────────────────────────────
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
# Temporal Scoping Helpers
# ─────────────────────────────────────────────

def _extract_date_from_task(task: str) -> Optional[str]:
    """
    Trích xuất ngày tháng từ task string.
    Hỗ trợ các format: DD/MM/YYYY, DD/MM, YYYY-MM-DD
    """
    patterns = [
        r"(\d{2}/\d{2}/\d{4})",   # 07/02/2026
        r"(\d{2}/\d{2})",           # 07/02
        r"(\d{4}-\d{2}-\d{2})",    # 2026-02-07
    ]
    for p in patterns:
        m = re.search(p, task)
        if m:
            return m.group(1)
    return None


def _is_before_policy_v4(date_str: Optional[str]) -> bool:
    """
    Trả về True nếu ngày trong task là trước 01/02/2026
    (mốc áp dụng policy v4). Các đơn cũ hơn thuộc policy v3.
    """
    if not date_str:
        return False
    try:
        from datetime import datetime
        for fmt in ("%d/%m/%Y", "%d/%m", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(date_str, fmt)
                # Nếu chỉ có ngày/tháng, giả sử năm 2026
                if fmt == "%d/%m":
                    dt = dt.replace(year=2026)
                cutoff = datetime(2026, 2, 1)
                return dt < cutoff
            except ValueError:
                continue
    except Exception:
        pass
    return False


# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────

def _llm_analyze_policy(task: str, chunks: list) -> dict:
    """
    Sprint 2: Dùng LLM phân tích policy sâu hơn rule-based.
    Trả về dict exceptions bổ sung hoặc empty dict nếu LLM không phát hiện thêm.
    """
    if not chunks:
        return {"llm_exceptions": [], "llm_note": "No context for LLM analysis."}

    context_str = "\n".join([
        f"[{i+1}] {c.get('source', 'unknown')}: {c.get('text', '')[:400]}"
        for i, c in enumerate(chunks[:5])
    ])

    system_prompt = """Bạn là Policy Analyst nội bộ. Nhiệm vụ: phân tích câu hỏi và context để xác định
các policy exception áp dụng. Trả lời CHÍNH XÁC dưới dạng JSON, không giải thích thêm.

JSON format:
{
  "policy_applies": true/false,
  "exceptions": [
    {"type": "tên_exception", "rule": "quy tắc áp dụng", "source": "tên file"}
  ],
  "policy_name": "tên_policy",
  "reasoning": "giải thích ngắn gọn"
}

Các exceptions có thể có:
- flash_sale_exception: đơn hàng Flash Sale không được hoàn tiền
- digital_product_exception: license key/subscription/download không được hoàn tiền
- activated_exception: sản phẩm đã kích hoạt/đăng ký không được hoàn tiền
- time_window_exception: yêu cầu ngoài cửa sổ thời gian cho phép
- manufacturer_defect_allowed: lỗi nhà sản xuất → có thể hoàn tiền ngay cả Flash Sale"""

    user_msg = f"""Câu hỏi/task: {task}

Context từ Knowledge Base:
{context_str}

Hãy phân tích và trả về JSON."""

    raw = _call_llm([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ])

    if not raw:
        return {"llm_exceptions": [], "llm_note": "LLM unavailable, using rule-based only."}

    # Parse JSON từ LLM output
    try:
        # Tìm JSON block nếu LLM wrap bằng ```json ... ```
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
        if json_match:
            raw = json_match.group(1)
        parsed = json.loads(raw)
        return {
            "llm_policy_applies": parsed.get("policy_applies", True),
            "llm_exceptions": parsed.get("exceptions", []),
            "llm_policy_name": parsed.get("policy_name", "unknown"),
            "llm_reasoning": parsed.get("reasoning", ""),
            "llm_note": "LLM analysis completed.",
        }
    except (json.JSONDecodeError, Exception) as e:
        return {
            "llm_exceptions": [],
            "llm_note": f"LLM JSON parse failed: {e}. Raw: {raw[:100]}",
        }


def analyze_policy(task: str, chunks: list) -> dict:
    """
    Phân tích policy dựa trên context chunks.
    Kết hợp 2 lớp:
      1. Rule-based: nhanh, ổn định, xử lý các exception rõ ràng
      2. LLM-based: phân tích sâu hơn, bắt các edge cases phức tạp

    Exceptions được xử lý:
    - Flash Sale → không được hoàn tiền (trừ lỗi nhà sản xuất)
    - Digital product / license key / subscription → không được hoàn tiền
    - Sản phẩm đã kích hoạt → không được hoàn tiền
    - Đơn hàng trước 01/02/2026 → áp dụng policy v3 (không có trong docs)

    Returns:
        dict with: policy_applies, policy_name, exceptions_found, source, rule, explanation
    """
    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks]).lower()

    # ── Layer 1: Rule-based exception detection ──────────────────────────
    exceptions_found = []

    # Exception 1: Flash Sale
    if "flash sale" in task_lower or "flash sale" in context_text:
        # Kiểm tra nếu đồng thời là lỗi nhà sản xuất
        is_manufacturer_defect = any(kw in task_lower for kw in [
            "lỗi nhà sản xuất", "lỗi sản xuất", "manufacturer", "defect"
        ])
        if is_manufacturer_defect:
            exceptions_found.append({
                "type": "flash_sale_manufacturer_defect",
                "rule": "Flash Sale + lỗi nhà sản xuất trong 7 ngày → CÓ THỂ được hoàn tiền (cần xét thêm).",
                "source": "policy_refund_v4.txt",
            })
        else:
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

    # Exception 3: Activated / already-used product
    if any(kw in task_lower for kw in ["đã kích hoạt", "đã đăng ký", "đã sử dụng", "đã dùng"]):
        exceptions_found.append({
            "type": "activated_exception",
            "rule": "Sản phẩm đã kích hoạt hoặc đăng ký tài khoản không được hoàn tiền (Điều 3).",
            "source": "policy_refund_v4.txt",
        })

    # ── Temporal Scoping ──────────────────────────────────────────────────
    # Sprint 2: Xác định đơn hàng trước 01/02/2026 → policy v3 áp dụng
    policy_name = "refund_policy_v4"
    policy_version_note = ""

    date_in_task = _extract_date_from_task(task)
    if _is_before_policy_v4(date_in_task):
        policy_name = "refund_policy_v3"
        policy_version_note = (
            f"Đơn hàng ngày {date_in_task} đặt trước 01/02/2026 → "
            "áp dụng chính sách hoàn tiền v3 (tài liệu v3 không có trong KB hiện tại). "
            "Cần liên hệ bộ phận CS để tra cứu policy v3."
        )
    elif any(kw in task_lower for kw in ["trước 01/02", "trước tháng 2", "tháng 1/2026"]):
        policy_version_note = (
            "Câu hỏi liên quan đến đơn hàng trước 01/02/2026. "
            "Policy v4 chỉ áp dụng từ 01/02/2026. "
            "Với đơn cũ hơn cần tra cứu policy v3."
        )

    # ── Layer 2: LLM-based deep analysis ──────────────────────────────────
    llm_result = _llm_analyze_policy(task, chunks)

    # Merge LLM exceptions vào rule-based (dedup theo type)
    existing_types = {ex["type"] for ex in exceptions_found}
    for llm_ex in llm_result.get("llm_exceptions", []):
        if llm_ex.get("type") not in existing_types:
            exceptions_found.append(llm_ex)
            existing_types.add(llm_ex.get("type", ""))

    # LLM có thể override policy_applies nếu phát hiện exception mới
    llm_policy_applies = llm_result.get("llm_policy_applies", True)
    rule_policy_applies = len(exceptions_found) == 0
    # Rule: cả hai phải đồng ý là applies → mới applies
    policy_applies = rule_policy_applies and llm_policy_applies

    sources = list({c.get("source", "unknown") for c in chunks if c})

    explanation = (
        f"Rule-based: {len(exceptions_found)} exceptions found. "
        f"LLM note: {llm_result.get('llm_note', 'n/a')}. "
        f"LLM reasoning: {llm_result.get('llm_reasoning', 'n/a')[:120]}"
    )

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
        # Step 1: Khi needs_tool=True, LUÔN gọi MCP search_kb (MCP là interface chính)
        if needs_tool:
            mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP search_kb")

            # Nếu chưa có chunks từ retrieval, dùng kết quả từ MCP
            if not chunks and mcp_result.get("output") and mcp_result["output"].get("chunks"):
                chunks = mcp_result["output"]["chunks"]
                state["retrieved_chunks"] = chunks

        # Step 2: Phân tích policy
        policy_result = analyze_policy(task, chunks)
        state["policy_result"] = policy_result

        # Step 3: Gọi check_access_permission nếu task liên quan đến access control
        task_lower = task.lower()
        if needs_tool and any(kw in task_lower for kw in ["access", "cấp quyền", "level 2", "level 3", "quyền"]):
            level = 3 if "level 3" in task_lower else 2
            is_emergency = any(kw in task_lower for kw in ["emergency", "khẩn cấp", "urgent"])
            requester = "contractor" if "contractor" in task_lower else "employee"
            mcp_result = _call_mcp_tool("check_access_permission", {
                "access_level": level,
                "requester_role": requester,
                "is_emergency": is_emergency,
            })
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP check_access_permission level={level}")

        # Step 4: Gọi get_ticket_info nếu task liên quan đến ticket/P1
        if needs_tool and any(kw in task_lower for kw in ["ticket", "p1", "jira"]):
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
    print("Policy Tool Worker - Standalone Test")
    print("=" * 50)

    test_cases = [
        {
            "task": "Khach hang Flash Sale yeu cau hoan tien vi san pham loi — duoc khong?",
            "retrieved_chunks": [
                {"text": "Ngoai le: Don hang Flash Sale khong duoc hoan tien.", "source": "policy_refund_v4.txt", "score": 0.9}
            ],
        },
        {
            "task": "Khach hang muon hoan tien license key da kich hoat.",
            "retrieved_chunks": [
                {"text": "San pham ky thuat so (license key, subscription) khong duoc hoan tien.", "source": "policy_refund_v4.txt", "score": 0.88}
            ],
        },
        {
            "task": "Don hang dat ngay 07/02/2026 co duoc hoan tien khong?",
            "retrieved_chunks": [
                {"text": "Chinh sach hoan tien v4 ap dung tu 01/02/2026.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
        },
        {
            "task": "Don hang dat ngay 31/01/2026 co duoc hoan tien khong?",
            "retrieved_chunks": [
                {"text": "Chinh sach hoan tien v4 ap dung tu 01/02/2026.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
        },
    ]

    for tc in test_cases:
        print(f"\n>> Task: {tc['task'][:70]}...")
        result = run(tc.copy())
        pr = result.get("policy_result", {})
        print(f"  policy_applies: {pr.get('policy_applies')}")
        print(f"  policy_name: {pr.get('policy_name')}")
        if pr.get("policy_version_note"):
            print(f"  version_note: {pr['policy_version_note'][:80]}...")
        if pr.get("exceptions_found"):
            for ex in pr["exceptions_found"]:
                print(f"  exception: {ex['type']} -- {ex['rule'][:60]}...")
        print(f"  MCP calls: {len(result.get('mcp_tools_used', []))}")

    print("\n[OK] policy_tool_worker test done.")
