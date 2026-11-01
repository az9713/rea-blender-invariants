# SPDX-License-Identifier: GPL-2.0-or-later
"""Run with Blender --background --factory-startup --disable-autoexec --python.

This is a real new-process replay of bounded controls against a hashed baseline.
It does not execute manifest code, arbitrary paths or expressions.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bpy
from blender_invariants import adapter
from blender_invariants.core import asset_identity, equivalent


def apply_operation(obj, operation, value):
    if operation['kind'] == 'scale':
        if not isinstance(value, list) or len(value) != 3 or not all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in value):
            raise ValueError('Scale replay requires three positive finite numbers')
        obj.scale = value
    elif operation['kind'] == 'gn_scalar':
        if type(value) not in (int, float, bool) or not math.isfinite(value):
            raise ValueError('Exposed node replay requires a finite scalar')
        modifier = obj.modifiers.get(operation['modifier'])
        if not modifier or modifier.type != 'NODES' or not hasattr(modifier.properties.inputs, operation['socket']):
            raise ValueError('Declared modifier/socket not found')
        adapter.set_gn_input(modifier, operation['socket'], value)
    else:
        raise ValueError('Unsupported manifest operation')
    obj.update_tag()
    bpy.context.view_layer.update()


def replay(path):
    manifest_path = Path(path).resolve()
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('schema') != 1 or manifest.get('unsupported'):
        raise ValueError('Manifest is unsupported; inspect recorded flags')
    if list(bpy.app.version) != manifest['blender_version'] or bpy.app.build_hash.decode() != manifest['build_hash']:
        raise ValueError('Pinned Blender version/build mismatch')
    baseline = (root / manifest['baseline_file']).resolve()
    if not baseline.is_relative_to(root) or not baseline.is_file():
        raise ValueError('Baseline path escapes manifest directory or is missing')
    if hashlib.sha256(baseline.read_bytes()).hexdigest() != manifest['baseline_sha256']:
        raise ValueError('Baseline SHA256 mismatch')
    for asset in manifest['assets']:
        if asset['status'] == 'packed':
            continue
        if asset['status'] != 'hashed':
            raise ValueError('Unverified external asset/cache')
        target = (root / asset['path']).resolve()
        identity = asset_identity(target, root)
        if identity.get('status') != 'hashed' or identity.get('sha256') != asset['sha256']:
            raise ValueError('External asset/cache SHA256 mismatch: ' + asset['name'])
    bpy.ops.wm.open_mainfile(filepath=str(baseline), load_ui=False, use_scripts=False)
    obj = bpy.data.objects.get(manifest['object'])
    if obj is None:
        raise ValueError('Selected object missing from pinned baseline')
    for asset in manifest['assets']:
        if asset['kind'] == 'image':
            image = bpy.data.images.get(asset['name'])
            if image is None:
                raise ValueError('Image ID missing')
            if asset['status'] == 'packed':
                if not image.packed_file or hashlib.sha256(bytes(image.packed_file.data)).hexdigest() != asset['sha256']:
                    raise ValueError('Packed image identity mismatch')
            else:
                image.filepath = str(root / asset['path'])
                image.reload()
    bpy.context.scene.frame_set(manifest['frame'])
    if adapter.graph_state(obj)['fingerprint'] != manifest['graph_fingerprint']:
        raise ValueError('Node graph fingerprint mismatch')
    if adapter.controls(obj) != manifest['controls']:
        raise ValueError('Baseline controls differ from captured values')
    initial = adapter.measured_object(obj)
    if not equivalent(manifest['baseline_metrics'], initial, manifest['tolerance'])['matches']:
        raise ValueError('Pinned baseline evaluated geometry differs')
    counterfactuals = []
    # Each operation is first evaluated alone against the same baseline. These
    # are actual parameter counterfactuals, not a guessed attribution from a diff.
    for operation in manifest['operations']:
        apply_operation(obj, operation, operation['after'])
        metrics = adapter.measured_object(obj)
        counterfactuals.append({'operation': operation, 'metrics': metrics,
                               'volume_delta': None if metrics['volume'] is None or initial['volume'] is None else metrics['volume'] - initial['volume'],
                               'area_delta': metrics['area'] - initial['area']})
        apply_operation(obj, operation, operation['before'])
    for operation in manifest['operations']:
        apply_operation(obj, operation, operation['after'])
    actual = adapter.measured_object(obj)
    verdict = equivalent(manifest['expected_metrics'], actual, manifest['tolerance'])
    return {'schema': 1, 'process_id': os.getpid(), 'blender_version': list(bpy.app.version),
            'build_hash': bpy.app.build_hash.decode(), 'verdict': verdict, 'actual_metrics': actual,
            'isolated_counterfactuals': counterfactuals, 'external_identities_verified': len(manifest['assets']),
            'limits': ['Selected evaluated mesh summary equivalence only.',
                       'No simulation, arbitrary node graph/history edit, or render equivalence proved.']}


if __name__ == '__main__':
    import traceback
    args = sys.argv[sys.argv.index('--') + 1:]
    report_path = Path(args[1]).resolve()
    try:
        result = replay(args[0])
        report_path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        if not result['verdict']['matches']:
            raise RuntimeError('Replay mesh-summary equivalence failed')
        print('INVARIANT_LEDGER_REPLAY_PASS', result['process_id'])
    except Exception as error:
        if not report_path.exists():
            report_path.write_text(json.dumps({'error': str(error), 'traceback': traceback.format_exc()}, indent=2) + '\n')
        raise
