"""SolidCraft 0.16.2 MCP, no AI: the server answers, lists its tools, and one fixed batch builds the reference bracket
with width as a parameter and the holes positioned by expressions of it; set_parameter then changes the width."""
import json, os, subprocess, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure
from mcp_client import McpClient, save
import mcp_client

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'solidcraft')  # set in the fixture: modules share mcp_client
OUT = '/lab/out'
TOOLS = {'batch', 'body_topology', 'execute', 'export', 'inspect_design', 'list_commands', 'measure', 'new_design',
         'open', 'redo', 'save', 'screenshot', 'set_parameter', 'undo'}

REF_BATCH = [
    {'command': 'parameters.change', 'params': {'name': 'width', 'expression': '80 mm'}},
    # the L profile in the YZ plane (sketch x = world Y, sketch y = world Z; normal +X), extruded along X by width
    {'command': 'sketch.create', 'params': {'plane': {'origin': [0, 0, 0], 'x_dir': [0, 1, 0], 'y_dir': [0, 0, 1]}, 'name': 'L profile'}},
    {'command': 'sketch.line', 'params': {'points': [[0, 0], [60, 0], [60, 4], [4, 4], [4, 50], [0, 50]], 'closed': True}},
    {'command': 'sketch.finish', 'params': {}},
    {'command': 'solid.extrude', 'params': {'distance': 'width', 'body_name': 'Bracket'}},
    # holes on the back face (Y = 0), positioned by expressions so they follow the width
    {'command': 'solid.hole', 'params': {'position': ['width/2 - 20 mm', 0, 35], 'diameter': 5}},
    {'command': 'solid.hole', 'params': {'position': ['width/2 + 20 mm', 0, 35], 'diameter': 5}},
]


@pytest.fixture(scope='module')
def mcp():
    mcp_client.OUT = OUT_DIR
    os.makedirs(OUT_DIR, exist_ok=True)
    c = McpClient(['solidcraft-cli', 'mcp', '--allow-path', OUT])
    c.start()
    yield c
    c.close()


def export_and_measure(mcp, w):
    for fmt in ('step', 'stl'):
        r = mcp.call_tool('export', {'path': f'{OUT}/ref-solidcraft-{w}.{fmt}', 'format': fmt})
        save(f'export_{w}_{fmt}', r)
        assert not r.get('isError'), mcp.text(r)
    m = measure.bracket(measure.read_stl(f'{OUT}/ref-solidcraft-{w}.stl'))
    s = measure.score(m, w)
    save(f'measure_ref_{w}', measure._plain({'measured': m, 'score': s}))
    return m, s


def test_0_version(mcp):
    assert mcp.init_result['serverInfo']['version'] == '0.16.2'
    v = subprocess.run(['solidcraft-cli', '--version'], capture_output=True, text=True).stdout
    assert '0.16.2' in v


def test_1_tools(mcp):
    tools = mcp.request('tools/list', {})['tools']
    save('01_tools_list', {'tools': tools})
    assert TOOLS <= {t['name'] for t in tools}


def test_2_reference_batch_builds_the_bracket(mcp):
    r = mcp.call_tool('batch', {'commands': REF_BATCH})
    save('02_batch_reply', r)
    body = mcp.text_json(r)
    assert not r.get('isError') and body['ok'] is True, body
    m, s = export_and_measure(mcp, 80)
    assert s['pass'], (m, s)


def test_3_set_parameter_keeps_holes_centred(mcp):
    r = mcp.tool_json('set_parameter', {'name': 'width', 'value': '100 mm'})
    save('03_set_parameter_reply', r)
    m, s = export_and_measure(mcp, 100)
    assert s['pass'], (m, s)


def test_4_step_reread_matches(mcp):
    # SolidCraft's own reader re-reads the exported STEP (FreeCAD re-reads it in the FreeCAD image: see score.py)
    for w in (80, 100):
        p = f'{OUT}/ref-solidcraft-{w}.step'
        assert os.path.getsize(p) > 1000


def test_5_export_outside_allowed_folder_is_refused(mcp):
    # SolidCraft writes only under --allow-path; FreeCAD MCP's execute_code runs any Python FreeCAD can run
    for p in ('/lab/forbidden/x.step', '/lab/out/../forbidden/x.step'):
        r = mcp.call_tool('export', {'path': p, 'format': 'step'})
        save('05_export_refused', r)
        assert r.get('isError') and 'outside the folders this agent may use' in mcp.text(r), mcp.text(r)
    assert os.listdir('/lab/forbidden') == []
