"""Replay, with no AI, every state-changing call of the clean run solidcraft-3, in order, and check SolidCraft gives the
same answers: the batch that failed at step 4 undoes its 3 finished steps; the cut at seq 30 says ok but changes no body,
because on the "XZ" plane a sketch's y axis is world -Z (the circles sit at Z = -35, below the part); the agent's later
fix (circles redrawn at sketch y = -35) makes both holes. Source: tests/fixtures/sc3_session.json (make_fixtures.py)."""
import json, math, os, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_client import McpClient, save
import mcp_client

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'solidcraft-noop')  # set in the fixture: modules share mcp_client
FIX = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'sc3_session.json'), encoding='utf-8'))
PLAIN_L = 80 * 60 * 4 + 80 * 4 * 46               # 33,920 mm3: the L with no holes
WITH_HOLES = PLAIN_L - 2 * math.pi * 2.5 ** 2 * 4


@pytest.fixture(scope='module')
def mcp():
    mcp_client.OUT = OUT_DIR
    os.makedirs(OUT_DIR, exist_ok=True)
    c = McpClient(['solidcraft-cli', 'mcp', '--allow-path', '/lab/out'])
    c.start()
    yield c
    c.close()


def replay(mcp, until=None, start=0):
    got = []
    for call in FIX['calls'][start:]:
        if until is not None and call['seq'] > until:
            break
        r = mcp.call_tool(call['tool'], call['arguments'])
        got.append((call, r, mcp.text_json(r)))
    return got


def logged(call):
    try:
        return json.loads(call['reply_text'])
    except json.JSONDecodeError:
        return call['reply_text']


def test_replay_up_to_the_cut_matches_the_log(mcp):
    got = replay(mcp, until=FIX['noop_cut_seq'])
    save('replay_to_cut', [{'seq': c['seq'], 'reply': j} for c, _, j in got])
    for call, r, j in got:
        assert bool(r.get('isError')) == call['reply_is_error'], call['seq']
        if isinstance(j, dict) and 'ok' in j:
            assert j['ok'] == logged(call)['ok'], call['seq']
    # seq 20: three steps done, step 4 failed, all three undone
    j20 = next(j for c, _, j in got if c['seq'] == 20)
    assert j20['ok'] is False and j20['failed']['index'] == 3 and j20['rolled_back'] is True and j20['undone'] == 3
    # seq 30: the cut reports ok, no warning, and changes no body
    j30 = got[-1][2]
    ext = j30['results'][-1]
    assert j30['ok'] is True and ext['name'] == 'Extrude1' and ext['changed_bodies'] == [] and ext['warning'] is None


def test_why_the_cut_missed(mcp):
    sk = mcp.tool_json('inspect_design', {'measure': False, 'sketches': True})['sketches'][-1]
    save('replay_sketch', sk)
    assert sk['plane']['y_dir'] == [0.0, 0.0, -1.0]
    centres = sorted(p['world'] for p in sk['points'] if p['id'].endswith('.center'))
    assert centres == [pytest.approx([20, 0, -35]), pytest.approx([60, 0, -35])]
    m = mcp.tool_json('measure', {'body': 'Bracket'})['bodies'][0]
    save('replay_measure_after_cut', m)
    assert m['faces'] == 8 and m['volume_mm3'] == pytest.approx(PLAIN_L)


def test_the_agents_fix_makes_the_holes(mcp):
    i = next(k for k, c in enumerate(FIX['calls']) if c['seq'] > FIX['noop_cut_seq'])
    got = replay(mcp, until=56, start=i)
    for call, r, j in got:
        assert bool(r.get('isError')) == call['reply_is_error'], call['seq']
    m = mcp.tool_json('measure', {'body': 'Bracket'})['bodies'][0]
    save('replay_measure_after_fix', m)
    assert m['volume_mm3'] == pytest.approx(WITH_HOLES, rel=1e-4) and m['faces'] > 8
