# SPDX-License-Identifier: GPL-2.0-or-later
"""Dependency-free geometry checks and invariant contracts, never a history engine."""
from dataclasses import dataclass, asdict
import hashlib
import json
import math
from pathlib import Path


def _finite(values):
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise ValueError('Non-finite or nonnumeric geometry')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                     separators=(',', ':')).encode()).hexdigest()


def measure(vertices, edges, polygons, triangles):
    if not vertices:
        raise ValueError('Empty evaluated mesh')
    for vertex in vertices:
        if len(vertex) != 3:
            raise ValueError('Expected 3D vertices')
        _finite(vertex)
    n = len(vertices)
    for group, size in ((edges, 2), (triangles, 3)):
        for item in group:
            if len(item) != size or len(set(item)) != size or any(type(i) is not int or i < 0 or i >= n for i in item):
                raise ValueError('Malformed mesh indices')
    parents = list(range(n))

    def find(a):
        while parents[a] != a:
            parents[a] = parents[parents[a]]
            a = parents[a]
        return a

    canonical_edges = {tuple(sorted(e)) for e in edges}
    if len(canonical_edges) != len(edges):
        raise ValueError('Duplicate edges')
    for a, b in edges:
        parents[find(b)] = find(a)
    incidence, winding = {}, {}
    for polygon in polygons:
        if len(polygon) < 3 or len(set(polygon)) != len(polygon) or any(type(i) is not int or i < 0 or i >= n for i in polygon):
            raise ValueError('Malformed polygon')
        for a, b in zip(polygon, polygon[1:] + polygon[:1]):
            edge = tuple(sorted((a, b)))
            incidence[edge] = incidence.get(edge, 0) + 1
            winding[edge] = winding.get(edge, 0) + (1 if a < b else -1)
    flags = []
    boundary_edges = sum(incidence.get(e, 0) == 1 for e in canonical_edges)
    if set(incidence) != canonical_edges:
        flags.append('polygon_edge_mismatch')
    if any(incidence.get(e, 0) != 2 for e in canonical_edges):
        flags.append('open_nonmanifold_or_loose_mesh')
    if any(winding[e] != 0 for e in incidence if incidence[e] == 2):
        flags.append('inconsistent_winding')
    minimum = [min(v[a] for v in vertices) for a in range(3)]
    maximum = [max(v[a] for v in vertices) for a in range(3)]
    area, signed_volumes = 0., {}
    origin = vertices[0]
    for triangle in triangles:
        a, b, c = [vertices[i] for i in triangle]
        ab, ac = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        cross = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]]
        triangle_area = math.sqrt(sum(v * v for v in cross)) / 2
        if not math.isfinite(triangle_area):
            raise ValueError('Derived area is non-finite')
        if triangle_area <= 1e-15:
            flags.append('degenerate_triangle')
        area += triangle_area
        p, q, r = [[v[i] - origin[i] for i in range(3)] for v in (a, b, c)]
        qr = [q[1] * r[2] - q[2] * r[1], q[2] * r[0] - q[0] * r[2], q[0] * r[1] - q[1] * r[0]]
        volume = sum(p[i] * qr[i] for i in range(3)) / 6
        component = find(triangle[0])
        signed_volumes[component] = signed_volumes.get(component, 0.) + volume
    _finite([area, *signed_volumes.values()])
    volume = None if flags else sum(abs(v) for v in signed_volumes.values())
    if volume is not None:
        _finite([volume])
    return {'vertices': n, 'edges': len(edges), 'faces': len(polygons), 'triangles': len(triangles),
            'components': len({find(i) for i in range(n)}), 'euler': n - len(edges) + len(polygons),
            'boundary_edges': boundary_edges, 'area': area, 'volume': volume,
            'bounds_min': minimum, 'bounds_max': maximum, 'unsupported': sorted(set(flags)),
            'mesh_digest': digest({'vertices': vertices, 'edges': edges, 'polygons': polygons})}


