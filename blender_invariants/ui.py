# SPDX-License-Identifier: GPL-2.0-or-later
import json
import os
from pathlib import Path
import subprocess
import bpy
from bpy.props import BoolProperty, FloatProperty, PointerProperty, StringProperty
from . import adapter
from .core import Contract


def workspace(settings):
    if not settings.output_dir:
        raise ValueError('Choose a workspace directory first')
    value = bpy.path.abspath(settings.output_dir) or os.getcwd()
    return Path(value).resolve()


def isolated_environment(root):
    env = dict(os.environ)
    for key, suffix in [('HOME', 'home'), ('USERPROFILE', 'home'), ('APPDATA', 'home/AppData/Roaming'),
                        ('LOCALAPPDATA', 'home/AppData/Local'), ('TEMP', 'tmp'), ('TMP', 'tmp'),
                        ('BLENDER_USER_CONFIG', 'config'), ('BLENDER_USER_SCRIPTS', 'scripts'),
                        ('BLENDER_USER_DATAFILES', 'datafiles'), ('XDG_CACHE_HOME', 'cache'),
                        ('XDG_CONFIG_HOME', 'xdg-config'), ('XDG_DATA_HOME', 'xdg-data')]:
        target = Path(root) / suffix
        target.mkdir(parents=True, exist_ok=True)
        env[key] = str(target)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONPYCACHEPREFIX'] = str(Path(root) / 'pycache')
    return env


def replay_process(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    output = manifest_path.parent / 'replay-results.json'
    if output.exists():
        output.unlink()
    worker = Path(__file__).parent / 'replay_worker.py'
    completed = subprocess.run([bpy.app.binary_path, '--background', '--factory-startup',
                                '--disable-autoexec', '--threads', '1', '--python-exit-code', '1',
                                '--python', str(worker), '--', str(manifest_path), str(output)],
                               cwd=manifest_path.parent, env=isolated_environment(manifest_path.parent / '.replay-runtime'),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               encoding='utf-8', errors='replace', timeout=120)
    if completed.returncode or not output.exists():
        raise RuntimeError('Clean-process replay failed. ' + completed.stdout[-1800:])
    result = json.loads(output.read_text())
    if not result.get('verdict', {}).get('matches'):
        raise RuntimeError('Replay did not match the declared mesh summaries')
    return result


class IL_Settings(bpy.types.PropertyGroup):
    output_dir: StringProperty(name='Workspace', subtype='DIR_PATH', default='//invariant-ledger', options={'PATH_SUPPORTS_BLEND_RELATIVE'})
    cache_path: StringProperty(name='Declared cache file', subtype='FILE_PATH', default='', options={'PATH_SUPPORTS_BLEND_RELATIVE'})
    volume_min: FloatProperty(name='Volume min ratio', default=.8, min=.000001)
    volume_max: FloatProperty(name='Volume max ratio', default=1.2, min=.000001)
    area_min: FloatProperty(name='Area min ratio', default=.8, min=.000001)
    area_max: FloatProperty(name='Area max ratio', default=1.2, min=.000001)
    preserve_topology: BoolProperty(name='Preserve topology', default=True)
    last_report: StringProperty(default='')
    replay_status: StringProperty(default='Not replayed')


class IL_OT_capture(bpy.types.Operator):
    bl_idname = 'invariant_ledger.capture'
    bl_label = 'Capture baseline and contract'
    bl_description = 'Save a baseline blend COPY and an explicit numerical contract in the workspace'

    def execute(self, context):
        try:
            settings = context.scene.invariant_ledger
            obj = context.view_layer.objects.active
            if obj is None:
                raise ValueError('Select a mesh object')
            contract = Contract(settings.volume_min, settings.volume_max, settings.area_min,
                                settings.area_max, settings.preserve_topology)
            result = adapter.capture(obj, workspace(settings), contract, settings.cache_path)
            settings.last_report = ''
            settings.replay_status = 'Captured: ' + result['object']
            self.report({'INFO'}, 'Baseline copy and contract captured')
            return {'FINISHED'}
        except Exception as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}


