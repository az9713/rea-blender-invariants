"""Real Blender API, Geometry Nodes, add-on installation, and NEW-process replay."""
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import traceback
import bpy

ROOT = Path(os.environ['INVARIANT_LEDGER_ROOT']).resolve()
ARTIFACTS = ROOT / 'artifacts'
SESSION = ARTIFACTS / 'session'
SESSION.mkdir(parents=True, exist_ok=True)
# Relative asset and workspace paths remain portable in the synthetic .blend.
os.chdir(SESSION)
results = []
addon = adapter = obj = modifier = scale_socket = baseline = None


def check(name, action):
    try:
        details = action()
        results.append({'name': name, 'passed': True, 'details': details})
        print('PASS', name, flush=True)
    except Exception:
        results.append({'name': name, 'passed': False, 'traceback': traceback.format_exc()})
        print('FAIL', name, traceback.format_exc(), flush=True)


def isolation():
    values = {'executable': bpy.app.binary_path, 'config': bpy.utils.user_resource('CONFIG'),
              'scripts': bpy.utils.user_resource('SCRIPTS'), 'datafiles': bpy.utils.user_resource('DATAFILES')}
    for value in values.values():
        assert Path(value).resolve().is_relative_to(ROOT), value
    return {k: Path(v).resolve().relative_to(ROOT).as_posix() for k, v in values.items()}


def install_and_register():
    global addon, adapter
    bpy.ops.preferences.addon_install(filepath=str(ROOT / '.runtime/candidate-addon.zip'), overwrite=True)
    bpy.ops.preferences.addon_enable(module='blender_invariants')
    import blender_invariants as package
    addon = package
    adapter = addon.adapter
    installed = Path(addon.__file__).resolve().parent
    assert installed.is_relative_to(Path(os.environ['BLENDER_USER_SCRIPTS']).resolve())
    for name in ['__init__.py', 'ui.py', 'adapter.py', 'core.py', 'replay_worker.py']:
        assert hashlib.sha256((installed / name).read_bytes()).digest() == hashlib.sha256((ROOT / 'blender_invariants' / name).read_bytes()).digest()
    assert hasattr(bpy.types.Scene, 'invariant_ledger')
    assert bpy.types.IL_PT_invariant_ledger.bl_space_type == 'VIEW_3D'
    return {'installed_zip': True, 'panel_registered': True, 'source_files_hash_matched': True}


def geometry_node_fixture():
    global obj, modifier, scale_socket
    random.seed(17)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add(size=2)
    obj = bpy.context.object
    obj.name = 'ScientificCube'
    tree = bpy.data.node_groups.new('DeclaredCubeGeometry', 'GeometryNodeTree')
    tree.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    scale_socket = tree.interface.new_socket(name='Uniform Scale', in_out='INPUT', socket_type='NodeSocketFloat')
    scale_socket.default_value = 1.0
    inputs = tree.nodes.new('NodeGroupInput')
    output = tree.nodes.new('NodeGroupOutput')
    cube = tree.nodes.new('GeometryNodeMeshCube')
    cube.inputs['Size'].default_value = (2, 2, 2)
    combine = tree.nodes.new('ShaderNodeCombineXYZ')
    transform = tree.nodes.new('GeometryNodeTransform')
    for axis in 'XYZ':
        tree.links.new(inputs.outputs['Uniform Scale'], combine.inputs[axis])
    tree.links.new(combine.outputs['Vector'], transform.inputs['Scale'])
    tree.links.new(cube.outputs['Mesh'], transform.inputs['Geometry'])
    tree.links.new(transform.outputs['Geometry'], output.inputs['Geometry'])
    modifier = obj.modifiers.new('DeclaredGeometry', 'NODES')
    modifier.node_group = tree
    adapter.set_gn_input(modifier, scale_socket.identifier, 1.0)
    bpy.context.view_layer.update()
    metrics = adapter.measured_object(obj)
    assert metrics['unsupported'] == [], metrics
    assert abs(metrics['volume'] - 8) < 1e-6, metrics
    assert abs(metrics['area'] - 24) < 1e-6, metrics
    assert metrics['vertices'] == 8 and metrics['faces'] == 6
    return {'volume': metrics['volume'], 'area': metrics['area'], 'seed': 17, 'actual_geometry_nodes': True}


