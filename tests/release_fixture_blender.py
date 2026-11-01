"""Real install and replay checks against the exact extracted replacement release."""
import hashlib,json,os,sys,math
from pathlib import Path
import bpy
ROOT=Path(os.environ['INVARIANT_LEDGER_ROOT']).resolve()
EXAMPLE=ROOT/'.runtime/release-example-0.1.1'
checks=[]
bpy.ops.preferences.addon_install(filepath=str(ROOT/'artifacts/InvariantLedger-0.1.1-addon.zip'),overwrite=True)
bpy.ops.preferences.addon_enable(module='blender_invariants')
import blender_invariants as addon
for name in ['__init__.py','ui.py','adapter.py','core.py','replay_worker.py']:
 assert hashlib.sha256((Path(addon.__file__).parent/name).read_bytes()).digest()==hashlib.sha256((ROOT/'blender_invariants'/name).read_bytes()).digest()
checks.append('Actual v0.1.1 release ZIP installed/enabled; installed code hash-matches source')
manifest=json.loads((EXAMPLE/'manifest.json').read_text())
assert hashlib.sha256((EXAMPLE/'baseline.blend').read_bytes()).hexdigest()==manifest['baseline_sha256']
checks.append('Extracted baseline bytes match regenerated manifest')
bpy.ops.wm.open_mainfile(filepath=str(EXAMPLE/'baseline.blend'),load_ui=False,use_scripts=False)
obj=bpy.data.objects[manifest['object']]
baseline_metrics=addon.adapter.measured_object(obj)
assert math.isclose(baseline_metrics['volume'],8,abs_tol=1e-6)
assert addon.adapter.controls(obj)==manifest['controls']
checks.append('Sanitized baseline opens and retains actual evaluated volume8 and declared controls')
image=next(i for i in bpy.data.images if i.name=='fixture.png')
assert image.filepath.replace('\\','/')=='//assets/fixture.png'
assert hashlib.sha256((EXAMPLE/'assets/fixture.png').read_bytes()).hexdigest()==next(a['sha256']for a in manifest['assets']if a['kind']=='image')
checks.append('Active relative image filename and external image bytes preserved')
result=addon.replay_process(EXAMPLE/'manifest.json')
assert result['process_id']!=os.getpid() and result['verdict']['matches']
assert math.isclose(result['actual_metrics']['volume'],125,abs_tol=1e-6)
assert all(math.isclose(a,b,abs_tol=1e-6)for a,b in zip(sorted(x['metrics']['volume']for x in result['isolated_counterfactuals']),[15.625,64.0]))
checks.append('Actual different-process extracted release replay reproduces combined125 and isolated15.625/64 volumes')
report={'passed':True,'checks':checks,'native_Blender':list(bpy.app.version),'build_hash':bpy.app.build_hash.decode(),'different_process_verified':True,'baseline_sha256':manifest['baseline_sha256'],'GUI_drawing_verified':False,'baseline_measured_volume':baseline_metrics['volume'],'combined_measured_volume':result['actual_metrics']['volume'],'tested_release_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'limits':['Native panel registration/operators tested headlessly; prior hidden-window GUI access violation remains unresolved.','Selected mesh summaries only; not full geometry, simulation or render equivalence.']}
(ROOT/'artifacts/release-v0.1.1-tests.json').write_text(json.dumps(report,indent=2)+'\n')
print('EXTRACTED_RELEASE_PASS',len(checks))
