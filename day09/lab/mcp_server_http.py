"""
mcp_server_http.py — Real MCP Server (Bonus +2)
Sprint 3 Advanced: MCP server dùng thư viện `mcp` chính thức + FastAPI HTTP wrapper.

Hai chế độ chạy:
    1. MCP stdio mode (dùng với Claude Desktop / MCP clients):
       python mcp_server_http.py --stdio

    2. HTTP API mode (REST endpoints, dùng test bằng browser/curl):
       python mcp_server_http.py --http
       → http://localhost:8000/docs

Tools exposed (giống mcp_server.py nhưng qua protocol thật):
    • search_kb               — semantic search ChromaDB
    • get_ticket_info         — tra cứu ticket từ tickets.json
    • check_access_permission — kiểm tra quyền theo SOP
    • create_ticket           — tạo ticket mới persistent

Chạy thử HTTP:
    python mcp_server_http.py --http
    curl http://localhost:8000/tools
    curl -X POST http://localhost:8000/call/search_kb -H "Content-Type: application/json" \
         -d '{"query": "SLA P1", "top_k": 2}'
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Reuse tool implementations from mcp_server.py
sys.path.insert(0, str(Path(__file__).parent))
from mcp_server import (
    tool_search_kb,
    tool_get_ticket_info,
    tool_check_access_permission,
    tool_create_ticket,
    TOOL_SCHEMAS,
)


# ─────────────────────────────────────────────
# Mode 1: Real MCP Server (stdio transport)
# Dùng với Claude Desktop hoặc MCP-compatible clients
# ─────────────────────────────────────────────

def run_mcp_stdio():
    """
    Khởi chạy MCP server thật dùng thư viện `mcp` official.
    Transport: stdio (standard MCP protocol).
    """
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types

    app = Server("day09-kb-server")

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        tools = []

        tools.append(types.Tool(
            name="search_kb",
            description="Tìm kiếm Knowledge Base nội bộ bằng semantic search. Trả về top-k chunks liên quan nhất.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Câu hỏi hoặc keyword cần tìm"},
                    "top_k": {"type": "integer", "description": "Số chunks cần trả về", "default": 3},
                },
                "required": ["query"],
            },
        ))

        tools.append(types.Tool(
            name="get_ticket_info",
            description="Tra cứu thông tin ticket từ hệ thống nội bộ.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "ID ticket (VD: IT-1234, P1-LATEST)"},
                },
                "required": ["ticket_id"],
            },
        ))

        tools.append(types.Tool(
            name="check_access_permission",
            description="Kiểm tra điều kiện cấp quyền truy cập theo Access Control SOP.",
            inputSchema={
                "type": "object",
                "properties": {
                    "access_level": {"type": "integer", "description": "Level cần cấp (1-4)"},
                    "requester_role": {"type": "string", "description": "Vai trò của người yêu cầu"},
                    "is_emergency": {"type": "boolean", "description": "Có phải khẩn cấp không", "default": False},
                },
                "required": ["access_level", "requester_role"],
            },
        ))

        tools.append(types.Tool(
            name="create_ticket",
            description="Tạo ticket mới trong hệ thống (persistent storage).",
            inputSchema={
                "type": "object",
                "properties": {
                    "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["priority", "title"],
            },
        ))

        return tools

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        import json

        dispatch = {
            "search_kb": tool_search_kb,
            "get_ticket_info": tool_get_ticket_info,
            "check_access_permission": tool_check_access_permission,
            "create_ticket": tool_create_ticket,
        }

        if name not in dispatch:
            result = {"error": f"Tool '{name}' không tồn tại."}
        else:
            try:
                result = dispatch[name](**arguments)
            except Exception as e:
                result = {"error": str(e)}

        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    print("🚀 MCP stdio server starting (day09-kb-server)...", file=sys.stderr)
    asyncio.run(main())


# ─────────────────────────────────────────────
# Mode 2: FastAPI HTTP Server
# REST API wrapper, dễ test và tích hợp
# ─────────────────────────────────────────────

def run_http_server():
    """
    Khởi chạy FastAPI HTTP server expose 4 MCP tools dưới dạng REST endpoints.
    """
    import uvicorn
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    from typing import Any, Optional

    api = FastAPI(
        title="Day09 MCP Tool Server",
        description="FastAPI HTTP wrapper cho 4 MCP tools: search_kb, get_ticket_info, check_access_permission, create_ticket",
        version="1.0.0",
    )

    # ── Request models ──────────────────────────

    class SearchKBRequest(BaseModel):
        query: str
        top_k: int = 3

    class GetTicketRequest(BaseModel):
        ticket_id: str

    class CheckAccessRequest(BaseModel):
        access_level: int
        requester_role: str
        is_emergency: bool = False

    class CreateTicketRequest(BaseModel):
        priority: str
        title: str
        description: str = ""

    class GenericCallRequest(BaseModel):
        arguments: dict = {}

    # ── Endpoints ───────────────────────────────

    @api.get("/", summary="Server info")
    def root():
        return {
            "server": "day09-kb-server",
            "version": "1.0.0",
            "transport": "HTTP (FastAPI)",
            "tools": list(TOOL_SCHEMAS.keys()),
            "docs": "/docs",
        }

    @api.get("/tools", summary="List all available tools (MCP tools/list)")
    def list_tools():
        return {"tools": list(TOOL_SCHEMAS.values())}

    @api.post("/tools/search_kb", summary="Semantic search Knowledge Base")
    def search_kb(req: SearchKBRequest):
        result = tool_search_kb(query=req.query, top_k=req.top_k)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result

    @api.post("/tools/get_ticket_info", summary="Tra cứu thông tin ticket")
    def get_ticket_info(req: GetTicketRequest):
        result = tool_get_ticket_info(ticket_id=req.ticket_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    @api.post("/tools/check_access_permission", summary="Kiểm tra quyền truy cập")
    def check_access_permission(req: CheckAccessRequest):
        result = tool_check_access_permission(
            access_level=req.access_level,
            requester_role=req.requester_role,
            is_emergency=req.is_emergency,
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    @api.post("/tools/create_ticket", summary="Tạo ticket mới")
    def create_ticket(req: CreateTicketRequest):
        result = tool_create_ticket(
            priority=req.priority,
            title=req.title,
            description=req.description,
        )
        return result

    @api.post("/call/{tool_name}", summary="Generic tool dispatch (MCP tools/call)")
    def call_tool(tool_name: str, req: GenericCallRequest):
        """
        Generic endpoint tương đương MCP tools/call.
        Body: {"arguments": {...}}
        """
        dispatch = {
            "search_kb": tool_search_kb,
            "get_ticket_info": tool_get_ticket_info,
            "check_access_permission": tool_check_access_permission,
            "create_ticket": tool_create_ticket,
        }
        if tool_name not in dispatch:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' không tồn tại. Available: {list(dispatch.keys())}",
            )
        try:
            result = dispatch[tool_name](**req.arguments)
            return result
        except TypeError as e:
            raise HTTPException(status_code=422, detail=f"Invalid arguments: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    print("\n🚀 FastAPI MCP HTTP Server")
    print("   http://localhost:8000/docs  ← Swagger UI (test tools tại đây)")
    print("   http://localhost:8000/tools ← List tools")
    print("   POST /call/{tool_name}      ← Generic dispatch\n")

    uvicorn.run(api, host="localhost", port=8000)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Day09 MCP Server (real mcp library + FastAPI)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--stdio", action="store_true", help="Chạy MCP stdio server (dùng với Claude Desktop)")
    group.add_argument("--http", action="store_true", help="Chạy FastAPI HTTP server (port 8000)")
    args = parser.parse_args()

    if args.stdio:
        run_mcp_stdio()
    else:
        # Default: HTTP mode (dễ demo hơn)
        run_http_server()