def capture_baseline():
    global baseline
    assets = SESSION / 'assets'
    assets.mkdir(exist_ok=True)
    generated = bpy.data.images.new('FixturePixelGenerated', 2, 2)
    generated.pixels = [random.random(), .3, .4, 1.] * 4
    generated.file_format = 'PNG'
    generated.filepath_raw = str(assets / 'fixture.png')
    generated.save()
    bpy.data.images.remove(generated)
    image = bpy.data.images.load(str(assets / 'fixture.png'))
    image.use_fake_user = True
    image.filepath = '//assets/fixture.png'
    (assets / 'cache-identity.json').write_text('{"seed":17,"frame":1,"synthetic":true}\n')
    settings = bpy.context.scene.invariant_ledger
    settings.output_dir = '//'
    settings.cache_path = '//assets/cache-identity.json'
    bpy.context.scene.frame_set(1)
    assert bpy.ops.invariant_ledger.capture() == {'FINISHED'}
    baseline = json.loads((SESSION / 'capture.json').read_text())
    assert len(baseline['assets']) == 2 and all(a['status'] == 'hashed' for a in baseline['assets'])
    assert baseline['baseline_sha256'] == hashlib.sha256((SESSION / 'baseline.blend').read_bytes()).hexdigest()
    return {'baseline_copy_exists': True, 'external_image_and_cache_hashed': True}


def scrub_public_synthetic_baseline():
    global baseline
    # Release fixture only: save the unchanged synthetic baseline uncompressed,
    # scrub cached UI folder strings and stale relative-image string padding.
    # No arbitrary user document is ever processed by this test helper.
    bpy.ops.wm.save_as_mainfile(filepath=str(SESSION / 'baseline.blend'), copy=True,
                               check_existing=False, compress=False)
    sys.path.insert(0,str(ROOT))
    from scripts.scrub_synthetic_fixture import scrub
    report=scrub(SESSION/'baseline.blend',ROOT)
    baseline['baseline_sha256']=report['new_sha256']
    (SESSION/'capture.json').write_text(json.dumps(baseline,indent=2)+'\n')
    (ARTIFACTS/'fixture-privacy.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def measured_changes():
    adapter.set_gn_input(modifier, scale_socket.identifier, 2.0)
    obj.scale = (1.25, 1.25, 1.25)
    obj.update_tag()
    bpy.context.view_layer.update()
    assert bpy.ops.invariant_ledger.analyze() == {'FINISHED'}
    result = json.loads(bpy.context.scene.invariant_ledger.last_report)
    assert not result['passes'] and len(result['violations']) == 2, result
    assert result['replay_supported'], result
    assert len(result['operations']) == 2
    assert math.isclose(result['ratios']['volume'], 15.625, abs_tol=1e-6)
    assert math.isclose(result['ratios']['area'], 6.25, abs_tol=1e-6)
    return {'volume_ratio': result['ratios']['volume'], 'area_ratio': result['ratios']['area'],
            'declared_operations': len(result['operations']), 'violations': result['violations']}


def real_clean_process_replay():
    assert bpy.ops.invariant_ledger.replay() == {'FINISHED'}
    result = json.loads((SESSION / 'replay-results.json').read_text())
    assert result['process_id'] != os.getpid(), 'Replay reused the original process'
    assert result['verdict']['matches'], result
    volumes = sorted(r['metrics']['volume'] for r in result['isolated_counterfactuals'])
    assert len(volumes) == 2 and math.isclose(volumes[0], 15.625, abs_tol=1e-6) and math.isclose(volumes[1], 64, abs_tol=1e-6), volumes
    return {'different_process_verified': True, 'isolated_counterfactual_volumes': volumes,
            'combined_volume': result['actual_metrics']['volume'], 'identities_verified': result['external_identities_verified']}


def cache_tamper_refused():
    path = SESSION / 'assets/cache-identity.json'
    original = path.read_bytes()
    try:
        path.write_bytes(original + b'changed')
        result = adapter.analyze(obj, baseline, SESSION)
        assert 'external_asset_or_cache_identity_changed' in result['unsupported_replay']
        # Use the last VALID manifest: worker must independently hash assets.
        try:
            addon.replay_process(SESSION / 'manifest.json')
            raise AssertionError('Tampered dependency unexpectedly replayed')
        except RuntimeError as error:
            assert 'SHA256 mismatch' in str(error), str(error)
        return {'analysis_flags_identity_change': True, 'independent_child_rejected_tamper': True}
    finally:
        path.write_bytes(original)


def untracked_edits_flagged():
    old_scale = obj.scale.copy()
    obj.scale.x = -obj.scale.x
    bpy.context.view_layer.update()
    try:
        assert 'nonpositive_object_scale_outside_replay_contract' in adapter.analyze(obj, baseline, SESSION)['unsupported_replay']
    finally:
        obj.scale = old_scale
        bpy.context.view_layer.update()
    vertex = obj.data.vertices[0]
    old = vertex.co.copy()
    try:
        vertex.co.x += .125
        assert 'source_mesh_changed_outside_declared_controls' in adapter.analyze(obj, baseline, SESSION)['unsupported_replay']
    finally:
        vertex.co = old
    cube = next(n for n in modifier.node_group.nodes if n.bl_idname == 'GeometryNodeMeshCube')
    cube.inputs['Size'].default_value = (3, 2, 2)
    obj.update_tag()
    bpy.context.view_layer.update()
    try:
        assert 'node_graph_changed_outside_declared_controls' in adapter.analyze(obj, baseline, SESSION)['unsupported_replay']
    finally:
        cube.inputs['Size'].default_value = (2, 2, 2)
        obj.update_tag()
        bpy.context.view_layer.update()
    return {'base_mesh_edit_flagged': True, 'internal_node_edit_flagged': True, 'nonpositive_scale_flagged': True}


def open_mesh_volume_refused():
    bpy.ops.mesh.primitive_plane_add(size=2)
    plane = bpy.context.object
    try:
        metrics = adapter.measured_object(plane)
        assert metrics['volume'] is None and metrics['boundary_edges'] == 4
        return {'volume': metrics['volume'], 'unsupported': metrics['unsupported']}
    finally:
        bpy.data.objects.remove(plane, do_unlink=True)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)


