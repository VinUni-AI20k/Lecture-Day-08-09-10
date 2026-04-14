"""
mcp_client.py — MCP Client with Pluggable Transport (Sprint 3)
Replaces direct `from mcp_server import dispatch_tool` calls in workers.

BEFORE (Sprint 2):
    from mcp_server import dispatch_tool
    result = dispatch_tool("search_kb", {"query": task})

AFTER (Sprint 3):
    from mcp_client import get_client
    from mcp_protocol import MCPRequest, MCPContext

    client = get_client()
    response = client.dispatch(MCPRequest(
        tool_name="search_kb",
        tool_input={"query": task, "top_k": 3},
        context=MCPContext(run_id=state["run_id"], caller="policy_tool_worker"),
    ))
    if response.is_ok():
        chunks = response.output["chunks"]

Transport selection (via env var MCP_TRANSPORT):
    inprocess (default) — calls mcp_server in-process (no network overhead)
    http                — POSTs to MCP HTTP server (run mcp_http_server.py first)

To switch to HTTP mode:
    $ MCP_TRANSPORT=http MCP_SERVER_URL=http://localhost:8000 python graph.py
"""

import os
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from mcp_protocol import MCPContext, MCPError, MCPRequest, MCPResponse


# ─────────────────────────────────────────────────────
# Transport Layer — pluggable, swappable
# ─────────────────────────────────────────────────────

class MCPTransport(ABC):
    """
    Abstract transport interface.

    Subclasses implement how MCPRequests are sent to the server.
    Workers depend on MCPTransport (not InProcessTransport or HttpTransport
    directly), so the transport can be swapped without changing worker code.
    """

    @abstractmethod
    def call(self, request: MCPRequest) -> MCPResponse:
        """Execute a tool call and return a structured response. Never raises."""
        ...

    @abstractmethod
    def list_tools(self) -> list:
        """Return list of available tool schemas from the server."""
        ...


class InProcessTransport(MCPTransport):
    """
    In-process transport: calls mcp_server.dispatch_tool() directly.

    This is the default transport for the lab. It has zero network overhead
    and is fully backward compatible with the existing mcp_server.py.

    The key improvement over the Sprint 2 approach is that the result is
    now wrapped in an MCPResponse envelope (with request_id, latency, error
    structure) instead of a raw dict.
    """

    def call(self, request: MCPRequest) -> MCPResponse:
        import mcp_server  # lazy import — avoids circular deps at module load time

        start = time.time()
        try:
            raw_output = mcp_server.dispatch_tool(request.tool_name, request.tool_input)
            latency_ms = int((time.time() - start) * 1000)

            # mcp_server signals errors by returning {"error": "..."} with no other keys.
            # We detect this pattern and convert it to a proper MCPError.
            if (
                isinstance(raw_output, dict)
                and "error" in raw_output
                and len(raw_output) == 1
            ):
                return MCPResponse(
                    request_id=request.request_id,
                    tool_name=request.tool_name,
                    status="error",
                    error=MCPError(
                        code="TOOL_EXEC_FAILED",
                        message=str(raw_output["error"]),
                    ),
                    latency_ms=latency_ms,
                )

            return MCPResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status="success",
                output=raw_output,
                latency_ms=latency_ms,
            )

        except Exception as exc:
            latency_ms = int((time.time() - start) * 1000)
            return MCPResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status="error",
                error=MCPError(
                    code="TRANSPORT_FAILED",
                    message=str(exc),
                    details={"transport": "inprocess"},
                ),
                latency_ms=latency_ms,
            )

    def list_tools(self) -> list:
        import mcp_server
        return mcp_server.list_tools()


