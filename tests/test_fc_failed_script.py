"""Replay, with no AI, the clean run freecad-1's first program (it failed: NULL shape) and its follow-up listing.
The program created every object, then its check hit the empty final shape. execute_code doesn't wrap the code in an
undo transaction, so nothing is undone: the plates stay valid, both holes stay Invalid (a unitless width plus 20 mm),
and the holes-fuse and the cut stay Touched: never computed. Source: tests/fixtures/fc1_session.json."""
import json, os, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_client import McpClient, save
import mcp_client

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'freecad-failed-script')  # set in the fixture: modules share mcp_client
FIX = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'fc1_session.json'), encoding='utf-8'))


@pytest.fixture(scope='module')
def mcp():
    mcp_client.OUT = OUT_DIR
    os.makedirs(OUT_DIR, exist_ok=True)
    c = McpClient(['freecad-mcp', '--only-text-feedback'])
    c.start()
    yield c
    c.close()


def test_first_program_fails_with_a_null_shape(mcp):
    first, listing = FIX['calls']
    r = mcp.call_tool('execute_code', {'code': first['arguments']['code']})
    save('failed_program', r)
    assert r.get('isError') and 'NULL shape' in mcp.text(r)
    assert first['reply_is_error'] and 'NULL shape' in first['reply_text']


def test_nothing_is_undone(mcp):
    listing = FIX['calls'][1]
    r = mcp.call_tool('execute_code', {'code': listing['arguments']['code']})
    save('listing_after_failure', r)
    out = mcp.text(r)
    for line in ("BasePlate ['Up-to-date'] True", "BackPlate ['Up-to-date'] True",
                 "Hole1 ['Touched', 'Invalid'] False", "Hole2 ['Touched', 'Invalid'] False",
                 "Holes ['Touched'", "WallBracket ['Touched'"):   # 'Expanded' is only the GUI tree's state
        assert line in out, line
        assert line in listing['reply_text'], line      # the same as the logged run