def restore_final_replay():
    path, manifest = adapter.export_manifest(obj, baseline, SESSION)
    assert not manifest['unsupported'], manifest['unsupported']
    result = addon.replay_process(path)
    assert result['verdict']['matches']
    return {'final_fixture_manifest_verified': True}


try:
    check('project_isolated_portable_runtime', isolation)
    check('real_zip_install_register_panel_and_operators', install_and_register)
    check('real_geometry_nodes_cube_evaluated_in_world_space', geometry_node_fixture)
    check('baseline_blend_copy_and_external_identities', capture_baseline)
    check('synthetic_fixture_metadata_padding_sanitized', scrub_public_synthetic_baseline)
    check('declared_GN_and_object_scale_invariant_violations', measured_changes)
    check('new_process_replay_and_isolated_edit_counterfactuals', real_clean_process_replay)
    check('cache_tamper_independently_refused', cache_tamper_refused)
    check('untracked_mesh_and_node_graph_edits_flagged', untracked_edits_flagged)
    check('real_open_mesh_has_unsupported_volume', open_mesh_volume_refused)
    check('final_synthetic_replay_fixture_restored_and_verified', restore_final_replay)
finally:
    files = ['blender_invariants/' + name for name in ['__init__.py', 'ui.py', 'adapter.py', 'core.py', 'replay_worker.py']]
    files += ['tests/integration_blender.py','scripts/scrub_synthetic_fixture.py','tests/test_fixture_privacy.py']
    report = {'runtime': 'Real portable Blender + evaluated Geometry Nodes; no mocked bpy',
              'blender_version': list(bpy.app.version), 'build_hash': bpy.app.build_hash.decode(),
              'passed': sum(r['passed'] for r in results), 'total': len(results), 'results': results,
              'tested_files': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}}
    (ARTIFACTS / 'integration-results.json').write_text(json.dumps(report, indent=2) + '\n')
    print('INVARIANT_LEDGER_NATIVE', report['passed'], '/', report['total'], flush=True)
    if report['passed'] != report['total']:
        raise RuntimeError('Native integration failed; inspect integration-results.json')
