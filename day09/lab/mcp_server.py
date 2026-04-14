"""
mcp_server.py — Mock MCP Server
Sprint 3: Implement ít nhất 2 MCP tools.

Mô phỏng MCP (Model Context Protocol) interface trong Python.
Agent (MCP client) gọi dispatch_tool() thay vì hard-code từng API.

Tools available:
    1. search_kb(query, top_k)           → tìm kiếm Knowledge Base
    2. get_ticket_info(ticket_id)        → tra cứu thông tin ticket (mock data)
    3. check_access_permission(level, requester_role)  → kiểm tra quyền truy cập
    4. create_ticket(priority, title, description)     → tạo ticket mới (mock)

Sử dụng:
    from mcp_server import dispatch_tool, list_tools

    # Discover available tools
    tools = list_tools()

    # Call a tool
    result = dispatch_tool("search_kb", {"query": "SLA P1", "top_k": 3})

Sprint 3 TODO:
    - Option Standard: Sử dụng file này as-is (mock class)
    - Option Advanced: Implement HTTP server với FastAPI hoặc dùng `mcp` library

Chạy thử:
    python mcp_server.py
"""

import copy
from datetime import datetime
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────
# Tool Definitions (Schema Discovery)
# Giống với cách MCP server expose tool list cho client
# ─────────────────────────────────────────────

TOOL_SCHEMAS = {
    "search_kb": {
        "name": "search_kb",
        "description": "Tìm kiếm Knowledge Base nội bộ bằng semantic search. Trả về top-k chunks liên quan nhất.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Câu hỏi hoặc keyword cần tìm"},
                "top_k": {"type": "integer", "description": "Số chunks cần trả về", "default": 3},
            },
            "required": ["query"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "chunks": {"type": "array"},
                "sources": {"type": "array"},
                "total_found": {"type": "integer"},
            },
        },
    },
    "get_ticket_info": {
        "name": "get_ticket_info",
        "description": "Tra cứu thông tin ticket từ hệ thống Jira nội bộ.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "ID ticket (VD: IT-1234, P1-LATEST)"},
            },
            "required": ["ticket_id"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "priority": {"type": "string"},
                "status": {"type": "string"},
                "assignee": {"type": "string"},
                "created_at": {"type": "string"},
                "sla_deadline": {"type": "string"},
            },
        },
    },
    "check_access_permission": {
        "name": "check_access_permission",
        "description": "Kiểm tra điều kiện cấp quyền truy cập theo Access Control SOP.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "access_level": {"type": "integer", "description": "Level cần cấp (1, 2, hoặc 3)"},
                "requester_role": {"type": "string", "description": "Vai trò của người yêu cầu"},
                "is_emergency": {"type": "boolean", "description": "Có phải khẩn cấp không", "default": False},
            },
            "required": ["access_level", "requester_role"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "can_grant": {"type": "boolean"},
                "required_approvers": {"type": "array"},
                "emergency_override": {"type": "boolean"},
                "source": {"type": "string"},
            },
        },
    },
    "create_ticket": {
        "name": "create_ticket",
        "description": "Tạo ticket mới trong hệ thống Jira (MOCK — không tạo thật trong lab).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["priority", "title"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "url": {"type": "string"},
                "created_at": {"type": "string"},
            },
        },
    },
}


def _matches_schema_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    return True


def _validate_tool_input(tool_name: str, tool_input: dict) -> Optional[dict]:
    schema = TOOL_SCHEMAS[tool_name].get("inputSchema", {})

    if not isinstance(tool_input, dict):
        return {
            "error": f"Invalid input for tool '{tool_name}': input must be an object/dict.",
            "schema": schema,
        }

    required_fields = schema.get("required", [])
    missing_fields = [field for field in required_fields if field not in tool_input]

    properties = schema.get("properties", {})
    type_errors = []
    enum_errors = []

    for key, value in tool_input.items():
        prop_schema = properties.get(key)
        if not prop_schema:
            continue

        expected_type = prop_schema.get("type")
        if expected_type and not _matches_schema_type(value, expected_type):
            type_errors.append(
                f"field '{key}' expected '{expected_type}' but got '{type(value).__name__}'"
            )
            continue

        enum_values = prop_schema.get("enum")
        if enum_values and value not in enum_values:
            enum_errors.append(
                f"field '{key}' must be one of {enum_values}, got '{value}'"
            )

    if missing_fields or type_errors or enum_errors:
        return {
            "error": f"Invalid input for tool '{tool_name}'.",
            "missing_required": missing_fields,
            "type_errors": type_errors,
            "enum_errors": enum_errors,
            "schema": schema,
        }

    return None


# ─────────────────────────────────────────────
# Tool Implementations
# ─────────────────────────────────────────────

