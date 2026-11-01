# SPDX-License-Identifier: GPL-2.0-or-later
"""Blender API measurement and bounded edit manifests. No bpy import in core."""
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import bpy
from .core import Contract, asset_identity, compare, digest, measure

REVIEWED_NODES = {'NodeGroupInput', 'NodeGroupOutput', 'GeometryNodeMeshCube',
                 'GeometryNodeTransform', 'ShaderNodeCombineXYZ', 'ShaderNodeMath',
                 'ShaderNodeValue', 'GeometryNodeJoinGeometry', 'GeometryNodeSetPosition',
                 'GeometryNodeInputPosition', 'ShaderNodeVectorMath', 'GeometryNodeRealizeInstances'}


def get_gn_input(modifier, identifier):
    prop = getattr(modifier.properties.inputs, identifier)
    if hasattr(prop, 'type') and prop.type == 'ATTRIBUTE':
        raise ValueError('Attribute-driven scalar inputs are outside the replay contract')
    return prop.value


def set_gn_input(modifier, identifier, value):
    prop = getattr(modifier.properties.inputs, identifier)
    if hasattr(prop, 'type') and prop.type == 'ATTRIBUTE':
        raise ValueError('Attribute-driven scalar inputs are outside the replay contract')
    prop.value = value


def measured_object(obj):
    if obj.type != 'MESH':
        raise ValueError('Select a mesh object; curves, volumes and instances are unsupported')
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        matrix = evaluated.matrix_world
        vertices = [list(matrix @ vertex.co) for vertex in mesh.vertices]
        return measure(vertices, [list(edge.vertices) for edge in mesh.edges],
                       [list(face.vertices) for face in mesh.polygons],
                       [list(triangle.vertices) for triangle in mesh.loop_triangles])
    finally:
        evaluated.to_mesh_clear()


