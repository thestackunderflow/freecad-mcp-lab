"""Build the replay fixtures from the CLEAN agent runs only (out/runs/), never from the pilot folders.
    python tests/fixtures/make_fixtures.py
sc3_session.json: every state-changing call of solidcraft-3 (the run with the "ok" cut that removed nothing), in order,
with the logged reply, so the no-AI replay can check it gets the same answers.
fc1_session.json: freecad-1's first program (failed: NULL shape) and its follow-up listing of the document.
fc3_script.json: freecad-3's one program (the whole job), for the finished-part frame."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, '..', '..', 'out', 'runs')
MUTATING = {'batch', 'execute', 'set_parameter', 'new_design', 'undo', 'redo'}


def session(run):
    rows = [json.loads(l) for l in open(os.path.join(RUNS, run, 'transcript.jsonl'), encoding='utf-8')]
    out = []
    for i, e in enumerate(rows):
        m = e['msg']
        if isinstance(m, dict) and m.get('method') == 'tools/call':
            rep = next(x for x in rows[i + 1:] if x['dir'] == 'server->client' and isinstance(x['msg'], dict) and x['msg'].get('id') == m['id'])
            res = rep['msg'].get('result', {})
            out.append({'seq': e['seq'], 'tool': m['params']['name'], 'arguments': m['params'].get('arguments', {}),
                        'reply_is_error': bool(res.get('isError')),
                        'reply_text': '\n'.join(c.get('text', '') for c in res.get('content', []) if c.get('type') == 'text')})
    return out


def dump(name, obj):
    with open(os.path.join(HERE, name), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write('\n')


if __name__ == '__main__':
    sc3 = [c for c in session('solidcraft-3') if c['tool'] in MUTATING]
    dump('sc3_session.json', {'source': 'out/runs/solidcraft-3/transcript.jsonl (clean run, 19 Oct 2026): every state-changing call, in order',
                              'noop_cut_seq': 30, 'calls': sc3})
    fc1 = session('freecad-1')
    dump('fc1_session.json', {'source': 'out/runs/freecad-1/transcript.jsonl (clean run, 19 Oct 2026): seq 18 the first program (NULL shape), seq 20 the listing',
                              'calls': [c for c in fc1 if c['seq'] in (18, 20)]})
    fc3 = session('freecad-3')
    dump('fc3_script.json', {'source': 'out/runs/freecad-3/transcript.jsonl seq 18 (clean run, 19 Oct 2026): the whole job in one program',
                             'code': fc3[0]['arguments']['code']})
    print('sc3 calls', [(c['seq'], c['tool']) for c in sc3])
