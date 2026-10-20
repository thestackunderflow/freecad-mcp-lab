"""Score every agent run the same way. Runs in the FreeCAD image (NumPy for the STL, freecadcmd for the STEP):
    docker run --rm --entrypoint /usr/bin/python3 -v "$PWD:/work" -w /work freecad-mcp-lab:1.1.4 claude-run/score.py
Writes out/runs/<arm>-<run>/score.json and out/runs/SCORES.json (+ a table on stdout)."""
import glob, json, os, re, subprocess, sys
sys.path.insert(0, '/work/tests')
import measure

RUNS = '/work/out/runs'
REBUILD = re.compile(r'Part\.make|makeBox|makeCylinder|newDocument|addObject\(\s*["\']Part::(Box|Cylinder)')
PARAM_EDIT = re.compile(r'setExpression|Spreadsheet|\.set\(\s*["\']|recompute')


def transcript(d):
    calls, errors, by_id, codes = [], [], {}, []
    p = os.path.join(d, 'transcript.jsonl')
    if not os.path.exists(p):
        return calls, errors, codes
    for ln in open(p, encoding='utf-8'):
        e = json.loads(ln)
        m = e['msg']
        if not isinstance(m, dict):
            continue
        if e['dir'] == 'client->server' and m.get('method') == 'tools/call':
            c = {'seq': e['seq'], 't': e['t'], 'tool': m['params']['name'], 'args': m['params'].get('arguments', {})}
            calls.append(c); by_id[m['id']] = c
            if c['tool'].startswith('execute_code'):
                codes.append((e['seq'], c['args'].get('code', '')))
        elif e['dir'] == 'server->client' and m.get('id') in by_id:
            res = m.get('result') or {}
            text = ' '.join(x.get('text', '') for x in res.get('content', []) if isinstance(x, dict))
            failed = 'error' in m or res.get('isError') or '"success": false' in text or '"ok": false' in text
            if failed:
                errors.append({'seq': e['seq'], 'tool': by_id[m['id']]['tool'], 'text': (text or json.dumps(m.get('error')))[:300]})
    return calls, errors, codes


def step_check(path):
    p = subprocess.run(['freecadcmd', '/work/tests/step_check.py'], env=dict(os.environ, STEP_FILE=path),
                       capture_output=True, text=True, timeout=120)
    line = next((l for l in p.stdout.splitlines() if l.startswith('STEP_CHECK ')), None)
    return json.loads(line[len('STEP_CHECK '):]) if line else {'error': (p.stdout + p.stderr)[-300:]}


def score_run(d):
    meta = json.load(open(os.path.join(d, 'run-meta.json')))
    out = {}
    try:
        out = json.load(open(os.path.join(d, 'claude-output.json')))
    except Exception as ex:
        out = {'error': str(ex)}
    calls, errors, codes = transcript(d)
    res = {'arm': meta['arm'], 'run': meta['run'], 'model': meta['model'], 'exit': meta['exit'], 'wall_s': meta['wall_s'],
           'claude_version': meta.get('claude_version'),
           'cost_usd': out.get('total_cost_usd'), 'num_turns': out.get('num_turns'), 'is_error': out.get('is_error'),
           'models_used': sorted((out.get('modelUsage') or {}).keys()),
           'tool_calls': len(calls), 'tools_used': sorted({c['tool'] for c in calls}), 'failed_calls': len(errors),
           'failures': errors, 'final_answer': (out.get('result') or '')[:2000]}
    for w in (80, 100):
        stl, step = f'{d}/bracket-{w}.stl', f'{d}/bracket-{w}.step'
        if os.path.exists(stl):
            m = measure.bracket(measure.read_stl(stl))
            res[f'w{w}'] = measure._plain({'measured': m, 'score': measure.score(m, w)})
        else:
            res[f'w{w}'] = {'missing': 'stl'}
        res[f'w{w}_step'] = measure._plain(step_check(step)) if os.path.exists(step) else {'missing': 'step'}
    # how the width change was made: calls after the first bracket-80 export
    exp80 = next((c['seq'] for c in calls if 'bracket-80' in json.dumps(c['args'])), None)
    later = [c for c in calls if exp80 and c['seq'] > exp80]
    if meta['arm'] == 'solidcraft':
        res['change_method'] = ('set_parameter' if any(c['tool'] == 'set_parameter' for c in later) else
                                'parameters.change' if any('parameters.change' in json.dumps(c['args']) for c in later) else
                                'other: read the transcript')
    else:
        # The agents export both widths from one script, so read the last script that succeeded as a whole: a
        # spreadsheet cell set to the new width, then recompute, with no geometry created after that line.
        failed = {f['seq'] - 1 for f in errors}  # a reply's seq follows its request's
        ok_codes = [c for s, c in codes if s not in failed]
        code = ok_codes[-1] if ok_codes else ''
        m = re.search(r'\.set\(\s*["\'][A-Z]+\d+["\']\s*,\s*(str\(w\)|["\']100)', code)
        res['change_method'] = ('spreadsheet parameter set, then recompute'
                                if m and 'recompute' in code[m.end():] and not REBUILD.search(code[m.end():])
                                else 'other: read the transcript') + ' (heuristic; checked by reading the code)'
    res['pass_80'] = bool(res['w80'].get('score', {}).get('pass'))
    res['pass_100'] = bool(res['w100'].get('score', {}).get('pass'))
    json.dump(res, open(os.path.join(d, 'score.json'), 'w'), indent=1)
    return res


if __name__ == '__main__':
    rows = [score_run(d) for d in sorted(glob.glob(f'{RUNS}/*-*')) if os.path.isdir(d) and os.path.exists(f'{d}/run-meta.json')]
    json.dump(rows, open(f'{RUNS}/SCORES.json', 'w'), indent=1)
    print(f"{'run':18} {'80':5} {'100':5} {'calls':5} {'fail':4} {'cost':7} {'wall':5} change")
    for r in rows:
        print(f"{r['arm'] + '-' + r['run']:18} {str(r['pass_80']):5} {str(r['pass_100']):5} {r['tool_calls']:5} "
              f"{r['failed_calls']:4} {str(r['cost_usd'])[:7]:7} {r['wall_s']:5} {r['change_method']}")
