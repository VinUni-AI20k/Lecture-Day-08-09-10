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

import re
from datetime import date

POLICY_SOURCE_FILE = "policy_refund_v4.txt"
POLICY_V4_EFFECTIVE_DATE = date(2026, 2, 1)
DATE_DMY_REGEX = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")

FLASH_SALE_KEYWORDS = (
    "flash sale",
    "flashsale",
    "khuyến mãi flash sale",
    "khuyen mai flash sale",
)
FLASH_SALE_HINT_KEYWORDS = (
    "mã giảm giá đặc biệt",
    "ma giam gia dac biet",
)
DIGITAL_PRODUCT_KEYWORDS = ("license key", "license", "subscription", "kỹ thuật số")
ACTIVATED_PRODUCT_KEYWORDS = ("đã kích hoạt", "đã đăng ký", "đã sử dụng")
DIGITAL_PRODUCT_HINT_KEYWORDS = (
    "hàng kỹ thuật số",
    "hang ky thuat so",
    "sản phẩm kỹ thuật số",
    "san pham ky thuat so",
    "digital product",
)
ACTIVATED_PRODUCT_HINT_KEYWORDS = (
    "đã được kích hoạt",
    "da duoc kich hoat",
    "đăng ký tài khoản",
    "dang ky tai khoan",
)
TEMPORAL_V3_HINT_KEYWORDS = (
    "trước 01/02",
    "truoc 01/02",
    "trước ngày 01/02/2026",
    "truoc ngay 01/02/2026",
    "áp dụng chính sách v3",
    "ap dung chinh sach v3",
)
TICKET_LOOKUP_KEYWORDS = ("ticket", "p1", "jira")

WORKER_NAME = "policy_tool_worker"


def _normalize(text: str) -> str:
    """Normalize input text for simple keyword checks."""
    if not isinstance(text, str):
        return ""
    return text.lower()


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    """Return True when text contains at least one keyword."""
    return any(kw in text for kw in keywords)


def _join_chunk_text(chunks: list) -> str:
    """Flatten retrieved chunk texts to one normalized string."""
    raw = " ".join(c.get("text", "") for c in chunks if isinstance(c, dict))
    return _normalize(raw)


def _collect_sources(chunks: list) -> list:
    """Collect unique sources from chunks while keeping output stable."""
    unique_sources = []
    seen = set()
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        source = chunk.get("source", "unknown")
        if source not in seen:
            seen.add(source)
            unique_sources.append(source)
    return unique_sources


def _make_exception(exception_type: str, rule: str) -> dict:
    """Standardize exception object format."""
    return {
        "type": exception_type,
        "rule": rule,
        "source": POLICY_SOURCE_FILE,
    }


def _is_flash_sale_case(task_text: str, context_text: str) -> bool:
    """Detect Flash Sale exception using direct mention or policy hint phrases."""
    if _contains_any(task_text, FLASH_SALE_KEYWORDS) or _contains_any(context_text, FLASH_SALE_KEYWORDS):
        return True

    task_has_flash_sale_hint = _contains_any(task_text, FLASH_SALE_HINT_KEYWORDS)
    context_confirms_flash_sale = _contains_any(context_text, FLASH_SALE_KEYWORDS)
    return task_has_flash_sale_hint and context_confirms_flash_sale


def _is_digital_product_case(task_text: str, context_text: str) -> bool:
    """Detect digital-product exception from task or retrieved context."""
    if _contains_any(task_text, DIGITAL_PRODUCT_KEYWORDS) or _contains_any(context_text, DIGITAL_PRODUCT_KEYWORDS):
        return True

    task_has_digital_hint = _contains_any(task_text, DIGITAL_PRODUCT_HINT_KEYWORDS)
    context_confirms_digital = _contains_any(context_text, DIGITAL_PRODUCT_KEYWORDS)
    return task_has_digital_hint and context_confirms_digital


def _is_activated_product_case(task_text: str, context_text: str) -> bool:
    """Detect activated-account/product exception from task or context."""
    if _contains_any(task_text, ACTIVATED_PRODUCT_KEYWORDS) or _contains_any(context_text, ACTIVATED_PRODUCT_KEYWORDS):
        return True

    task_has_activated_hint = _contains_any(task_text, ACTIVATED_PRODUCT_HINT_KEYWORDS)
    context_confirms_activated = _contains_any(context_text, ACTIVATED_PRODUCT_KEYWORDS)
    return task_has_activated_hint and context_confirms_activated


def _extract_dates(text: str) -> list[date]:
    """Extract dd/mm/yyyy dates from text and convert to date objects."""
    parsed_dates = []
    for day_str, month_str, year_str in DATE_DMY_REGEX.findall(text):
        try:
            parsed_dates.append(date(int(year_str), int(month_str), int(day_str)))
        except ValueError:
            continue
    return parsed_dates


