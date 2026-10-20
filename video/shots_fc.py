# FreeCAD frame for the video, no AI: the clean run freecad-3's one program (tests/fixtures/fc3_script.json), finished part.
import base64, json, sys
sys.path.insert(0, '/work/tests')
from mcp_client import McpClient
m = McpClient(["freecad-mcp", "--only-text-feedback"]); m.start()
def view(name, **kw):
    r = m.call_tool("get_view", {"view_name": "Isometric", "width": 1080, "height": 1080, **kw})
    img = next(c for c in r["content"] if c.get("type") == "image")
    open(f"/work/video/frames/{name}.png", "wb").write(base64.b64decode(img["data"]))
    print(name, "ok")
r = m.call_tool("execute_code", {"code": json.load(open('/work/tests/fixtures/fc3_script.json'))['code']})
print("run3:", m.text(r)[:300])
m.call_tool("execute_code", {"code": "import FreeCADGui as G\nfor o in App.ActiveDocument.Objects:\n    o.ViewObject.Visibility = (o.Name == 'Bracket')\nG.SendMsgToActiveView('ViewFit')"})
view("fc-finished-iso")
m.close()
