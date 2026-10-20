"""The measurer, checked on synthetic meshes with known answers before it scores anything."""
import math, os, struct, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure


def box_tris(x0, y0, z0, x1, y1, z1):
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return [v[list(t)] for t in f]


def write_stl(path, tris, binary=True):
    if binary:
        with open(path, 'wb') as fh:
            fh.write(b'\0' * 80 + struct.pack('<I', len(tris)))
            for t in tris:
                fh.write(struct.pack('<3f', 0, 0, 0) + struct.pack('<9f', *np.asarray(t).ravel()) + b'\0\0')
    else:
        with open(path, 'w') as fh:
            fh.write('solid t\n')
            for t in tris:
                fh.write(' facet normal 0 0 0\n  outer loop\n')
                for p in t:
                    fh.write(f'   vertex {p[0]} {p[1]} {p[2]}\n')
                fh.write('  endloop\n endfacet\n')
            fh.write('endsolid t\n')


class TestMeasure:
    def test_box_volume_and_bbox_binary_and_ascii(self):
        for binary in (True, False):
            p = os.path.join(tempfile.mkdtemp(), 'b.stl')
            write_stl(p, box_tris(0, 0, 0, 80, 60, 4), binary)
            tris = measure.read_stl(p)
            assert abs(measure.volume(tris) - 80 * 60 * 4) < 1e-6
            assert np.allclose(measure.bbox(tris), [[0, 0, 0], [80, 60, 4]])

    def test_circle_fit(self):
        pts = [(30 + 2.5 * math.cos(a), 35 + 2.5 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
        cx, cz, d = measure.fit_circle(np.array(pts))
        assert abs(cx - 30) < 1e-9 and abs(cz - 35) < 1e-9 and abs(d - 5) < 1e-9

    def test_bracket_features_from_vertices(self):
        # Two plates (no holes in the mesh) plus hole-edge vertices injected as degenerate triangles on the y=0 face.
        W = 80
        tris = box_tris(0, 0, 0, W, 60, 4) + box_tris(0, 0, 4, W, 4, 50)
        for cx in (W / 2 - 20, W / 2 + 20):
            ring = [(cx + 2.5 * math.cos(a), 0.0, 35 + 2.5 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 32, endpoint=False)]
            for i in range(len(ring)):
                tris.append(np.array([ring[i], ring[(i + 1) % len(ring)], ring[i]]))
        m = measure.bracket(tris)
        assert abs(m['width'] - 80) < 1e-6 and abs(m['depth'] - 60) < 1e-6 and abs(m['height'] - 50) < 1e-6
        assert abs(m['base_thickness'] - 4) < 1e-6 and abs(m['back_thickness'] - 4) < 1e-6
        assert [round(d, 6) for d in m['hole_diameters']] == [5, 5]
        assert abs(m['hole_spacing'] - 40) < 1e-6 and abs(m['hole_height'] - 35) < 1e-6
        assert abs(m['holes_offset_from_centre']) < 1e-6

    def test_score_against_spec(self):
        ok = {'width': 80, 'depth': 60, 'height': 50, 'base_thickness': 4, 'back_thickness': 4,
              'hole_diameters': [5, 5], 'hole_spacing': 40, 'hole_height': 35, 'holes_offset_from_centre': 0,
              'volume': 33762.9}
        s = measure.score(ok, 80)
        assert s['pass'] and not s['failures']
        bad = dict(ok, holes_offset_from_centre=10)
        s = measure.score(bad, 80)
        assert not s['pass'] and s['failures'] == ['holes_offset_from_centre']

    def test_analytic_volume(self):
        assert abs(measure.spec_volume(80) - 33762.92) < 0.01
        assert abs(measure.spec_volume(100) - 42242.92) < 0.01