def _resolve_policy_version(task_text: str, context_text: str) -> tuple[str, str]:
    """Resolve refund policy version based on effective date and temporal hints."""
    all_dates = _extract_dates(task_text) + _extract_dates(context_text)
    pre_v4_dates = sorted(d for d in all_dates if d < POLICY_V4_EFFECTIVE_DATE)
    has_v3_hint = _contains_any(task_text, TEMPORAL_V3_HINT_KEYWORDS) or _contains_any(context_text, TEMPORAL_V3_HINT_KEYWORDS)

    if pre_v4_dates or has_v3_hint:
        evidence_date = pre_v4_dates[0].strftime("%d/%m/%Y") if pre_v4_dates else "(không rõ ngày cụ thể)"
        note = (
            f"Phát hiện mốc thời gian trước 01/02/2026 ({evidence_date}) nên áp dụng chính sách v3; "
            "tài liệu hiện tại chỉ có policy v4, cần xác nhận thêm với CS Team."
        )
        return "refund_policy_v3", note

    return "refund_policy_v4", ""


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
    task_lower = _normalize(task)
    context_text = _join_chunk_text(chunks)

    # --- Rule-based exception detection ---
    exceptions_found = []

    # Exception 1: Flash Sale
    if _is_flash_sale_case(task_lower, context_text):
        exceptions_found.append(
            _make_exception(
                "flash_sale_exception",
                "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
            )
        )

    # Exception 2: Digital product
    if _is_digital_product_case(task_lower, context_text):
        exceptions_found.append(
            _make_exception(
                "digital_product_exception",
                "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền (Điều 3).",
            )
        )

    # Exception 3: Activated product
    if _is_activated_product_case(task_lower, context_text):
        exceptions_found.append(
            _make_exception(
                "activated_exception",
                "Sản phẩm đã kích hoạt hoặc đăng ký tài khoản không được hoàn tiền (Điều 3).",
            )
        )

    # Determine which policy version applies (temporal scoping)
    policy_name, policy_version_note = _resolve_policy_version(task_lower, context_text)

    # Determine policy_applies
    policy_applies = len(exceptions_found) == 0
    if policy_name == "refund_policy_v3" and policy_version_note:
        # v3 policy content is unavailable in current docs, so require human confirmation.
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

    sources = _collect_sources(chunks)

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
    task_lower = _normalize(task)
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
        if needs_tool and _contains_any(task_lower, TICKET_LOOKUP_KEYWORDS):
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
            "task": "Đơn này dùng mã giảm giá đặc biệt, có hoàn tiền được không?",
            "retrieved_chunks": [
                {"text": "Đơn hàng đã áp dụng mã giảm giá đặc biệt theo chương trình khuyến mãi Flash Sale.", "source": "policy_refund_v4.txt", "score": 0.9}
            ],
        },
        {
            "task": "Khách hàng muốn hoàn tiền license key đã kích hoạt.",
            "retrieved_chunks": [
                {"text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.88}
            ],
        },
        {
            "task": "Đơn này có hoàn tiền được không?",
            "retrieved_chunks": [
                {"text": "Sản phẩm thuộc danh mục hàng kỹ thuật số (license key, subscription).", "source": "policy_refund_v4.txt", "score": 0.87}
            ],
        },
        {
            "task": "Khách này xin hoàn tiền dù đã đăng ký tài khoản rồi.",
            "retrieved_chunks": [
                {"text": "Sản phẩm đã được kích hoạt hoặc đăng ký tài khoản thì không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.86}
            ],
        },
        {
            "task": "Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạt.",
            "retrieved_chunks": [
                {"text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất, chưa dùng.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
        },
        {
            "task": "Khách hàng đặt đơn ngày 31/01/2026 và yêu cầu hoàn tiền ngày 07/02/2026. Được hoàn tiền không?",
            "retrieved_chunks": [
                {"text": "Chính sách có hiệu lực từ 01/02/2026. Đơn trước ngày hiệu lực áp dụng policy v3.", "source": "policy_refund_v4.txt", "score": 0.84}
            ],
        },
    ]

    for tc in test_cases:
        print(f"\n▶ Task: {tc['task'][:70]}...")
        result = run(tc.copy())
        pr = result.get("policy_result", {})
        print(f"  policy_applies: {pr.get('policy_applies')}")
        print(f"  policy_name: {pr.get('policy_name')}")
        if pr.get("exceptions_found"):
            for ex in pr["exceptions_found"]:
                print(f"  exception: {ex['type']} — {ex['rule'][:60]}...")
        if pr.get("policy_version_note"):
            print(f"  temporal_note: {pr['policy_version_note'][:90]}...")
        print(f"  MCP calls: {len(result.get('mcp_tools_used', []))}")

    print("\n✅ policy_tool_worker test done.")
