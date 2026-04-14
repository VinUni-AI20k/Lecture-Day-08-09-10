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

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────
# Tool Definitions (Schema Discovery)
#
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
        "emergency_bypass_note": "Level 2 can be granted temporarily with approval from Line Manager and IT Admin on-call.",
        "note": "Elevated access",
    },
    3: {
        "required_approvers": ["Line Manager", "IT Admin", "IT Security"],
        "emergency_can_bypass": False,
        "note": "Admin access — no emergency bypass",
    },
}


# ─────────────────────────────────────────────
# MCP Server Implementation
# ─────────────────────────────────────────────

class MCPServer:
    """
    Mock MCP Server providing internal tools for the AI Agent.
    Following the Model Context Protocol (MCP) design patterns.
    """

    def __init__(self):
        self.tool_schemas = TOOL_SCHEMAS
        self.tickets = {
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
                "assignee": "tran.thi.b@company.internal",
                "created_at": "2026-04-13T09:15:00",
                "sla_deadline": "2026-04-14T09:15:00",
                "escalated": False,
            },
            "IT-5678": {
                "ticket_id": "IT-5678",
                "priority": "P3",
                "title": "Cần cập nhật plugin Slack cho Jira",
                "status": "resolved",
                "assignee": "le.van.c@company.internal",
                "created_at": "2026-04-10T14:20:00",
                "sla_deadline": "2026-04-12T14:20:00",
                "escalated": False,
            },
        }
        self.access_rules = ACCESS_RULES

    def search_kb(self, query: str, top_k: int = 3) -> dict:
        """
        Search Knowledge Base using ChromaDB (via retrieval worker).
        """
        try:
            # Reusing retrieval logic from workers/retrieval.py for consistency
            import sys
            sys.path.insert(0, os.path.dirname(__file__))
            from workers.retrieval import retrieve_dense
            
            chunks = retrieve_dense(query, top_k=top_k)
            sources = list({c["source"] for c in chunks})
            
            return {
                "chunks": chunks,
                "sources": sources,
                "total_found": len(chunks),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": f"Failed to query Knowledge Base: {str(e)}",
                "chunks": [],
                "sources": [],
                "total_found": 0
            }

    def get_ticket_info(self, ticket_id: str) -> dict:
        """
        Lookup ticket information from mock database.
        """
        ticket_id = ticket_id.upper()
        # Handle special keyword if agent looks for the most critical one
        if ticket_id in ["P1", "LATEST-P1", "URGENT"]:
            ticket_id = "P1-LATEST"
            
        ticket = self.tickets.get(ticket_id)
        if ticket:
            return {
                **ticket,
                "queried_at": datetime.now().isoformat(),
                "status_code": 200
            }
        
        return {
            "error": f"Ticket '{ticket_id}' not found.",
            "available_ids": list(self.tickets.keys()),
            "status_code": 404
        }

    def check_access_permission(self, access_level: int, requester_role: str, is_emergency: bool = False) -> dict:
        """
        Check access permission conditions based on Access Control SOP.
        """
        rule = self.access_rules.get(access_level)
        if not rule:
            return {"error": f"Invalid access level {access_level}. Valids: 1, 2, 3."}

        can_grant = True
        notes = []

        if is_emergency and rule.get("emergency_can_bypass"):
            notes.append(rule.get("emergency_bypass_note", "Emergency bypass granted."))
            can_grant = True
        elif is_emergency and not rule.get("emergency_can_bypass"):
            notes.append(f"Level {access_level} does NOT allow emergency bypass. Standard process required.")
            can_grant = False if access_level == 3 else True # Simplify: Level 3 is strict

        return {
            "access_level": access_level,
            "can_grant": can_grant,
            "required_approvers": rule["required_approvers"],
            "emergency_override": is_emergency and rule.get("emergency_can_bypass", False),
            "notes": notes,
            "source": "access_control_sop.txt",
        }

    def create_ticket(self, priority: str, title: str, description: str = "") -> dict:
        """
        Create a new ticket (MOCK).
        """
        mock_id = f"IT-{1000 + hash(title) % 8999}"
        ticket = {
            "ticket_id": mock_id,
            "priority": priority,
            "title": title,
            "description": description[:500],
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "url": f"https://jira.company.internal/browse/{mock_id}",
            "note": "MOCK ticket created in system.",
        }
        return ticket

    def list_tools(self) -> list:
        return list(self.tool_schemas.values())

    def dispatch(self, tool_name: str, tool_input: dict) -> dict:
        """
        MCP Dispatcher: receives tool name and input, returns output.
        """
        # Map tool names to methods
        tool_map = {
            "search_kb": self.search_kb,
            "get_ticket_info": self.get_ticket_info,
            "check_access_permission": self.check_access_permission,
            "create_ticket": self.create_ticket,
        }

        if tool_name not in tool_map:
            return {"error": f"Tool '{tool_name}' not found."}

        try:
            return tool_map[tool_name](**tool_input)
        except Exception as e:
            return {"error": f"Execution error: {str(e)}"}


# ─────────────────────────────────────────────
# Global Instance for simple import
# ─────────────────────────────────────────────

_server = MCPServer()

def list_tools():
    return _server.list_tools()

def dispatch_tool(tool_name: str, tool_input: dict):
    return _server.dispatch(tool_name, tool_input)


# ─────────────────────────────────────────────
# Test & Demo
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import time
    
    print("\n" + "="*60)
    print("🚀  MOCK MCP SERVER — STANDALONE TEST")
    print("="*60)

    # 1. Discover tools
    print("\n[Discovery] Listing available tools...")
    tools = list_tools()
    for t in tools:
        print(f"  📦 {t['name']:<24} | {t['description'][:60]}...")

    # 2. Test search_kb
    print("\n[Tool Call] search_kb: 'SLA P1'...")
    res = dispatch_tool("search_kb", {"query": "SLA P1 resolution time", "top_k": 2})
    if "error" in res:
        print(f"  ❌ Error: {res['error']}")
    else:
        print(f"  ✅ Found {res['total_found']} chunks.")
        for i, c in enumerate(res['chunks']):
            print(f"     [{i+1}] {c.get('source')}: {c.get('text', '')[:80]}...")

    # 3. Test get_ticket_info
    print("\n[Tool Call] get_ticket_info: 'P1-LATEST'...")
    ticket = dispatch_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
    if "error" in ticket:
        print(f"  ❌ Error: {ticket['error']}")
    else:
        print(f"  🎫 Ticket {ticket['ticket_id']} ({ticket['priority']}) - Status: {ticket['status']}")
        print(f"     Assignee: {ticket['assignee']}")

    # 4. Test check_access_permission
    print("\n[Tool Call] check_access_permission: Level 3, Emergency...")
    perm = dispatch_tool("check_access_permission", {
        "access_level": 3, 
        "requester_role": "contractor", 
        "is_emergency": True
    })
    print(f"  🔐 Grant: {perm.get('can_grant')} | Approvers: {perm.get('required_approvers')}")
    print(f"     Notes: {perm.get('notes')}")

    print("\n" + "="*60)
    print("✅  MCP SERVER TEST FINISHED")
    print("="*60 + "\n")
