"""STL measurer for the bracket: NumPy only, no CAD kernel, the same code for both programs' exports.

    python3 measure.py part.stl 80     -> JSON: measured dimensions + score against the spec at width 80

Spec (README): width W along X, base depth 60 (Y), height 50 (Z), plates 4 mm thick, two 5 mm holes through the back
plate, 40 mm apart, centred across the width, 35 mm above the bottom.
"""
import json, math, struct, sys
import numpy as np

TOL_MM = 0.1
TOL_VOL = 0.005
SPEC = {'depth': 60, 'height': 50, 'base_thickness': 4, 'back_thickness': 4,
        'hole_diameter': 5, 'hole_spacing': 40, 'hole_height': 35, 'holes_offset_from_centre': 0}


def read_stl(path):
    """Triangles as an (n, 3, 3) array; binary or ASCII STL."""
    raw = open(path, 'rb').read()
    if len(raw) >= 84:
        n = struct.unpack('<I', raw[80:84])[0]
        if 84 + 50 * n == len(raw):
            rec = np.frombuffer(raw[84:], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]), count=n)
            return rec['v'].astype(float).reshape(n, 3, 3)
    pts = [list(map(float, ln.split()[1:4])) for ln in raw.decode('ascii', 'replace').splitlines()
           if ln.strip().startswith('vertex')]
    return np.array(pts, float).reshape(-1, 3, 3)


def bbox(tris):
    v = np.asarray(tris).reshape(-1, 3)
    return np.array([v.min(0), v.max(0)])


def volume(tris):
    t = np.asarray(tris)
    return abs(np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6.0)


def fit_circle(xz):
    """Least-squares circle (Kasa) through 2-D points: (cx, cz, diameter)."""
    x, z = xz[:, 0], xz[:, 1]
    A = np.c_[2 * x, 2 * z, np.ones(len(x))]
    cx, cz, c = np.linalg.lstsq(A, x * x + z * z, rcond=None)[0]
    return cx, cz, 2 * math.sqrt(c + cx * cx + cz * cz)


def spec_volume(w):
    return w * 60 * 4 + w * 4 * 46 - 2 * math.pi * 2.5 ** 2 * 4


def bracket(tris):
    tris = np.asarray(tris)
    v = np.unique(np.round(tris.reshape(-1, 3), 6), axis=0)
    lo, hi = v.min(0), v.max(0)
    w, d, h = hi - lo
    base_t = v[v[:, 1] > lo[1] + 0.5 * d][:, 2].max() - lo[2]
    back_t = v[v[:, 2] > lo[2] + 0.5 * h][:, 1].max() - lo[1]
    m = {'width': w, 'depth': d, 'height': h, 'base_thickness': base_t, 'back_thickness': back_t,
         'volume': volume(tris), 'triangles': int(len(tris))}
    # hole-edge vertices: on the back plate, away from its outline
    sel = v[(v[:, 1] <= lo[1] + back_t + 1e-6) & (v[:, 2] > lo[2] + base_t + 1) & (v[:, 2] < hi[2] - 1)
            & (v[:, 0] > lo[0] + 1) & (v[:, 0] < hi[0] - 1)]
    mid = (lo[0] + hi[0]) / 2
    holes = []
    for side in (sel[sel[:, 0] < mid], sel[sel[:, 0] >= mid]):
        if len(side) >= 6:
            cx, cz, dia = fit_circle(side[:, [0, 2]])
            holes.append((cx, cz, dia))
    m['holes_found'] = len(holes)
    if len(holes) == 2:
        m['hole_diameters'] = [holes[0][2], holes[1][2]]
        m['hole_spacing'] = holes[1][0] - holes[0][0]
        m['hole_height'] = (holes[0][1] + holes[1][1]) / 2 - lo[2]
        m['holes_offset_from_centre'] = (holes[0][0] + holes[1][0]) / 2 - mid
    return m


def score(m, w):
    """Compare a measurement with the spec at width w: {'pass', 'failures'}."""
    fails = []
    if abs(m.get('width', -1) - w) > TOL_MM:
        fails.append('width')
    for k in ('depth', 'height', 'base_thickness', 'back_thickness', 'hole_spacing', 'hole_height', 'holes_offset_from_centre'):
        if k not in m or abs(m[k] - SPEC[k]) > TOL_MM:
            fails.append(k)
    ds = m.get('hole_diameters') or []
    if len(ds) != 2 or any(abs(x - SPEC['hole_diameter']) > TOL_MM for x in ds):
        fails.append('hole_diameters')
    if 'volume' in m and abs(m['volume'] - spec_volume(w)) > TOL_VOL * spec_volume(w):
        fails.append('volume')
    return {'pass': not fails, 'failures': fails}


def _plain(o):
    if isinstance(o, dict):
        return {k: _plain(x) for k, x in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(x) for x in o]
    return round(float(o), 4) if isinstance(o, (float, np.floating)) else o


if __name__ == '__main__':
    path, w = sys.argv[1], float(sys.argv[2])
    m = bracket(read_stl(path))
    print(json.dumps(_plain({'file': path, 'spec_width': w, 'spec_volume': spec_volume(w), 'measured': m, 'score': score(m, w)}), indent=1))
