import json, sys
sys.path.insert(0, '/work/tests')
from mcp_client import McpClient
F = json.load(open('/work/tests/fixtures/sc1_noop_cut.json'))
m = McpClient(["solidcraft-cli", "mcp", "--allow-path", "/lab/out"]); m.start()
for c in F['calls'][:2]:
    m.call_tool(c['tool'], c['arguments'])
d = m.text_json(m.call_tool("inspect_design", {"measure": False, "sketches": True}))
sk = d.get('sketches') or d
print(json.dumps(sk, indent=0)[:2500])
