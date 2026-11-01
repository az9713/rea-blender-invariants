# SPDX-License-Identifier: GPL-2.0-or-later
bl_info = {
    'name': 'Invariant Ledger', 'author': 'Invariant Ledger contributors',
    'version': (0, 1, 1), 'blender': (5, 2, 0),
    'location': '3D View > Sidebar > Invariant Ledger',
    'description': 'Scientific mesh invariants, declared-edit counterfactuals and bounded clean-process replay',
    'category': 'Object',
}

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

if bpy is not None:
    from .ui import register, unregister, replay_process, adapter
