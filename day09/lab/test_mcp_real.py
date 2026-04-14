import os
import sys
import unittest
import requests
import time

# Ensure project root in path
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

class TestRealMCPIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Thiết lập environment cho HTTP transport
        os.environ["MCP_TRANSPORT"] = "http"
        os.environ["MCP_SERVER_URL"] = "http://localhost:8030"
        
        # Thử kết nối tới server (đã chạy ở background)
        max_retries = 5
        for i in range(max_retries):
            try:
                resp = requests.get("http://localhost:8030/health", timeout=2)
                if resp.status_code == 200:
                    print(f"\n[OK] MCP Server reachable at http://localhost:8030")
                    return
            except Exception:
                pass
            print(f"Waiting for MCP server (retry {i+1}/{max_retries})...")
            time.sleep(2)
        raise RuntimeError("MCP Server not reachable. Make sure uvicorn is running on port 8000.")

    def test_01_list_tools(self):
        from mcp_client import get_client
        client = get_client()
        tools = client.list_tools()
        self.assertGreaterEqual(len(tools), 2, "Should have at least 2 tools (search_kb and get_ticket_info)")
        tool_names = [t['name'] for t in tools]
        self.assertIn("search_kb", tool_names)
        self.assertIn("get_ticket_info", tool_names)

    def test_02_search_kb_tool(self):
        from mcp_client import get_client
        from mcp_protocol import MCPRequest
        client = get_client()
        resp = client.dispatch(MCPRequest(
            tool_name="search_kb",
            tool_input={"query": "SLA P1", "top_k": 1}
        ))
        self.assertTrue(resp.is_ok(), f"search_kb failed: {resp.error.message if resp.error else 'unknown error'}")
        self.assertIn("chunks", resp.output)
        self.assertGreater(len(resp.output["chunks"]), 0)

    def test_03_get_ticket_info_tool(self):
        from mcp_client import get_client
        from mcp_protocol import MCPRequest
        client = get_client()
        resp = client.dispatch(MCPRequest(
            tool_name="get_ticket_info",
            tool_input={"ticket_id": "P1-LATEST"}
        ))
        self.assertTrue(resp.is_ok(), f"get_ticket_info failed: {resp.error.message if resp.error else 'unknown error'}")
        self.assertEqual(resp.output["priority"], "P1")

    def test_04_policy_tool_integration(self):
        # Test xem policy_tool_worker có gọi được MCP qua HTTP không
        from workers.policy_tool import run as policy_run
        test_state = {
            "task": "SLA ticket P1 là bao lâu?",
            "needs_tool": True,
            "retrieved_chunks": [],
            "mcp_tools_used": [],
            "history": [],
            "run_id": "test_integration_run"
        }
        result = policy_run(test_state)
        self.assertGreater(len(result["mcp_tools_used"]), 0, "Policy tool should have used at least one MCP tool")
        
        # Kiểm tra xem log từ server có đúng không (request_id, latency, v.v.)
        for call in result["mcp_tools_used"]:
            self.assertIn("request_id", call)
            self.assertIn("latency_ms", call)

if __name__ == "__main__":
    unittest.main()
