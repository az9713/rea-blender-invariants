"""Actual Blender window/panel draw and screenshot, launched hidden by the harness."""
import hashlib
import json
import os
from pathlib import Path
import traceback
import bpy

ROOT = Path(os.environ['INVARIANT_LEDGER_ROOT']).resolve()
checks, errors = [], []


def finish():
    report = {'native_gui': True, 'passed': len(checks), 'checks': checks, 'errors': errors,
              'tested_files': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in ['blender_invariants/__init__.py', 'blender_invariants/ui.py', 'tests/gui_smoke.py']}}
    (ROOT / 'artifacts/gui-results.json').write_text(json.dumps(report, indent=2) + '\n')
    bpy.ops.wm.quit_blender()


def screenshot():
    try:
        window = bpy.context.window_manager.windows[0]
        area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
        region = next(r for r in area.regions if r.type == 'UI')
        assert region.active_panel_category == 'Invariant Ledger'
        assert bpy.context.scene.invariant_ledger.last_report
        with bpy.context.temp_override(window=window, area=area):
            bpy.ops.screen.screenshot(filepath=str(ROOT / 'docs/native-panel.png'), check_existing=False)
        assert (ROOT / 'docs/native-panel.png').stat().st_size > 10000
        checks.append('native_panel_drawn_and_window_pixels_captured')
    except Exception:
        errors.append(traceback.format_exc())
    finish()
    return None


def activate_panel():
    try:
        window = bpy.context.window_manager.windows[0]
        area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
        region = next(r for r in area.regions if r.type == 'UI')
        region.active_panel_category = 'Invariant Ledger'
        checks.append('native_sidebar_category_activated')
        bpy.app.timers.register(screenshot, first_interval=1.0)
    except Exception:
        errors.append(traceback.format_exc())
        finish()
    return None


def setup():
    try:
        bpy.ops.preferences.addon_enable(module='blender_invariants')
        import blender_invariants as addon
        from blender_invariants.replay_worker import apply_operation
        checks.append('installed_addon_enabled_in_real_GUI')
        session = ROOT / 'artifacts/session'
        manifest = json.loads((session / 'manifest.json').read_text())
        bpy.ops.wm.open_mainfile(filepath=str(session / 'baseline.blend'), load_ui=False, use_scripts=False)
        obj = bpy.data.objects[manifest['object']]
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        for operation in manifest['operations']:
            apply_operation(obj, operation, operation['after'])
        assert bpy.ops.invariant_ledger.analyze() == {'FINISHED'}
        report = json.loads(bpy.context.scene.invariant_ledger.last_report)
        assert not report['passes'] and len(report['operations']) == 2
        checks.append('native_GUI_operator_measured_real_invariant_violations')
        window = bpy.context.window_manager.windows[0]
        area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
        area.spaces.active.show_region_ui = True
        region = next(r for r in area.regions if r.type == 'WINDOW')
        with bpy.context.temp_override(window=window, area=area, region=region):
            bpy.ops.view3d.view_all(center=True)
        area.tag_redraw()
        bpy.app.timers.register(activate_panel, first_interval=1.0)
    except Exception:
        errors.append(traceback.format_exc())
        bpy.app.timers.register(finish, first_interval=.2)

    return None

bpy.app.timers.register(setup, first_interval=1.0)