@dataclass(frozen=True)
class Contract:
    volume_ratio_min: float = .8
    volume_ratio_max: float = 1.2
    area_ratio_min: float = .8
    area_ratio_max: float = 1.2
    preserve_topology: bool = True
    require_closed: bool = True
    tolerance: float = 1e-6

    def validate(self):
        values = [self.volume_ratio_min, self.volume_ratio_max, self.area_ratio_min,
                  self.area_ratio_max, self.tolerance]
        _finite(values)
        if any(v <= 0 for v in values) or self.volume_ratio_min > self.volume_ratio_max or self.area_ratio_min > self.area_ratio_max:
            raise ValueError('Invalid invariant intervals')
        if self.tolerance >= .01:
            raise ValueError('Tolerance too permissive')


def compare(before, after, contract):
    contract.validate()
    violations, ratios = [], {}
    if contract.require_closed and (before['unsupported'] or after['unsupported']):
        violations.append('Closed consistently wound mesh required; volume is unsupported')
    for metric in ('area', 'volume'):
        old, new = before[metric], after[metric]
        if old is None or new is None or old <= 0:
            ratios[metric] = None
            if metric == 'volume':
                violations.append('Volume ratio cannot be established')
            continue
        ratio = new / old
        _finite([ratio])
        ratios[metric] = ratio
        low, high = getattr(contract, metric + '_ratio_min'), getattr(contract, metric + '_ratio_max')
        if not low - contract.tolerance <= ratio <= high + contract.tolerance:
            violations.append(f'{metric} ratio {ratio:.6g} violates [{low:.6g}, {high:.6g}]')
    topology = {key: after[key] - before[key] for key in ('vertices', 'edges', 'faces', 'components', 'euler')}
    if contract.preserve_topology and any(topology.values()):
        violations.append('Declared topology preservation failed')
    return {'passes': not violations, 'violations': violations, 'ratios': ratios,
            'topology_delta': topology, 'bounds_before': [before['bounds_min'], before['bounds_max']],
            'bounds_after': [after['bounds_min'], after['bounds_max']],
            'causality_limit': 'Measured deltas and declared edits are evidence of association. Isolated replay tests sufficiency for the recorded result, not exclusive causation.'}


def equivalent(expected, actual, tolerance=1e-6):
    _finite([tolerance])
    if tolerance <= 0 or tolerance >= .01:
        raise ValueError('Invalid equivalence tolerance')
    failures = []
    for key in ('vertices', 'edges', 'faces', 'triangles', 'components', 'euler', 'boundary_edges'):
        if expected[key] != actual[key]:
            failures.append(key + ' differs')
    for key in ('area', 'volume'):
        a, b = expected[key], actual[key]
        if a is None or b is None:
            if a != b:
                failures.append(key + ' support differs')
        else:
            _finite([a, b])
            if not math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance):
                failures.append(key + ' differs beyond tolerance')
    for key in ('bounds_min', 'bounds_max'):
        _finite(expected[key] + actual[key])
        if any(not math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance) for a, b in zip(expected[key], actual[key])):
            failures.append(key + ' differs beyond tolerance')
    if expected['unsupported'] != actual['unsupported']:
        failures.append('unsupported flags differ')
    return {'matches': not failures, 'failures': failures, 'tolerance': tolerance,
            'scope': 'Mesh counts, connectivity summary, area, volume and axis-aligned bounds; not full mesh/render equivalence'}


def asset_identity(path, allowed_root, max_bytes=64 * 1024 * 1024):
    root = Path(allowed_root).resolve()
    target = Path(path).resolve()
    if not target.is_relative_to(root):
        return {'status': 'outside_workspace_not_read', 'path': str(path)}
    relative = target.relative_to(root).as_posix()
    if not target.is_file():
        return {'status': 'missing', 'path': relative}
    size = target.stat().st_size
    if size > max_bytes:
        return {'status': 'too_large_not_hashed', 'path': relative, 'size': size}
    return {'status': 'hashed', 'path': relative, 'size': size,
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
