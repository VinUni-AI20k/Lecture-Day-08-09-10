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

from dotenv import load_dotenv
load_dotenv()

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
    }
}


# ─────────────────────────────────────────────
# Tool Implementations
# ─────────────────────────────────────────────

from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def _get_embedding(text:str):
    resp = client.embeddings.create(input=text, model="text-embedding-3-small")
    return resp.data[0].embedding


def tool_search_kb(query: str, top_k: int = 3) -> dict:
    """
    Tìm kiếm Knowledge Base bằng semantic search.

    TODO Sprint 3: Kết nối với ChromaDB thực.
    Hiện tại: Delegate sang retrieval worker.

    Implement by Phuoc
    """
    try:
        import chromadb
        
        client = chromadb.PersistentClient(path=os.getenv("CHROMA_DB_PATH"))
        collection = client.get_or_create_collection(os.getenv("CHROMA_COLLECTION"))
        query_embedding = _get_embedding(text = query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )

        chunks = []
        for i, (doc, dist, meta) in enumerate(zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0]
        )):
            chunks.append({
                "text": doc,
                "source": meta.get("source", "unknown"),
                "score": round(1 - dist, 4),  # cosine similarity
                "metadata": meta,
            })

        sources = list({c["source"] for c in chunks})            
        return {
            "chunks": chunks,
            "sources": sources,
            "total_found": len(chunks),
        }
    
    except Exception as e:
        print(e)
        # Fallback: return mock data nếu ChromaDB chưa setup
        return {
            "chunks": [
                {
                    "text": f"[MOCK] Không thể query ChromaDB: {e}. Kết quả giả lập.",
                    "source": "mock_data",
                    "score": 0.5,
                }
            ],
            "sources": ["mock_data"],
            "total_found": 1,
        }


# Mock ticket database
# MOCK_TICKETS = {
#     "P1-LATEST": {
#         "ticket_id": "IT-9847",
#         "priority": "P1",
#         "title": "API Gateway down — toàn bộ người dùng không đăng nhập được",
#         "status": "in_progress",
#         "assignee": "nguyen.van.a@company.internal",
#         "created_at": "2026-04-13T22:47:00",
#         "sla_deadline": "2026-04-14T02:47:00",
#         "escalated": True,
#         "escalated_to": "senior_engineer_team",
#         "notifications_sent": ["slack:#incident-p1", "email:incident@company.internal", "pagerduty:oncall"],
#     },
#     "IT-1234": {
#         "ticket_id": "IT-1234",
#         "priority": "P2",
#         "title": "Feature login chậm cho một số user",
#         "status": "open",
#         "assignee": None,
#         "created_at": "2026-04-13T09:15:00",
#         "sla_deadline": "2026-04-14T09:15:00",
#         "escalated": False,
#     },
# }


# def tool_get_ticket_info(ticket_id: str) -> dict:
#     """
#     Tra cứu thông tin ticket (mock data).
#     """
#     ticket = MOCK_TICKETS.get(ticket_id.upper())
#     if ticket:
#         return ticket
#     # Không tìm thấy
#     return {
#         "error": f"Ticket '{ticket_id}' không tìm thấy trong hệ thống.",
#         "available_mock_ids": list(MOCK_TICKETS.keys()),
#     }


# Mock access control rules, implement addition rule #4, `apply_for` key
# for each level
ACCESS_RULES = {
    1: {
        "required_approvers": ["Line Manager"],
        "emergency_can_bypass": False,
        "note": "Read Only",
        "apply_for": ["Staff", "contractor"]
    },
    2: {
        "required_approvers": ["Line Manager", "IT Admin"],
        "emergency_can_bypass": True,
        "emergency_bypass_note": "Level 2 có thể cấp tạm thời với approval đồng thời của Line Manager và IT Admin on-call.",
        "note": "Standard user access",
        "apply_for": ["Staff"]
    },
    3: {
        "required_approvers": ["Line Manager", "IT Admin", "IT Security"],
        "emergency_can_bypass": False,
        "note": "Elevated access",
        "apply_for": ["Team Lead", "Senior Engineer", "Manager"]
    },
    4: {
        "required_approvers": ["IT Manager", "CISO"],
        "emergency_can_bypass": False,
        "note": "Admin access — không có emergency bypass",
        "apply_for": ["DevOps", "SRE", "IT Admin"]
    },
}


def tool_check_access_permission(access_level: int, requester_role: str, is_emergency: bool = False) -> dict:
    """
    Kiểm tra điều kiện cấp quyền theo Access Control SOP.
    """
    rule = ACCESS_RULES.get(access_level)
    if not rule:
        return {"error": f"Access level {access_level} không hợp lệ. Levels: 1, 2, 3."}

    can_grant = True
    notes = []

    if requester_role not in rule['required_approvers']:
        can_grant = False

    if is_emergency and rule.get("emergency_can_bypass"):
        notes.append(rule.get("emergency_bypass_note", ""))
        can_grant = True
    elif is_emergency and not rule.get("emergency_can_bypass"):
        notes.append(f"Level {access_level} KHÔNG có emergency bypass. Phải follow quy trình chuẩn.")

    return {
        "can_grant": can_grant,
        "required_approvers": rule["required_approvers"],
        "approver_count": len(rule["required_approvers"]),
        "emergency_override": is_emergency and rule.get("emergency_can_bypass", False),
        "source": "access_control_sop.txt",
    }


# def tool_create_ticket(priority: str, title: str, description: str = "") -> dict:
#     """
#     Tạo ticket mới (MOCK — in log, không tạo thật).
#     """
#     mock_id = f"IT-{9900 + hash(title) % 99}"
#     ticket = {
#         "ticket_id": mock_id,
#         "priority": priority,
#         "title": title,
#         "description": description[:200],
#         "status": "open",
#         "created_at": datetime.now().isoformat(),
#         "url": f"https://jira.company.internal/browse/{mock_id}",
#         "note": "MOCK ticket — không tồn tại trong hệ thống thật",
#     }
#     print(f"  [MCP create_ticket] MOCK: {mock_id} | {priority} | {title[:50]}")
#     return ticket


# ─────────────────────────────────────────────
# Dispatch Layer — MCP server interface
# ─────────────────────────────────────────────

TOOL_REGISTRY = {
    "search_kb": tool_search_kb,
    "check_access_permission": tool_check_access_permission
}


def list_tools() -> list:
    """
    MCP discovery: trả về danh sách tools có sẵn.
    Tương đương với `tools/list` trong MCP protocol.
    """
    return list(TOOL_SCHEMAS.values())


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
    if tool_name not in TOOL_REGISTRY:
        return {
            "error": f"Tool '{tool_name}' không tồn tại. Available: {list(TOOL_REGISTRY.keys())}"
        }

    tool_fn = TOOL_REGISTRY[tool_name]
    try:
        result = tool_fn(**tool_input)
        return result
    except TypeError as e:
        return {
            "error": f"Invalid input for tool '{tool_name}': {e}",
            "schema": TOOL_SCHEMAS[tool_name]["inputSchema"],
        }
    except Exception as e:
        return {
            "error": f"Tool '{tool_name}' execution failed: {e}",
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

    # # 3. Test get_ticket_info
    # print("\n🎫 Test: get_ticket_info")
    # ticket = dispatch_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
    # print(f"  Ticket: {ticket.get('ticket_id')} | {ticket.get('priority')} | {ticket.get('status')}")
    # if ticket.get("notifications_sent"):
    #     print(f"  Notifications: {ticket['notifications_sent']}")

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