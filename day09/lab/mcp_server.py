"""
mcp_server.py - Advanced Sprint 3 MCP server using the real `mcp` library.

The policy worker talks to this process through the MCP stdio transport instead
of importing Python helpers directly. Local helper functions are still kept for
debug/demo and to preserve the lab's current test workflow.
"""

import json
import os
import re
import sys
import unicodedata
from datetime import datetime

from mcp.server.fastmcp import FastMCP


TOOL_SCHEMAS = {
    "search_kb": {
        "name": "search_kb",
        "description": "Search the internal KB and return the most relevant chunks.",
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
        "description": "Look up ticket details from the internal ticket system mock.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
            },
            "required": ["ticket_id"],
        },
    },
    "check_access_permission": {
        "name": "check_access_permission",
        "description": "Check access approval and emergency override rules.",
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
        "description": "Create a mock ticket in the lab environment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
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
        "title": "API Gateway down - all users cannot sign in",
        "status": "in_progress",
        "assignee": "nguyen.van.a@company.internal",
        "created_at": "2026-04-13T22:47:00",
        "sla_deadline": "2026-04-14T02:47:00",
        "escalated": True,
        "escalated_to": "senior_engineer_team",
        "notifications_sent": [
            "slack:#incident-p1",
            "email:incident@company.internal",
            "pagerduty:oncall",
        ],
    },
    "IT-1234": {
        "ticket_id": "IT-1234",
        "priority": "P2",
        "title": "Login feature is slow for some users",
        "status": "open",
        "assignee": None,
        "created_at": "2026-04-13T09:15:00",
        "sla_deadline": "2026-04-14T09:15:00",
        "escalated": False,
    },
}


ACCESS_RULES = {
    1: {
        "required_approvers": ["Line Manager"],
        "emergency_can_bypass": False,
    },
    2: {
        "required_approvers": ["Line Manager", "IT Admin"],
        "emergency_can_bypass": True,
        "emergency_bypass_note": (
            "Level 2 can be granted temporarily with approval from the line manager and the on-call IT Admin."
        ),
    },
    3: {
        "required_approvers": ["Line Manager", "IT Admin", "IT Security"],
        "emergency_can_bypass": False,
    },
    4: {
        "required_approvers": ["IT Manager", "CISO"],
        "emergency_can_bypass": False,
    },
}


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.lower()


def _tokenize(text: str) -> list:
    return re.findall(r"[a-z0-9_]+", _normalize(text))