def tool_search_kb(query: str, top_k: int = 3) -> dict:
    """
    Tìm kiếm Knowledge Base bằng semantic search.

    TODO Sprint 3: Kết nối với ChromaDB thực.
    Hiện tại: Delegate sang retrieval worker.
    """
    query = (query or "").strip()
    if not query:
        return {
            "chunks": [],
            "sources": [],
            "total_found": 0,
            "error": "query must not be empty",
        }

    try:
        top_k = max(1, int(top_k))
    except (TypeError, ValueError):
        top_k = 3

    try:
        # Tái dùng retrieval logic từ workers/retrieval.py
        from workers.retrieval import retrieve_dense

        chunks = retrieve_dense(query, top_k=top_k)
        sources = sorted({c.get("source", "unknown") for c in chunks})
        return {
            "chunks": chunks,
            "sources": sources,
            "total_found": len(chunks),
        }
    except Exception as e:
        return {
            "chunks": [],
            "sources": [],
            "total_found": 0,
            "error": f"search_kb failed: {e}",
        }


# Mock ticket database
MOCK_TICKETS = {
    "P1-LATEST": {
        "ticket_id": "IT-9847",
        "priority": "P1",
        "title": "API Gateway down — toàn bộ người dùng không đăng nhập được",
        "status": "in_progress",
        "assignee": "nguyen.van.a@company.internal",
        "created_at": "2026-04-13T22:47:00",
        "sla_deadline": "2026-04-14T02:47:00",
        "escalated": True,
        "escalated_to": "senior_engineer_team",
        "notifications_sent": ["slack:#incident-p1", "email:incident@company.internal", "pagerduty:oncall"],
    },
    "IT-1234": {
        "ticket_id": "IT-1234",
        "priority": "P2",
        "title": "Feature login chậm cho một số user",
        "status": "open",
        "assignee": None,
        "created_at": "2026-04-13T09:15:00",
        "sla_deadline": "2026-04-14T09:15:00",
        "escalated": False,
    },
}


def tool_get_ticket_info(ticket_id: str) -> dict:
    """
    Tra cứu thông tin ticket (mock data).
    """
    ticket_key = str(ticket_id or "").strip().upper()
    if not ticket_key:
        return {
            "error": "ticket_id is required.",
            "available_mock_ids": list(MOCK_TICKETS.keys()),
        }

    ticket = MOCK_TICKETS.get(ticket_key)
    if ticket:
        return dict(ticket)
    # Không tìm thấy
    return {
        "error": f"Ticket '{ticket_id}' không tìm thấy trong hệ thống.",
        "available_mock_ids": list(MOCK_TICKETS.keys()),
    }


# Mock access control rules
ACCESS_RULES = {
    1: {
        "required_approvers": ["Line Manager"],
        "emergency_can_bypass": False,
        "note": "Standard user access",
    },
    2: {
        "required_approvers": ["Line Manager", "IT Admin"],
        "emergency_can_bypass": True,
        "emergency_bypass_note": "Level 2 có thể cấp tạm thời với approval đồng thời của Line Manager và IT Admin on-call.",
        "note": "Elevated access",
    },
    3: {
        "required_approvers": ["Line Manager", "IT Admin", "IT Security"],
        "emergency_can_bypass": False,
        "note": "Admin access — không có emergency bypass",
    },
}


def tool_check_access_permission(access_level: int, requester_role: str, is_emergency: bool = False) -> dict:
    """
    Kiểm tra điều kiện cấp quyền theo Access Control SOP.
    """
    try:
        access_level = int(access_level)
    except (TypeError, ValueError):
        return {"error": "access_level phải là số nguyên 1, 2, hoặc 3."}

    requester_role = str(requester_role or "").strip().lower()
    if not requester_role:
        return {"error": "requester_role là bắt buộc."}

    rule = ACCESS_RULES.get(access_level)
    if not rule:
        return {"error": f"Access level {access_level} không hợp lệ. Levels: 1, 2, 3."}

    can_grant = True
    notes = []

    if is_emergency and rule.get("emergency_can_bypass"):
        notes.append(rule.get("emergency_bypass_note", ""))
        can_grant = True
    elif is_emergency and not rule.get("emergency_can_bypass"):
        notes.append(f"Level {access_level} KHÔNG có emergency bypass. Phải follow quy trình chuẩn.")

    if requester_role == "contractor" and access_level == 3:
        can_grant = False
        notes.append("Contractor không được cấp trực tiếp Level 3; cần quy trình escalate qua nhân sự nội bộ.")

    return {
        "access_level": access_level,
        "requester_role": requester_role,
        "can_grant": can_grant,
        "required_approvers": rule["required_approvers"],
        "approver_count": len(rule["required_approvers"]),
        "emergency_override": is_emergency and rule.get("emergency_can_bypass", False),
        "notes": notes,
        "source": "access_control_sop.txt",
    }


