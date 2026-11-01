"""Create a candidate install ZIP from exact package files, never recursive cache copies."""
from pathlib import Path
import zipfile
ROOT = Path(__file__).resolve().parents[1]
files = ['__init__.py', 'ui.py', 'adapter.py', 'core.py', 'replay_worker.py']
target = ROOT / '.runtime/candidate-addon.zip'
target.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in files:
        archive.write(ROOT / 'blender_invariants' / name, 'blender_invariants/' + name)
print('Candidate add-on ZIP staged:', target.name)
