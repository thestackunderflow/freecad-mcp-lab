# SolidCraft frames for the video, no AI: replay the clean run solidcraft-3 (tests/fixtures/sc3_session.json) up to the
# cut that said ok and changed nothing (seq 30), shoot it, then replay the agent's fix (to seq 56) and shoot again.
import base64, json, sys
sys.path.insert(0, '/work/tests')
from mcp_client import McpClient
F = json.load(open('/work/tests/fixtures/sc3_session.json', encoding='utf-8'))
m = McpClient(["solidcraft-cli", "mcp", "--allow-path", "/lab/out"]); m.start()
def shot(name, view):
    r = m.call_tool("screenshot", {"view": view, "width": 1080, "height": 1080})
    img = next(c for c in r["content"] if c.get("type") == "image")
    open(f"/work/video/frames/{name}.png", "wb").write(base64.b64decode(img["data"]))
    print(name, m.text(r)[:120])
for c in F['calls']:
    if c['seq'] > F['noop_cut_seq']: break
    m.call_tool(c['tool'], c['arguments'])
shot("sc-noop-cut-iso", "iso"); shot("sc-noop-cut-front", "front")
for c in F['calls']:
    if F['noop_cut_seq'] < c['seq'] <= 56: m.call_tool(c['tool'], c['arguments'])
shot("sc-fixed-iso", "iso")
m.close()
