"""Native CPU renders of the synthetic measured fixture, not UI screenshots."""
import json
import os
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(os.environ['INVARIANT_LEDGER_ROOT']).resolve()
import sys
sys.path.insert(0,str(ROOT))
from blender_invariants import adapter
from blender_invariants.replay_worker import apply_operation
session=ROOT/'artifacts/session'
bpy.ops.wm.open_mainfile(filepath=str(session/'baseline.blend'),load_ui=False,use_scripts=False)
manifest=json.loads((session/'manifest.json').read_text())
obj=bpy.data.objects[manifest['object']]
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=32
scene.cycles.seed=17
scene.cycles.use_denoising=True
scene.render.resolution_x=640
scene.render.resolution_y=480
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.world.color=(.025,.035,.05)
material=bpy.data.materials.new('SyntheticLedgerTeal')
material.diffuse_color=(.08,.65,.48,1)
principled=material.node_tree.nodes.get('Principled BSDF')
principled.inputs['Base Color'].default_value=(.08,.65,.48,1)
principled.inputs['Roughness'].default_value=.35
obj.data.materials.append(material)
# Generated geometry needs an explicit material node; adding one changes the
# material only and does not change the measured mesh invariants.
group=obj.modifiers[0].node_group
output=next(n for n in group.nodes if n.bl_idname=='NodeGroupOutput')
incoming=output.inputs['Geometry'].links[0].from_socket
assign=group.nodes.new('GeometryNodeSetMaterial')
assign.inputs['Material'].default_value=material
group.links.new(incoming,assign.inputs['Geometry'])
group.links.new(assign.outputs['Geometry'],output.inputs['Geometry'])
camera_data=bpy.data.cameras.new('EvidenceCamera')
camera=bpy.data.objects.new('EvidenceCamera',camera_data)
scene.collection.objects.link(camera)
camera.location=(8,-10,7)
camera.rotation_euler=(-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO'
camera_data.ortho_scale=11.5
scene.camera=camera
for name,location,power,size in [('Key',(3,-4,7),1200,5),('Fill',(-4,-2,3),700,5),('Rim',(3,4,5),1000,3)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
 light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=location
 light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
before=adapter.measured_object(obj)
scene.render.filepath=str(ROOT/'docs/native-before.png')
bpy.ops.render.render(write_still=True)
for operation in manifest['operations']:apply_operation(obj,operation,operation['after'])
after=adapter.measured_object(obj)
scene.render.filepath=str(ROOT/'docs/native-after.png')
bpy.ops.render.render(write_still=True)
(ROOT/'artifacts/render-results.json').write_text(json.dumps({'native_cpu_render':True,'seed':17,'samples':32,'before_volume':before['volume'],'after_volume':after['volume'],'before_area':before['area'],'after_area':after['area'],'limit':'Illustrative renders of the measured synthetic fixture. No render equivalence test or GUI screenshot claim.'},indent=2)+'\n')
