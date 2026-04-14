"""
workers/mcp_client.py — Shared MCP client adapter for workers.

Workers call this module instead of importing mcp_server directly,
so the transport can be swapped later without touching each worker.
"""

from datetime import datetime


def call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """Call an MCP tool through the local compatibility adapter."""
    try:
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
