import json, sys
sys.path.insert(0, '/work/tests')
from mcp_client import McpClient
m = McpClient(["freecad-mcp", "--only-text-feedback"])
init = m.start()
print("SERVER", json.dumps(init.get("serverInfo")), init.get("protocolVersion"))
tools = m.request("tools/list", {})["tools"]
print("TOOLS", len(tools), sorted(t["name"] for t in tools))
r = m.call_tool("get_rpc_status", {})
print("STATUS", m.text(r)[:1500])
m.close()