class HttpTransport(MCPTransport):
    """
    HTTP transport: sends JSON requests to a running MCP HTTP server.

    Designed to work with mcp_http_server.py (FastAPI).
    Enables running the MCP server as a separate process or microservice,
    which is the first step toward a microservices-ready architecture.

    Setup:
        1. Start the server:  uvicorn mcp_http_server:app --port 8000
        2. Set env vars:      MCP_TRANSPORT=http MCP_SERVER_URL=http://localhost:8000
        3. Run workers:       python graph.py (workers auto-use HTTP)
    """

    def __init__(self, base_url: Optional[str] = None, timeout: int = 60):
        self.base_url = (base_url or os.getenv("MCP_SERVER_URL", "http://localhost:8000")).rstrip("/")
        self.timeout = timeout

    def call(self, request: MCPRequest) -> MCPResponse:
        try:
            import requests as http_requests
        except ImportError:
            return MCPResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status="error",
                error=MCPError(
                    code="DEPENDENCY_MISSING",
                    message="HttpTransport requires 'requests' package. Run: pip install requests",
                ),
            )

        start = time.time()
        try:
            resp = http_requests.post(
                f"{self.base_url}/tools/call",
                json=request.to_dict(),
                timeout=self.timeout,
            )
            latency_ms = int((time.time() - start) * 1000)
            resp.raise_for_status()
            data = resp.json()

            # Normalize server response into MCPResponse
            if data.get("status") == "error":
                err = data.get("error") or {}
                return MCPResponse(
                    request_id=data.get("request_id", request.request_id),
                    tool_name=data.get("tool_name", request.tool_name),
                    status="error",
                    error=MCPError(
                        code=err.get("code", "SERVER_ERROR"),
                        message=err.get("message", "Unknown server error"),
                        details=err.get("details"),
                    ),
                    latency_ms=latency_ms,
                )

            return MCPResponse(
                request_id=data.get("request_id", request.request_id),
                tool_name=data.get("tool_name", request.tool_name),
                status="success",
                output=data.get("output"),
                latency_ms=latency_ms,
            )

        except Exception as exc:
            latency_ms = int((time.time() - start) * 1000)
            return MCPResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status="error",
                error=MCPError(
                    code="HTTP_TRANSPORT_FAILED",
                    message=str(exc),
                    details={"url": f"{self.base_url}/tools/call"},
                ),
                latency_ms=latency_ms,
            )

    def list_tools(self) -> list:
        try:
            import requests as http_requests
            resp = http_requests.get(f"{self.base_url}/tools", timeout=10)
            resp.raise_for_status()
            return resp.json().get("tools", [])
        except Exception as exc:
            print(f"[MCPClient][HttpTransport] list_tools failed: {exc}")
            return []


# ─────────────────────────────────────────────────────
# MCPClient — unified interface used by all workers
# ─────────────────────────────────────────────────────

class MCPClient:
    """
    MCP Client — used by workers instead of importing mcp_server directly.

    Responsibilities:
    - Wrap tool calls in MCPRequest/MCPResponse protocol
    - Delegate transport (in-process vs. HTTP) to the injected MCPTransport
    - Never raise exceptions — always return MCPResponse (callers check is_ok())

    Usage:
        from mcp_client import get_client
        from mcp_protocol import MCPRequest, MCPContext

        client = get_client()
        response = client.dispatch(MCPRequest(
            tool_name="check_access_permission",
            tool_input={"access_level": 3, "requester_role": "contractor"},
            context=MCPContext(run_id=state["run_id"], caller="policy_tool_worker"),
        ))
        if response.is_ok():
            print(response.output)
        else:
            print(f"Error: {response.error.code}: {response.error.message}")
    """

    def __init__(self, transport: Optional[MCPTransport] = None):
        self._transport: MCPTransport = transport or _default_transport()

    def dispatch(self, request: MCPRequest) -> MCPResponse:
        """
        Execute a tool call via the configured transport.

        Args:
            request: MCPRequest with tool_name, tool_input, and optional context.

        Returns:
            MCPResponse — always. Check response.is_ok() before using response.output.
        """
        return self._transport.call(request)

    def list_tools(self) -> list:
        """
        Discover all available tools from the MCP server.

        Returns:
            List of tool schema dicts (same format as mcp_server.list_tools()).
        """
        return self._transport.list_tools()


# ─────────────────────────────────────────────────────
# Transport factory & singleton accessor
# ─────────────────────────────────────────────────────

