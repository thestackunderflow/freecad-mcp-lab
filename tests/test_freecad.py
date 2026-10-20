"""FreeCAD MCP (neka-nat/freecad-mcp v0.1.27) on FreeCAD 1.1.4, no AI: the server answers, lists its documented tools,
and a fixed script sent through execute_code builds the reference bracket that the measurer then checks.
Run inside the FreeCAD image (its start.sh has FreeCAD's RPC server up before pytest starts)."""
import base64, json, os, subprocess, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure
from mcp_client import McpClient, save
import mcp_client

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'freecad')  # set in the fixture: modules share mcp_client
OUT = '/lab/out'
DOCUMENTED = {'create_document', 'list_documents', 'reload_document', 'create_object', 'edit_object', 'delete_object',
              'get_objects', 'get_object', 'get_view', 'execute_code', 'execute_code_async', 'get_async_status',
              'execute_code_headless', 'get_rpc_status', 'insert_part_from_library', 'get_parts_list', 'run_fem_analysis'}

REF_SCRIPT = '''
import FreeCAD as App, Part, MeshPart
W = {w}
doc = App.newDocument("RefBracket{w}")
s = Part.makeBox(W, 60, 4).fuse(Part.makeBox(W, 4, 50))
for cx in (W / 2 - 20, W / 2 + 20):
    s = s.cut(Part.makeCylinder(2.5, 4, App.Vector(cx, 0, 35), App.Vector(0, 1, 0)))
s = s.removeSplitter()
o = doc.addObject("Part::Feature", "Bracket"); o.Shape = s
doc.recompute()
Part.export([o], "{out}/ref-freecad-{w}.step")
MeshPart.meshFromShape(Shape=s, LinearDeflection=0.01, AngularDeflection=0.05).write("{out}/ref-freecad-{w}.stl")
print("volume", s.Volume)
'''


@pytest.fixture(scope='module')
def mcp():
    mcp_client.OUT = OUT_DIR
    os.makedirs(OUT_DIR, exist_ok=True)
    c = McpClient(['freecad-mcp', '--only-text-feedback'])
    c.start()
    yield c
    c.close()


def test_0_versions(mcp):
    sha = open('/opt/freecad/FreeCAD_1.1.4-Linux-x86_64-py311.AppImage-SHA256.txt').read()
    assert 'FreeCAD_1.1.4-Linux-x86_64-py311.AppImage' in sha
    pip = subprocess.run(['/opt/mcp/bin/pip', 'show', 'freecad-mcp'], capture_output=True, text=True).stdout
    assert 'Version: 0.1.27' in pip
    status = mcp.text_json(mcp.call_tool('get_rpc_status', {}))
    save('00_rpc_status', status)
    assert status['addon_version'] == '0.1.27' and status['version_check'] == 'ok'
    assert status['rpc_server'] == 'running' and status['gui_dispatch']['state'] == 'healthy'


def test_1_documented_tools(mcp):
    tools = mcp.request('tools/list', {})['tools']
    save('01_tools_list', {'tools': tools})
    assert DOCUMENTED <= {t['name'] for t in tools}


@pytest.mark.parametrize('w', [80, 100])
def test_2_reference_bracket_via_execute_code(mcp, w):
    r = mcp.call_tool('execute_code', {'code': REF_SCRIPT.format(w=w, out=OUT)})
    save(f'02_execute_code_ref_{w}', r)
    assert not r.get('isError'), mcp.text(r)
    m = measure.bracket(measure.read_stl(f'{OUT}/ref-freecad-{w}.stl'))
    save(f'02_measure_ref_{w}', measure._plain({'measured': m, 'score': measure.score(m, w)}))
    assert measure.score(m, w)['pass'], (m, measure.score(m, w))


def test_3_step_reread_by_freecadcmd(mcp):
    for w in (80, 100):
        p = subprocess.run(['freecadcmd', '/work/tests/step_check.py'],
                           env=dict(os.environ, STEP_FILE=f'{OUT}/ref-freecad-{w}.step'), capture_output=True, text=True)
        line = next(l for l in p.stdout.splitlines() if l.startswith('STEP_CHECK '))
        res = json.loads(line[len('STEP_CHECK '):])
        save(f'03_step_check_{w}', res)
        assert [round(x, 3) for x in res['size']] == [w, 60, 50]
        assert abs(res['volume'] - measure.spec_volume(w)) < 0.001 * measure.spec_volume(w)


def test_4_get_view_returns_a_png(mcp):
    r = mcp.call_tool('get_view', {'view_name': 'Isometric', 'width': 960, 'height': 600})
    img = next(c for c in r['content'] if c.get('type') == 'image')
    png = base64.b64decode(img['data'])
    assert png[:8] == b'\x89PNG\r\n\x1a\n'
    open(os.path.join(mcp_client.OUT, '04_view_ref.png'), 'wb').write(png)