class IL_OT_analyze(bpy.types.Operator):
    bl_idname = 'invariant_ledger.analyze'
    bl_label = 'Measure and explain changes'

    def execute(self, context):
        try:
            settings = context.scene.invariant_ledger
            root = workspace(settings)
            baseline = json.loads((root / 'capture.json').read_text())
            result = adapter.analyze(context.view_layer.objects.active, baseline, root)
            settings.last_report = json.dumps(result, allow_nan=False)
            (root / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
            evidence = bpy.data.texts.get('InvariantLedgerEvidence') or bpy.data.texts.new('InvariantLedgerEvidence')
            evidence.clear()
            evidence.write(json.dumps(result, indent=2, allow_nan=False))
            self.report({'INFO'}, 'Invariants pass' if result['passes'] else 'Invariant violations measured')
            return {'FINISHED'}
        except Exception as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}


class IL_OT_replay(bpy.types.Operator):
    bl_idname = 'invariant_ledger.replay'
    bl_label = 'Export and verify clean-process replay'
    bl_description = 'Reopen the hashed baseline in a new Blender process; isolate each declared edit and compare mesh summaries'

    def execute(self, context):
        try:
            settings = context.scene.invariant_ledger
            root = workspace(settings)
            baseline = json.loads((root / 'capture.json').read_text())
            path, manifest = adapter.export_manifest(context.view_layer.objects.active, baseline, root)
            if manifest['unsupported']:
                raise ValueError('Replay refused: ' + '; '.join(manifest['unsupported']))
            result = replay_process(path)
            settings.replay_status = 'Verified in a new process; {} isolated edit(s)'.format(len(result['isolated_counterfactuals']))
            self.report({'INFO'}, settings.replay_status)
            return {'FINISHED'}
        except Exception as error:
            context.scene.invariant_ledger.replay_status = 'Failed/refused: ' + str(error)[:240]
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}


class IL_PT_panel(bpy.types.Panel):
    bl_label = 'Invariant Ledger'
    bl_idname = 'IL_PT_invariant_ledger'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Invariant Ledger'

    def draw(self, context):
        settings = context.scene.invariant_ledger
        layout = self.layout
        layout.prop(settings, 'output_dir')
        layout.prop(settings, 'cache_path')
        box = layout.box()
        box.label(text='Declare before capturing')
        row = box.row(align=True)
        row.prop(settings, 'volume_min')
        row.prop(settings, 'volume_max')
        row = box.row(align=True)
        row.prop(settings, 'area_min')
        row.prop(settings, 'area_max')
        box.prop(settings, 'preserve_topology')
        layout.operator('invariant_ledger.capture')
        layout.operator('invariant_ledger.analyze')
        if settings.last_report:
            try:
                result = json.loads(settings.last_report)
                box = layout.box()
                box.label(text='Contract passes' if result['passes'] else 'Contract violated',
                          icon='CHECKMARK' if result['passes'] else 'ERROR')
                for key, value in result['ratios'].items():
                    box.label(text='{} ratio: {}'.format(key, 'unsupported' if value is None else '{:.6g}'.format(value)))
                for line in result['violations'][:5]:
                    box.label(text=line[:90])
                box.label(text='Declared edits: ' + str(len(result['operations'])))
                for operation in result['operations'][:4]:
                    box.label(text='{}: {} -> {}'.format(operation.get('label', operation['kind']), operation['before'], operation['after'])[:90])
                for flag in result['unsupported_replay'][:5]:
                    box.label(text='Unsupported: ' + flag[:72], icon='INFO')
            except (ValueError, KeyError):
                box.label(text='Report unavailable; analyze again')
        layout.operator('invariant_ledger.replay')
        layout.label(text=settings.replay_status[:95])
        layout.label(text='Mesh summaries; not simulation/render proof', icon='INFO')


CLASSES = (IL_Settings, IL_OT_capture, IL_OT_analyze, IL_OT_replay, IL_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.invariant_ledger = PointerProperty(type=IL_Settings)


def unregister():
    del bpy.types.Scene.invariant_ledger
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
