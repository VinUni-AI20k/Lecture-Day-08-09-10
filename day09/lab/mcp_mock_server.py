"""
mcp_mock_server.py — Mock MCP Server (kept separate from real MCP server)

This module is intentionally lightweight and in-process.
Use this only for local fallback/testing.
Primary MCP server should be mcp_server.py (real HTTP + safeguards).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

TOOL_SCHEMAS = {
    "search_kb": {
        "name": "search_kb",
        "description": "Mock search tool for KB",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 3},
            },
            "required": ["query"],
        },
    },
    "get_ticket_info": {
        "name": "get_ticket_info",
        "description": "Mock ticket lookup",
        "inputSchema": {
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}},
            "required": ["ticket_id"],
        },
    },
    "check_access_permission": {
        "name": "check_access_permission",
        "description": "Mock access policy check",
        "inputSchema": {
            "type": "object",
            "properties": {
                "access_level": {"type": "integer"},
                "requester_role": {"type": "string"},
                "is_emergency": {"type": "boolean", "default": False},
            },
            "required": ["access_level", "requester_role"],
        },
    },
    "create_ticket": {
        "name": "create_ticket",
        "description": "Mock ticket create",
        "inputSchema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["priority", "title"],
        },
    },
}


MOCK_TICKETS = {
    "P1-LATEST": {
        "ticket_id": "IT-9847",
        "priority": "P1",
        "status": "in_progress",
        "assignee": "oncall.engineer@company.internal",
        "created_at": "2026-04-13T22:47:00",
        "sla_deadline": "2026-04-14T02:47:00",
        "notifications_sent": ["slack:#incident-p1", "pagerduty:oncall"],
    }
}

ACCESS_RULES = {
    1: {"required_approvers": ["Line Manager"], "emergency_can_bypass": False},
    2: {"required_approvers": ["Line Manager", "IT Admin"], "emergency_can_bypass": True},
    3: {"required_approvers": ["Line Manager", "IT Admin", "IT Security"], "emergency_can_bypass": False},
}


def tool_search_kb(query: str, top_k: int = 3) -> dict:
    try:
        from workers.retrieval import retrieve_dense

        chunks = retrieve_dense(query, top_k=top_k)
        sources = list(dict.fromkeys(c.get("source", "unknown") for c in chunks))
        return {"chunks": chunks, "sources": sources, "total_found": len(chunks)}
    except Exception as exc:
        return {
            "chunks": [{"text": f"[MOCK] search failed: {exc}", "source": "mock_data", "score": 0.5}],
            "sources": ["mock_data"],
            "total_found": 1,
        }


def tool_get_ticket_info(ticket_id: str) -> dict:
    return MOCK_TICKETS.get(ticket_id.upper(), {"error": f"Ticket '{ticket_id}' không tồn tại"})


def tool_check_access_permission(access_level: int, requester_role: str, is_emergency: bool = False) -> dict:
    rule = ACCESS_RULES.get(access_level)
    if not rule:
        return {"error": f"Access level {access_level} không hợp lệ"}
    return {
        "access_level": access_level,
        "can_grant": True,
        "required_approvers": rule["required_approvers"],
        "emergency_override": bool(is_emergency and rule.get("emergency_can_bypass", False)),
        "notes": ["mock_policy_check"],
        "source": "access_control_sop.txt",
    }


def tool_create_ticket(priority: str, title: str, description: str = "") -> dict:
    mock_id = f"MOCK-{abs(hash((priority, title))) % 10000:04d}"
    return {
        "ticket_id": mock_id,
        "priority": priority,
        "title": title,
        "description": description[:200],
        "created_at": datetime.now().isoformat(),
        "url": f"https://mock.local/tickets/{mock_id}",
    }


TOOL_REGISTRY = {
    "search_kb": tool_search_kb,
    "get_ticket_info": tool_get_ticket_info,
    "check_access_permission": tool_check_access_permission,
    "create_ticket": tool_create_ticket,
}


def list_tools() -> list:
    return list(TOOL_SCHEMAS.values())


def dispatch_tool(tool_name: str, tool_input: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict:
    if tool_name not in TOOL_REGISTRY:
        return {"error": {"code": "MCP_UNKNOWN_TOOL", "message": f"Tool '{tool_name}' không tồn tại"}}
    try:
        return TOOL_REGISTRY[tool_name](**(tool_input or {}))
    except TypeError as exc:
        return {"error": {"code": "MCP_INVALID_INPUT", "message": str(exc)}}
    except Exception as exc:
        return {"error": {"code": "MCP_EXECUTION_FAILED", "message": str(exc)}}


if __name__ == "__main__":
    print("📋 Mock MCP tools:")
    for t in list_tools():
        print(f" - {t['name']}")
    print("\n🔍 Demo:")
    print(dispatch_tool("search_kb", {"query": "SLA P1", "top_k": 2}))
