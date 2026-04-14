"""
mcp_server.py — Real HTTP MCP Server (Sprint 3)

Supports two usage modes:
1) In-process calls via dispatch_tool(...)
2) HTTP server endpoints:
   - GET  /health
   - GET  /tools/list
   - POST /tools/call

Guardrails (last defense layer):
- Validate and normalize all tool inputs server-side
- Reject unknown tools and malformed requests
- Block side-effect tools by default unless explicitly allowed
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


# ─────────────────────────────────────────────
# Tool schemas
# ─────────────────────────────────────────────

TOOL_SCHEMAS = {
    "search_kb": {
        "name": "search_kb",
        "description": "Search internal Knowledge Base and return top-k chunks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "top_k": {"type": "integer", "description": "Top chunks", "default": 3},
            },
            "required": ["query"],
        },
    },
    "get_ticket_info": {
        "name": "get_ticket_info",
        "description": "Lookup ticket details from mock ticket system.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Ticket ID (e.g. IT-1234, P1-LATEST)"},
            },
            "required": ["ticket_id"],
        },
    },
    "check_access_permission": {
        "name": "check_access_permission",
        "description": "Check access policy constraints from Access Control SOP.",
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
        "description": "Create a mock ticket (side-effect guarded).",
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
# Tool implementations
# ─────────────────────────────────────────────

def tool_search_kb(query: str, top_k: int = 3) -> dict:
    try:
        from workers.retrieval import retrieve_dense

        chunks = retrieve_dense(query, top_k=top_k)
        sources = list(dict.fromkeys(c.get("source", "unknown") for c in chunks))
        return {
            "chunks": chunks,
            "sources": sources,
            "total_found": len(chunks),
        }
    except Exception as exc:
        return {
            "chunks": [],
            "sources": [],
            "total_found": 0,
            "error": f"search_kb failed: {exc}",
        }


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
    ticket = MOCK_TICKETS.get(ticket_id.upper())
    if ticket:
        return ticket
    return {
        "error": f"Ticket '{ticket_id}' không tìm thấy trong hệ thống.",
        "available_mock_ids": list(MOCK_TICKETS.keys()),
    }


ACCESS_RULES = {
    1: {
        "required_approvers": ["Line Manager"],
        "emergency_can_bypass": False,
    },
    2: {
        "required_approvers": ["Line Manager", "IT Admin"],
        "emergency_can_bypass": True,
        "emergency_bypass_note": "Level 2 có thể cấp tạm thời với approval đồng thời của Line Manager và IT Admin on-call.",
    },
    3: {
        "required_approvers": ["Line Manager", "IT Admin", "IT Security"],
        "emergency_can_bypass": False,
    },
}


def tool_check_access_permission(access_level: int, requester_role: str, is_emergency: bool = False) -> dict:
    rule = ACCESS_RULES.get(access_level)
    if not rule:
        return {"error": f"Access level {access_level} không hợp lệ. Levels: 1, 2, 3."}

    notes = []
    if is_emergency and not rule.get("emergency_can_bypass"):
        notes.append(f"Level {access_level} KHÔNG có emergency bypass. Phải follow quy trình chuẩn.")
    if is_emergency and rule.get("emergency_can_bypass"):
        notes.append(rule.get("emergency_bypass_note", ""))

    return {
        "access_level": access_level,
        "can_grant": True,
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
        "note": "MOCK ticket — không tồn tại trong hệ thống thật",
    }


TOOL_REGISTRY: dict[str, Callable[..., dict]] = {
    "search_kb": tool_search_kb,
    "get_ticket_info": tool_get_ticket_info,
    "check_access_permission": tool_check_access_permission,
    "create_ticket": tool_create_ticket,
}


# ─────────────────────────────────────────────
# Guardrails (last defense layer)
# ─────────────────────────────────────────────

def _error(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _validate_required(tool_name: str, tool_input: dict[str, Any]) -> dict | None:
    required = TOOL_SCHEMAS[tool_name].get("inputSchema", {}).get("required", [])
    missing = [field for field in required if field not in tool_input]
    if missing:
        return _error("MCP_INVALID_INPUT", f"Missing required fields for {tool_name}", {"missing": missing})
    return None


def _normalize_input(tool_name: str, tool_input: dict[str, Any]) -> tuple[dict[str, Any], dict | None]:
    inp = dict(tool_input or {})
    missing_error = _validate_required(tool_name, inp)
    if missing_error:
        return inp, missing_error

    if tool_name == "search_kb":
        query = str(inp.get("query", "")).strip()
        if not query:
            return inp, _error("MCP_INVALID_INPUT", "query must not be empty")
        try:
            top_k = int(inp.get("top_k", 3))
        except Exception:
            return inp, _error("MCP_INVALID_INPUT", "top_k must be an integer")
        inp["query"] = query[:500]
        inp["top_k"] = max(1, min(5, top_k))

    elif tool_name == "get_ticket_info":
        ticket_id = str(inp.get("ticket_id", "")).strip().upper()
        if not ticket_id:
            return inp, _error("MCP_INVALID_INPUT", "ticket_id must not be empty")
        inp["ticket_id"] = ticket_id[:32]

    elif tool_name == "check_access_permission":
        try:
            access_level = int(inp.get("access_level", 0))
        except Exception:
            return inp, _error("MCP_INVALID_INPUT", "access_level must be an integer")
        if access_level not in {1, 2, 3}:
            return inp, _error("MCP_INVALID_INPUT", "access_level must be 1, 2, or 3")
        requester_role = str(inp.get("requester_role", "")).strip().lower()
        if requester_role not in {"employee", "contractor", "oncall", "it_admin"}:
            return inp, _error(
                "MCP_INVALID_INPUT",
                "requester_role must be one of: employee, contractor, oncall, it_admin",
            )
        inp["access_level"] = access_level
        inp["requester_role"] = requester_role
        inp["is_emergency"] = bool(inp.get("is_emergency", False))

    elif tool_name == "create_ticket":
        priority = str(inp.get("priority", "")).strip().upper()
        if priority not in {"P1", "P2", "P3", "P4"}:
            return inp, _error("MCP_INVALID_INPUT", "priority must be one of: P1, P2, P3, P4")
        title = str(inp.get("title", "")).strip()
        if len(title) < 5:
            return inp, _error("MCP_INVALID_INPUT", "title must be at least 5 chars")
        inp["priority"] = priority
        inp["title"] = title[:200]
        inp["description"] = str(inp.get("description", ""))[:1000]

    return inp, None


def _guard_side_effects(tool_name: str, metadata: dict[str, Any] | None) -> dict | None:
    if tool_name != "create_ticket":
        return None
    allow_env = _bool_env("MCP_ALLOW_SIDE_EFFECTS", default=False)
    allow_meta = bool((metadata or {}).get("allow_side_effects", False))
    if not (allow_env and allow_meta):
        return _error(
            "MCP_GUARD_BLOCKED",
            "Side-effect tool blocked by MCP safeguard layer",
            {
                "tool": tool_name,
                "hint": "Set MCP_ALLOW_SIDE_EFFECTS=true and metadata.allow_side_effects=true to enable",
            },
        )
    return None


# ─────────────────────────────────────────────
# Public MCP dispatch API
# ─────────────────────────────────────────────

def list_tools() -> list:
    return list(TOOL_SCHEMAS.values())


def dispatch_tool(tool_name: str, tool_input: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict:
    if tool_name not in TOOL_REGISTRY:
        return _error("MCP_UNKNOWN_TOOL", f"Tool '{tool_name}' không tồn tại", {"available": list(TOOL_REGISTRY.keys())})

    side_effect_error = _guard_side_effects(tool_name, metadata)
    if side_effect_error:
        return side_effect_error

    normalized_input, input_error = _normalize_input(tool_name, tool_input)
    if input_error:
        return input_error

    try:
        return TOOL_REGISTRY[tool_name](**normalized_input)
    except TypeError as exc:
        return _error("MCP_INVALID_INPUT", f"Invalid input for tool '{tool_name}'", {"reason": str(exc)})
    except Exception as exc:
        return _error("MCP_EXECUTION_FAILED", f"Tool '{tool_name}' execution failed", {"reason": str(exc)})


# ─────────────────────────────────────────────
# HTTP server endpoints
# ─────────────────────────────────────────────

class MCPHttpHandler(BaseHTTPRequestHandler):
    server_version = "Day09MCP/1.0"

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> tuple[dict[str, Any] | None, dict | None]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                return None, _error("MCP_INVALID_REQUEST", "Request body must be a JSON object")
            return data, None
        except Exception as exc:
            return None, _error("MCP_INVALID_REQUEST", "Invalid JSON request", {"reason": str(exc)})

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"ok": True, "service": "mcp_server", "timestamp": datetime.now().isoformat()})
            return
        if self.path == "/tools/list":
            self._send_json({"ok": True, "tools": list_tools()})
            return
        self._send_json(_error("MCP_NOT_FOUND", "Endpoint not found", {"path": self.path}), status=404)

    def do_POST(self) -> None:
        if self.path != "/tools/call":
            self._send_json(_error("MCP_NOT_FOUND", "Endpoint not found", {"path": self.path}), status=404)
            return

        body, body_error = self._read_json_body()
        if body_error:
            self._send_json(body_error, status=400)
            return

        if body is None:
            self._send_json(_error("MCP_INVALID_REQUEST", "Empty request body"), status=400)
            return

        tool = body.get("tool")
        tool_input = body.get("input", {})
        metadata = body.get("metadata", {})

        if not isinstance(tool, str) or not tool.strip():
            self._send_json(_error("MCP_INVALID_REQUEST", "'tool' must be a non-empty string"), status=400)
            return
        if not isinstance(tool_input, dict):
            self._send_json(_error("MCP_INVALID_REQUEST", "'input' must be an object"), status=400)
            return
        if metadata is not None and not isinstance(metadata, dict):
            self._send_json(_error("MCP_INVALID_REQUEST", "'metadata' must be an object"), status=400)
            return

        output = dispatch_tool(tool.strip(), tool_input, metadata=metadata)
        ok = "error" not in output
        self._send_json(
            {
                "ok": ok,
                "tool": tool,
                "output": output if ok else None,
                "error": output.get("error") if not ok else None,
                "timestamp": datetime.now().isoformat(),
            },
            status=200 if ok else 400,
        )


def run_http_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), MCPHttpHandler)
    print(f"🚀 MCP HTTP server running at http://{host}:{port}")
    print("   Endpoints: GET /health | GET /tools/list | POST /tools/call")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 MCP server stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    try:
        port = int(os.getenv("MCP_SERVER_PORT", "8080"))
    except ValueError:
        port = 8080

    mode = os.getenv("MCP_SERVER_MODE", "http").strip().lower()
    if mode == "http":
        run_http_server(host=host, port=port)
    else:
        print("📋 Available tools:")
        for t in list_tools():
            print(f"  • {t['name']}")
        print("\n🔍 Demo call: search_kb")
        print(dispatch_tool("search_kb", {"query": "SLA P1 resolution", "top_k": 2}))
