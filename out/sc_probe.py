import json, sys
sys.path.insert(0, '/work/tests')
from mcp_client import McpClient
m = McpClient(["solidcraft-cli", "mcp", "--allow-path", "/lab/out"])
init = m.start(); print("SERVER", init.get("serverInfo"))
print("TOOLS", sorted(t["name"] for t in m.request("tools/list", {})["tools"]))
r = m.text_json(m.call_tool("list_commands", {}))
txt = json.dumps(r)
print(len(txt))
open('/work/out/sc_list_commands.json','w').write(json.dumps(r, indent=1))
m.close()