def tool_search_kb(query: str, top_k: int = 3) -> dict:
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "docs")
    query_tokens = set(_tokenize(query))
    chunks = []

    for fname in sorted(os.listdir(docs_dir)):
        file_path = os.path.join(docs_dir, fname)
        if not os.path.isfile(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as file_obj:
            content = file_obj.read()

        sections = [section.strip() for section in re.split(r"\n(?=== )", content.replace("\r\n", "\n")) if section.strip()]
        for section_index, section_text in enumerate(sections, start=1):
            section_tokens = set(_tokenize(section_text))
            overlap = len(query_tokens & section_tokens)
            if overlap == 0:
                continue

            score = overlap / max(len(query_tokens), 1)
            normalized_query = _normalize(query)
            normalized_section = _normalize(section_text)
            normalized_source = _normalize(fname)

            if "flash sale" in normalized_query and "flash sale" in normalized_section:
                score += 0.2
            if "p1" in normalized_query and "p1" in normalized_section:
                score += 0.15
            if "level 2" in normalized_query and "level 2" in normalized_section:
                score += 0.15
            if "level 3" in normalized_query and "level 3" in normalized_section:
                score += 0.15
            if "refund" in normalized_query and "refund" in normalized_source:
                score += 0.1
            if "access" in normalized_query and "access" in normalized_source:
                score += 0.1
            if "sla" in normalized_query and "sla" in normalized_source:
                score += 0.1

            chunks.append(
                {
                    "text": section_text,
                    "source": fname,
                    "score": round(min(1.0, score), 4),
                    "metadata": {
                        "source": fname,
                        "fallback": "mcp_local_lexical_search",
                        "section_index": section_index,
                    },
                }
            )

    chunks.sort(key=lambda item: item["score"], reverse=True)
    chunks = chunks[:top_k]
    sources = list({c.get("source", "unknown") for c in chunks})
    return {
        "chunks": chunks,
        "sources": sources,
        "total_found": len(chunks),
    }


def tool_get_ticket_info(ticket_id: str) -> dict:
    ticket = MOCK_TICKETS.get(ticket_id.upper())
    if ticket:
        return ticket
    return {
        "error": f"Ticket '{ticket_id}' was not found.",
        "available_mock_ids": list(MOCK_TICKETS.keys()),
    }


def tool_check_access_permission(access_level: int, requester_role: str, is_emergency: bool = False) -> dict:
    rule = ACCESS_RULES.get(access_level)
    if not rule:
        return {"error": f"Access level {access_level} is invalid. Allowed levels: 1, 2, 3, 4."}

    notes = []
    can_grant = True

    if is_emergency and rule.get("emergency_can_bypass"):
        notes.append(rule.get("emergency_bypass_note", "Emergency override permitted."))
    elif is_emergency and not rule.get("emergency_can_bypass"):
        notes.append(f"Level {access_level} does not support emergency bypass. Follow the standard approval chain.")

    if requester_role.lower() == "contractor" and access_level >= 3:
        notes.append("Contractor access at this level must remain temporary and auditable.")

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
    mock_id = f"IT-{9900 + hash(title) % 99}"
    return {
        "ticket_id": mock_id,
        "priority": priority,
        "title": title,
        "description": description[:200],
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "url": f"https://jira.company.internal/browse/{mock_id}",
        "note": "Mock ticket only - not persisted to a real backend.",
    }


TOOL_REGISTRY = {
    "search_kb": tool_search_kb,
    "get_ticket_info": tool_get_ticket_info,
    "check_access_permission": tool_check_access_permission,
    "create_ticket": tool_create_ticket,
}


def list_tools() -> list:
    return list(TOOL_SCHEMAS.values())


def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Tool '{tool_name}' does not exist. Available: {list(TOOL_REGISTRY.keys())}"}

    tool_fn = TOOL_REGISTRY[tool_name]
    try:
        return tool_fn(**tool_input)
    except TypeError as exc:
        return {
            "error": f"Invalid input for tool '{tool_name}': {exc}",
            "schema": TOOL_SCHEMAS[tool_name]["inputSchema"],
        }
    except Exception as exc:
        return {"error": f"Tool '{tool_name}' execution failed: {exc}"}


MCP_APP = FastMCP(
    name="day09-lab-mcp",
    instructions="Internal CS and IT helpdesk MCP server for the Day 09 lab.",
    debug=False,
    log_level="ERROR",
)


@MCP_APP.tool(name="search_kb", description=TOOL_SCHEMAS["search_kb"]["description"])
def mcp_search_kb(query: str, top_k: int = 3) -> str:
    return json.dumps(tool_search_kb(query=query, top_k=top_k), ensure_ascii=False)


@MCP_APP.tool(name="get_ticket_info", description=TOOL_SCHEMAS["get_ticket_info"]["description"])
def mcp_get_ticket_info(ticket_id: str) -> str:
    return json.dumps(tool_get_ticket_info(ticket_id=ticket_id), ensure_ascii=False)


@MCP_APP.tool(
    name="check_access_permission",
    description=TOOL_SCHEMAS["check_access_permission"]["description"],
)
def mcp_check_access_permission(access_level: int, requester_role: str, is_emergency: bool = False) -> str:
    return json.dumps(
        tool_check_access_permission(
            access_level=access_level,
            requester_role=requester_role,
            is_emergency=is_emergency,
        ),
        ensure_ascii=False,
    )


@MCP_APP.tool(name="create_ticket", description=TOOL_SCHEMAS["create_ticket"]["description"])
def mcp_create_ticket(priority: str, title: str, description: str = "") -> str:
    return json.dumps(tool_create_ticket(priority=priority, title=title, description=description), ensure_ascii=False)


def run_stdio_server() -> None:
    MCP_APP.run("stdio")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if "--stdio-server" in sys.argv:
        run_stdio_server()
        raise SystemExit(0)

    print("=" * 60)
    print("Day 09 Lab - MCP Server (Advanced / mcp library)")
    print("=" * 60)
    print("\nAvailable tools:")
    for tool in list_tools():
        print(f"  - {tool['name']}: {tool['description']}")

    print("\nLocal dispatch smoke test:")
    for tool_name, payload in [
        ("search_kb", {"query": "SLA P1 resolution time", "top_k": 2}),
        ("get_ticket_info", {"ticket_id": "P1-LATEST"}),
        ("check_access_permission", {"access_level": 3, "requester_role": "contractor", "is_emergency": True}),
    ]:
        print(f"\n[{tool_name}]")
        print(json.dumps(dispatch_tool(tool_name, payload), ensure_ascii=False, indent=2)[:800])