def tool_create_ticket(priority: str, title: str, description: str = "") -> dict:
    """
    Tạo ticket mới (MOCK — in log, không tạo thật).
    """
    priority = str(priority or "").strip().upper()
    if priority not in {"P1", "P2", "P3", "P4"}:
        return {"error": "priority phải là một trong: P1, P2, P3, P4."}

    title = str(title or "").strip()
    if not title:
        return {"error": "title là bắt buộc để tạo ticket."}

    description = str(description or "")
    mock_id = f"IT-{9900 + (abs(hash(f'{priority}:{title}')) % 99)}"
    ticket = {
        "ticket_id": mock_id,
        "priority": priority,
        "title": title,
        "description": description[:200],
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "url": f"https://jira.company.internal/browse/{mock_id}",
        "note": "MOCK ticket — không tồn tại trong hệ thống thật",
    }
    print(f"  [MCP create_ticket] MOCK: {mock_id} | {priority} | {title[:50]}")
    return ticket


# ─────────────────────────────────────────────
# Dispatch Layer — MCP server interface
# ─────────────────────────────────────────────

TOOL_REGISTRY = {
    "search_kb": tool_search_kb,
    "get_ticket_info": tool_get_ticket_info,
    "check_access_permission": tool_check_access_permission,
    "create_ticket": tool_create_ticket,
}


def list_tools() -> list:
    """
    MCP discovery: trả về danh sách tools có sẵn.
    Tương đương với `tools/list` trong MCP protocol.
    """
    return [copy.deepcopy(schema) for schema in TOOL_SCHEMAS.values()]


def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    """
    MCP execution: nhận tool_name và input, gọi tool tương ứng.
    Tương đương với `tools/call` trong MCP protocol.

    Args:
        tool_name: tên tool (phải có trong TOOL_REGISTRY)
        tool_input: input dict (phải match với tool's inputSchema)

    Returns:
        Tool output dict, hoặc error dict nếu thất bại
    """
    tool_name = str(tool_name or "").strip()
    if tool_name not in TOOL_REGISTRY:
        return {
            "error": f"Tool '{tool_name}' không tồn tại. Available: {list(TOOL_REGISTRY.keys())}"
        }

    if tool_input is None:
        tool_input = {}

    validation_error = _validate_tool_input(tool_name, tool_input)
    if validation_error:
        return validation_error

    tool_fn = TOOL_REGISTRY[tool_name]
    try:
        result = tool_fn(**tool_input)
        if isinstance(result, dict):
            return result

        return {
            "error": f"Tool '{tool_name}' returned invalid output type '{type(result).__name__}'.",
        }
    except TypeError as e:
        return {
            "error": f"Invalid input for tool '{tool_name}': {e}",
            "schema": TOOL_SCHEMAS[tool_name]["inputSchema"],
        }
    except Exception as e:
        return {
            "error": f"Tool '{tool_name}' execution failed: {e}",
            "exception_type": type(e).__name__,
        }


# ─────────────────────────────────────────────
# Test & Demo
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MCP Server — Tool Discovery & Test")
    print("=" * 60)

    # 1. Discover tools
    print("\n📋 Available Tools:")
    for tool in list_tools():
        print(f"  • {tool['name']}: {tool['description'][:60]}...")

    # 2. Test search_kb
    print("\n🔍 Test: search_kb")
    result = dispatch_tool("search_kb", {"query": "SLA P1 resolution time", "top_k": 2})
    if result.get("chunks"):
        for c in result["chunks"]:
            print(f"  [{c.get('score', '?')}] {c.get('source')}: {c.get('text', '')[:70]}...")
    else:
        print(f"  Result: {result}")

    # 3. Test get_ticket_info
    print("\n🎫 Test: get_ticket_info")
    ticket = dispatch_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
    print(f"  Ticket: {ticket.get('ticket_id')} | {ticket.get('priority')} | {ticket.get('status')}")
    if ticket.get("notifications_sent"):
        print(f"  Notifications: {ticket['notifications_sent']}")

    # 4. Test check_access_permission
    print("\n🔐 Test: check_access_permission (Level 3, emergency)")
    perm = dispatch_tool("check_access_permission", {
        "access_level": 3,
        "requester_role": "contractor",
        "is_emergency": True,
    })
    print(f"  can_grant: {perm.get('can_grant')}")
    print(f"  required_approvers: {perm.get('required_approvers')}")
    print(f"  emergency_override: {perm.get('emergency_override')}")
    print(f"  notes: {perm.get('notes')}")

    # 5. Test invalid tool
    print("\n❌ Test: invalid tool")
    err = dispatch_tool("nonexistent_tool", {})
    print(f"  Error: {err.get('error')}")

    print("\n✅ MCP server test done.")
    print("\nTODO Sprint 3: Implement HTTP server nếu muốn bonus +2.")