def _default_transport() -> MCPTransport:
    """
    Select transport based on MCP_TRANSPORT environment variable.

    Defaults to InProcessTransport if env var is not set or is "inprocess".
    Set MCP_TRANSPORT=http to use HttpTransport.
    """
    transport_type = os.getenv("MCP_TRANSPORT", "inprocess").lower().strip()
    if transport_type == "http":
        base_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        print(f"[MCPClient] Using HttpTransport → {base_url}")
        return HttpTransport(base_url=base_url)
    return InProcessTransport()


_singleton: Optional[MCPClient] = None


def get_client(transport: Optional[MCPTransport] = None) -> MCPClient:
    """
    Returns the singleton MCPClient instance.

    Constructing on first call using the default transport.
    Pass a custom `transport` to override (useful in tests).

    Args:
        transport: Optional custom transport. If provided, a new client is created.

    Returns:
        MCPClient instance.
    """
    global _singleton
    if transport is not None:
        # Allow override (e.g. in tests: get_client(transport=MockTransport()))
        return MCPClient(transport=transport)
    if _singleton is None:
        _singleton = MCPClient()
    return _singleton


def reset_client() -> None:
    """Reset the singleton — useful in tests to force re-initialization."""
    global _singleton
    _singleton = None


# ─────────────────────────────────────────────────────
# Smoke test
# ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    print("=" * 60)
    print("MCPClient — Sprint 3 Smoke Test")
    print("=" * 60)

    transport_type = os.getenv("MCP_TRANSPORT", "inprocess")
    print(f"\nTransport: {transport_type}")

    client = get_client()

    # 1. List tools
    print("\n📋 Listing tools via client:")
    tools = client.list_tools()
    for t in tools:
        print(f"  • {t['name']}: {t['description'][:60]}...")

    # 2. search_kb
    print("\n🔍 Test: search_kb")
    resp = client.dispatch(MCPRequest(
        tool_name="search_kb",
        tool_input={"query": "SLA P1 resolution time", "top_k": 2},
        context=MCPContext(run_id="test_run_001", caller="smoke_test"),
    ))
    print(f"  status: {resp.status} | latency: {resp.latency_ms}ms | request_id: {resp.request_id[:8]}...")
    if resp.is_ok():
        print(f"  total_found: {resp.output.get('total_found')}")
    else:
        print(f"  error: {resp.error.code}: {resp.error.message}")

    # 3. get_ticket_info
    print("\n🎫 Test: get_ticket_info")
    resp2 = client.dispatch(MCPRequest(
        tool_name="get_ticket_info",
        tool_input={"ticket_id": "P1-LATEST"},
        context=MCPContext(run_id="test_run_001", caller="smoke_test"),
    ))
    print(f"  status: {resp2.status} | latency: {resp2.latency_ms}ms")
    if resp2.is_ok():
        print(f"  ticket: {resp2.output.get('ticket_id')} | priority: {resp2.output.get('priority')}")
    else:
        print(f"  error: {resp2.error.code}")

    # 4. check_access_permission
    print("\n🔐 Test: check_access_permission (Level 3, emergency)")
    resp3 = client.dispatch(MCPRequest(
        tool_name="check_access_permission",
        tool_input={"access_level": 3, "requester_role": "contractor", "is_emergency": True},
        context=MCPContext(run_id="test_run_001", caller="smoke_test"),
    ))
    print(f"  status: {resp3.status}")
    if resp3.is_ok():
        print(f"  can_grant: {resp3.output.get('can_grant')}")
        print(f"  required_approvers: {resp3.output.get('required_approvers')}")
        print(f"  emergency_override: {resp3.output.get('emergency_override')}")

    # 5. Invalid tool (error case)
    print("\n❌ Test: nonexistent_tool")
    resp4 = client.dispatch(MCPRequest(
        tool_name="nonexistent_tool",
        tool_input={},
    ))
    print(f"  status: {resp4.status}")
    print(f"  error.code: {resp4.error.code}")
    print(f"  error.message: {resp4.error.message}")

    print(f"\n✅ MCPClient Sprint 3 smoke test done (transport={transport_type}).")
    print("   To test HTTP transport: MCP_TRANSPORT=http python mcp_client.py")
