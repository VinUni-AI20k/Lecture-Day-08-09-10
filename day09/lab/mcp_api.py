from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn
from mcp_server import list_tools, dispatch_tool

app = FastAPI(title="MCP HTTP Server - Team 67")

class ToolCallRequest(BaseModel):
    tool_name: str
    tool_input: Dict[str, Any]

@app.get("/")
async def root():
    return {"message": "MCP HTTP Server - Team 67", "version": "1.0", "status": "running"}

@app.get("/tools")
async def get_tools():
    return {"tools": list_tools()}

@app.post("/tools/call")
async def call_tool(request: ToolCallRequest):
    result = dispatch_tool(request.tool_name, request.tool_input)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)