def _value(value):
    if isinstance(value, (bool, int, float, str)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Non-finite node parameter')
        return value
    if hasattr(value, 'name_full'):
        return {'id_type': type(value).__name__, 'name': value.name_full}
    try:
        return [_value(v) for v in value]
    except TypeError:
        return None


def graph_state(obj):
    nodes, links, unsupported = [], [], []
    for modifier in obj.modifiers:
        if modifier.type != 'NODES':
            unsupported.append('unreviewed_modifier:' + modifier.type)
            continue
        group = modifier.node_group
        if group is None:
            unsupported.append('missing_geometry_node_group')
            continue
        for node in group.nodes:
            if node.bl_idname not in REVIEWED_NODES:
                unsupported.append('unreviewed_node:' + node.bl_idname)
            record = {'modifier': modifier.name, 'name': node.name, 'type': node.bl_idname,
                      'inputs': {str(i): _value(socket.default_value) for i, socket in enumerate(node.inputs) if hasattr(socket, 'default_value')}}
            for prop in ('operation', 'data_type', 'domain', 'mode', 'noise_dimensions', 'normalize', 'input_type', 'axis'):
                if hasattr(node, prop):
                    record[prop] = _value(getattr(node, prop))
            nodes.append(record)
        for link in group.links:
            links.append([modifier.name, link.from_node.name, link.from_socket.identifier,
                          link.to_node.name, link.to_socket.identifier])
    state = {'nodes': sorted(nodes, key=lambda n: (n['modifier'], n['name'])), 'links': sorted(links)}
    return {'fingerprint': digest(state), 'unsupported': sorted(set(unsupported)), 'snapshot': state}


def base_mesh_digest(obj):
    return digest({'vertices': [list(v.co) for v in obj.data.vertices],
                   'edges': [list(e.vertices) for e in obj.data.edges],
                   'polygons': [list(p.vertices) for p in obj.data.polygons]})


def controls(obj):
    values = {'object_scale': {'kind': 'scale', 'value': list(obj.scale)}}
    for modifier in obj.modifiers:
        if modifier.type != 'NODES' or not modifier.node_group:
            continue
        for socket in modifier.node_group.interface.items_tree:
            if socket.item_type != 'SOCKET' or socket.in_out not in ('INPUT', 'BOTH'):
                continue
            if socket.socket_type not in ('NodeSocketFloat', 'NodeSocketInt', 'NodeSocketBool'):
                continue
            value = get_gn_input(modifier, socket.identifier)
            if type(value) not in (bool, int, float) or not math.isfinite(value):
                raise ValueError('Unsupported or non-finite exposed node value')
            key = digest([modifier.name, socket.identifier])
            values[key] = {'kind': 'gn_scalar', 'modifier': modifier.name,
                           'socket': socket.identifier, 'label': socket.name, 'value': value}
    return values


def identities(workspace, cache_path=''):
    records = []
    for image in bpy.data.images:
        if image.source != 'FILE' or (image.users == 0 and not image.use_fake_user):
            continue
        if image.packed_file:
            records.append({'kind': 'image', 'name': image.name, 'status': 'packed',
                            'sha256': hashlib.sha256(bytes(image.packed_file.data)).hexdigest()})
        elif image.filepath:
            identity = asset_identity(bpy.path.abspath(image.filepath), workspace)
            records.append(dict(identity, kind='image', name=image.name))
    if cache_path:
        records.append(dict(asset_identity(bpy.path.abspath(cache_path), workspace), kind='declared_cache', name='Declared cache file'))
    return sorted(records, key=lambda r: (r['kind'], r['name']))


def capture(obj, workspace, contract, cache_path=''):
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    contract.validate()
    graph = graph_state(obj)
    current = {'schema': 1, 'object': obj.name, 'metrics': measured_object(obj),
               'controls': controls(obj), 'graph': graph, 'base_mesh_digest': base_mesh_digest(obj),
               'untracked_transform': digest({'location': list(obj.location), 'rotation': list(obj.rotation_euler),
                                               'quaternion': list(obj.rotation_quaternion), 'mode': obj.rotation_mode,
                                               'delta_location': list(obj.delta_location), 'delta_rotation': list(obj.delta_rotation_euler),
                                               'delta_scale': list(obj.delta_scale)}),
               'assets': identities(workspace, cache_path), 'cache_path': cache_path,
               'contract': asdict(contract), 'frame': bpy.context.scene.frame_current,
               'blender_version': list(bpy.app.version), 'build_hash': bpy.app.build_hash.decode(),
               'unsupported': graph['unsupported']}
    # Save a copy, not the user's active document. No startup/preferences save.
    bpy.ops.wm.save_as_mainfile(filepath=str(workspace / 'baseline.blend'), copy=True, check_existing=False)
    current['baseline_sha256'] = hashlib.sha256((workspace / 'baseline.blend').read_bytes()).hexdigest()
    (workspace / 'capture.json').write_text(json.dumps(current, indent=2, allow_nan=False) + '\n')
    return current


def analyze(obj, baseline, workspace):
    if obj.name != baseline['object']:
        raise ValueError('Select the object named in the captured contract')
    now_controls, graph = controls(obj), graph_state(obj)
    flags = list(graph['unsupported'])
    if any(value <= 0 for value in obj.scale):
        flags.append('nonpositive_object_scale_outside_replay_contract')
    transform = digest({'location': list(obj.location), 'rotation': list(obj.rotation_euler),
                        'quaternion': list(obj.rotation_quaternion), 'mode': obj.rotation_mode,
                        'delta_location': list(obj.delta_location), 'delta_rotation': list(obj.delta_rotation_euler),
                        'delta_scale': list(obj.delta_scale)})
    if transform != baseline['untracked_transform']:
        flags.append('transform_changed_outside_declared_scale')
    if obj.parent or obj.constraints or obj.animation_data or obj.data.shape_keys:
        flags.append('parent_constraint_animation_or_shape_keys_unreviewed')
    operations = []
    if set(now_controls) != set(baseline['controls']):
        flags.append('declared_control_set_changed')
    for key in baseline['controls'].keys() & now_controls.keys():
        before, after = baseline['controls'][key], now_controls[key]
        if before['value'] != after['value']:
            operations.append(dict(after, before=before['value'], after=after['value']))
    if graph['fingerprint'] != baseline['graph']['fingerprint']:
        flags.append('node_graph_changed_outside_declared_controls')
    if base_mesh_digest(obj) != baseline['base_mesh_digest']:
        flags.append('source_mesh_changed_outside_declared_controls')
    if bpy.context.scene.frame_current != baseline['frame']:
        flags.append('frame_changed')
    assets = identities(workspace, baseline['cache_path'])
    if assets != baseline['assets']:
        flags.append('external_asset_or_cache_identity_changed')
    for asset in assets:
        if asset['status'] not in ('hashed', 'packed'):
            flags.append('unverified_external_dependency:' + asset['status'])
    metrics = measured_object(obj)
    result = compare(baseline['metrics'], metrics, Contract(**baseline['contract']))
    result.update({'metrics': metrics, 'operations': sorted(operations, key=lambda v: json.dumps(v, sort_keys=True)),
                   'assets': assets, 'unsupported_replay': sorted(set(flags)),
                   'replay_supported': not flags, 'object': obj.name})
    return result


def export_manifest(obj, baseline, workspace):
    workspace = Path(workspace).resolve()
    result = analyze(obj, baseline, workspace)
    manifest = {'schema': 1, 'baseline_file': 'baseline.blend',
                'baseline_sha256': baseline['baseline_sha256'], 'object': obj.name,
                'blender_version': baseline['blender_version'], 'build_hash': baseline['build_hash'],
                'frame': baseline['frame'], 'controls': baseline['controls'],
                'graph_fingerprint': baseline['graph']['fingerprint'],
                'expected_metrics': result['metrics'], 'operations': result['operations'],
                'baseline_metrics': baseline['metrics'],
                'assets': baseline['assets'], 'unsupported': result['unsupported_replay'],
                'tolerance': baseline['contract']['tolerance'], 'contract_result': result,
                'equivalence_scope': 'Selected evaluated mesh summaries only; no simulation, arbitrary history or render equivalence claim.'}
    path = workspace / 'manifest.json'
    path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    return path, manifest
