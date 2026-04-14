"""
mcp_server.py — Advanced MCP Server (FastAPI)
Sprint 3: Implement HTTP server để đạt Bonus +2.

Mô phỏng MCP (Model Context Protocol) interface qua REST API.
Agent (MCP client) sẽ gọi HTTP POST thay vì import code trực tiếp.

Tools available:
    1. search_kb(query, top_k)           → tìm kiếm Knowledge Base
    2. get_ticket_info(ticket_id)        → tra cứu thông tin ticket
    3. check_access_permission(level, requester_role)  → kiểm tra quyền
    4. create_ticket(priority, title, description)     → tạo ticket mới

Sử dụng (Client side trong policy_tool.py):
    import requests
    response = requests.post("http://localhost:8000/tools/call", json={
        "tool_name": "search_kb",
        "tool_input": {"query": "SLA P1", "top_k": 3}
    })
    result = response.json()

Chạy server:
    python mcp_server.py
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Khởi tạo FastAPI App
app = FastAPI(title="Mock MCP Server", description="Hệ thống cung cấp Tool cho Multi-Agent", version="1.0")

# ─────────────────────────────────────────────
# Tool Definitions (Schema Discovery)
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
    },
    "check_access_permission": {
        "name": "check_access_permission",
        "description": "Kiểm tra điều kiện cấp quyền truy cập theo Access Control SOP.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "access_level": {"type": "integer", "description": "Level cần cấp (1, 2, hoặc 3)"},
                "requester_role": {"type": "string", "description": "Vai trò người yêu cầu"},
                "is_emergency": {"type": "boolean", "description": "Có phải khẩn cấp không", "default": False},
            },
            "required": ["access_level", "requester_role"],
        },
    },
    "create_ticket": {
        "name": "create_ticket",
        "description": "Tạo ticket mới trong hệ thống Jira (MOCK).",
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

# ─────────────────────────────────────────────
# Tool Implementations (Business Logic)
# ─────────────────────────────────────────────
def tool_search_kb(query: str, top_k: int = 3) -> dict:
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from workers.retrieval import retrieve_dense
        chunks = retrieve_dense(query, top_k=top_k)
        sources = list({c["source"] for c in chunks})
        return {"chunks": chunks, "sources": sources, "total_found": len(chunks)}
    except Exception as e:
        return {
            "chunks": [{"text": f"[MOCK] Fallback mode. Cannot query DB: {e}", "source": "mock_data", "score": 0.5}],
            "sources": ["mock_data"],
            "total_found": 1,
        }

MOCK_TICKETS = {
    "P1-LATEST": {
        "ticket_id": "IT-9847", "priority": "P1", "title": "API Gateway down",
        "status": "in_progress", "assignee": "nguyen.van.a@company.internal",
        "created_at": "2026-04-13T22:47:00", "sla_deadline": "2026-04-14T02:47:00",
        "escalated": True, "escalated_to": "senior_engineer_team"
    },
    "IT-1234": {
        "ticket_id": "IT-1234", "priority": "P2", "title": "Feature login chậm",
        "status": "open", "assignee": None,
        "created_at": "2026-04-13T09:15:00", "sla_deadline": "2026-04-14T09:15:00",
        "escalated": False,
    },
}

def tool_get_ticket_info(ticket_id: str) -> dict:
    ticket = MOCK_TICKETS.get(ticket_id.upper())
    return ticket if ticket else {"error": f"Ticket '{ticket_id}' không tìm thấy.", "available_ids": list(MOCK_TICKETS.keys())}

ACCESS_RULES = {
    1: {"required_approvers": ["Line Manager"], "emergency_can_bypass": False},
    2: {"required_approvers": ["Line Manager", "IT Admin"], "emergency_can_bypass": True, "emergency_bypass_note": "Cấp tạm thời với approval từ Line Manager và IT Admin on-call."},
    3: {"required_approvers": ["Line Manager", "IT Admin", "IT Security"], "emergency_can_bypass": False},
}

def tool_check_access_permission(access_level: int, requester_role: str, is_emergency: bool = False) -> dict:
    rule = ACCESS_RULES.get(access_level)
    if not rule:
        return {"error": f"Access level {access_level} không hợp lệ."}

    can_grant = True
    notes = []
    if is_emergency and rule.get("emergency_can_bypass"):
        notes.append(rule.get("emergency_bypass_note", ""))
    elif is_emergency and not rule.get("emergency_can_bypass"):
        notes.append(f"Level {access_level} KHÔNG có emergency bypass. Phải follow quy trình chuẩn.")

    return {
        "can_grant": can_grant, "required_approvers": rule["required_approvers"],
        "emergency_override": is_emergency and rule.get("emergency_can_bypass", False),
        "notes": notes, "source": "access_control_sop.txt",
    }

def tool_create_ticket(priority: str, title: str, description: str = "") -> dict:
    mock_id = f"IT-{9900 + hash(title) % 99}"
    return {
        "ticket_id": mock_id, "priority": priority, "title": title, "status": "open",
        "url": f"https://jira.company.internal/browse/{mock_id}"
    }

TOOL_REGISTRY = {
    "search_kb": tool_search_kb,
    "get_ticket_info": tool_get_ticket_info,
    "check_access_permission": tool_check_access_permission,
    "create_ticket": tool_create_ticket,
}

# ─────────────────────────────────────────────
# API Endpoints (FastAPI)
# ─────────────────────────────────────────────

class ToolCallRequest(BaseModel):
    tool_name: str
    tool_input: dict

@app.get("/tools/list")
def list_tools_api():
    """MCP discovery: Trả về danh sách schema của các tools."""
    return {"tools": list(TOOL_SCHEMAS.values())}

@app.post("/tools/call")
def dispatch_tool_api(request: ToolCallRequest):
    """MCP execution: Gọi tool và nhận kết quả."""
    tool_name = request.tool_name
    tool_input = request.tool_input

    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' không tồn tại.")
    
    tool_fn = TOOL_REGISTRY[tool_name]
    try:
        result = tool_fn(**tool_input)
        return {"tool_name": tool_name, "status": "success", "result": result}
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"Lỗi input: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi thực thi: {e}")

# ─────────────────────────────────────────────
# Khởi chạy Server
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Khởi chạy MCP Server (FastAPI) trên cổng 8000...")
    print("Truy cập http://localhost:8000/docs để xem Swagger UI.")
    print("=" * 60)
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=8000, reload=True)