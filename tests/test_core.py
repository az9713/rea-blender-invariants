import math
from pathlib import Path
import tempfile
import unittest
from blender_invariants.core import Contract, asset_identity, compare, equivalent, measure


def cube(scale=1):
    vertices = [[scale*x, scale*y, scale*z] for x, y, z in
                [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    polygons = [[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
    edges = sorted({tuple(sorted((a,b))) for p in polygons for a,b in zip(p,p[1:]+p[:1])})
    triangles = [[p[0],p[i],p[i+1]] for p in polygons for i in range(1,len(p)-1)]
    return vertices, edges, polygons, triangles


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.base = measure(*cube())

    def test_closed_cube_area_volume_and_euler(self):
        self.assertEqual(self.base['unsupported'], [])
        self.assertAlmostEqual(self.base['volume'],8)
        self.assertAlmostEqual(self.base['area'],24)
        self.assertEqual(self.base['euler'],2)

    def test_scale_laws_expose_scientific_violation(self):
        result = compare(self.base, measure(*cube(2)), Contract())
        self.assertFalse(result['passes'])
        self.assertAlmostEqual(result['ratios']['volume'],8)
        self.assertAlmostEqual(result['ratios']['area'],4)
        self.assertEqual(len(result['violations']),2)

    def test_open_mesh_never_claims_volume(self):
        v,e,p,t = cube();p=p[:-1];t=t[:-2]
        result=measure(v,e,p,t)
        self.assertIsNone(result['volume'])
        self.assertIn('open_nonmanifold_or_loose_mesh',result['unsupported'])

    def test_inconsistent_winding_refuses_volume(self):
        v,e,p,t=cube();p[0]=p[0][::-1]
        result=measure(v,e,p,t)
        self.assertIsNone(result['volume'])
        self.assertIn('inconsistent_winding',result['unsupported'])

    def test_disconnected_solid_volumes_do_not_cancel(self):
        v,e,p,t=cube();v2=[[x+5,y,z] for x,y,z in v]
        shifted=lambda group:[[i+8 for i in item] for item in group]
        result=measure(v+v2,e+shifted(e),p+shifted([f[::-1] for f in p]),t+shifted([f[::-1] for f in t]))
        self.assertEqual(result['components'],2)
        self.assertAlmostEqual(result['volume'],16)

    def test_nonfinite_vertices_rejected(self):
        for value in (math.nan,math.inf,-math.inf):
            v,e,p,t=cube();v[0][0]=value
            with self.assertRaises(ValueError):measure(v,e,p,t)

    def test_duplicate_edges_and_bad_indices_rejected(self):
        v,e,p,t=cube()
        with self.assertRaises(ValueError):measure(v,e+[e[0]],p,t)
        with self.assertRaises(ValueError):measure(v,e,p,[[0,1,999]])

    def test_invalid_intervals_and_tolerance_rejected(self):
        for contract in (Contract(volume_ratio_min=2,volume_ratio_max=1),Contract(tolerance=math.nan),Contract(tolerance=.5)):
            with self.assertRaises(ValueError):contract.validate()

    def test_equivalence_is_tolerant_but_topology_exact(self):
        actual=dict(self.base,area=self.base['area']+1e-7)
        self.assertTrue(equivalent(self.base,actual)['matches'])
        self.assertFalse(equivalent(self.base,dict(actual,faces=99))['matches'])
        self.assertFalse(equivalent(self.base,dict(actual,area=25))['matches'])

    def test_volume_support_not_silently_equivalent(self):
        self.assertFalse(equivalent(self.base,dict(self.base,volume=None))['matches'])

    def test_asset_hash_changes_and_missing_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'cache.bin';p.write_bytes(b'one')
            a=asset_identity(p,folder);p.write_bytes(b'two');b=asset_identity(p,folder)
            self.assertNotEqual(a['sha256'],b['sha256'])
            self.assertEqual(asset_identity(Path(folder)/'missing',folder)['status'],'missing')

    def test_outside_asset_not_read_and_size_cap(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'scope';root.mkdir()
            outside=Path(folder)/'not-read';outside.write_bytes(b'outside')
            self.assertEqual(asset_identity(outside,root)['status'],'outside_workspace_not_read')
            inside=root/'large';inside.write_bytes(b'12345')
            self.assertEqual(asset_identity(inside,root,max_bytes=4)['status'],'too_large_not_hashed')


if __name__=='__main__':unittest.main()
