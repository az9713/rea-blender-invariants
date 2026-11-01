"""Exact-path, verification-gated installable add-on and synthetic example ZIPs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
PACKAGE_FILES = ['__init__.py', 'ui.py', 'adapter.py', 'core.py', 'replay_worker.py']
FIXTURE_FILES = ['baseline.blend', 'capture.json', 'analysis.json', 'manifest.json',
                 'replay-results.json', 'assets/fixture.png', 'assets/cache-identity.json']


def write_zip(path, entries):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for source, name in entries:
            if not source.is_file() or not source.resolve().is_relative_to(ROOT):
                raise RuntimeError('Missing or escaping package source: ' + str(source))
            if name.startswith('/') or '..' in name.split('/'):
                raise RuntimeError('Escaping archive path')
            archive.write(source, name)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('ZIP integrity check failed')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix(path.suffix + '.sha256').write_text(digest + '  ' + path.name + '\n')
    print(path.name, path.stat().st_size, digest)


def build():
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_core.py'], cwd=ROOT, check=True)
    native = json.loads((ARTIFACTS / 'integration-results.json').read_text())
    if native['passed'] != native['total'] or native['total'] < 10:
        raise RuntimeError('Real Blender integration must pass before release')
    for name, expected in native['tested_files'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Native evidence is stale for ' + name)
    source = json.loads((ROOT / 'investigation/public-source/manifest.json').read_text())
    if not source['commit'].startswith(native['build_hash']):
        raise RuntimeError('Collected source does not match the tested native build')
    for item in source['files']:
        if hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() != item['sha256']:
            raise RuntimeError('Pinned source evidence was modified')
    replay = json.loads((ARTIFACTS / 'session/replay-results.json').read_text())
    if not replay.get('verdict', {}).get('matches'):
        raise RuntimeError('Final synthetic replay fixture must pass')
    session = ARTIFACTS / 'session'
    manifest = json.loads((session / 'manifest.json').read_text())
    if hashlib.sha256((session / 'baseline.blend').read_bytes()).hexdigest() != manifest['baseline_sha256']:
        raise RuntimeError('Example baseline hash differs from manifest')
    for asset in manifest['assets']:
        if asset['status'] == 'hashed':
            target = (session / asset['path']).resolve()
            if not target.is_relative_to(session) or hashlib.sha256(target.read_bytes()).hexdigest() != asset['sha256']:
                raise RuntimeError('Example external identity differs')
    add_on = [(ROOT / 'blender_invariants' / name, 'blender_invariants/' + name) for name in PACKAGE_FILES]
    add_on += [(ROOT / name, 'blender_invariants/' + name) for name in ['LICENSE', 'NOTICE.md', 'README.md']]
    write_zip(ARTIFACTS / 'InvariantLedger-0.1.0-addon.zip', add_on)
    example = [(session / name, name) for name in FIXTURE_FILES]
    example += [(ROOT / name, name) for name in ['README.md', 'NOTICE.md', 'LICENSE']]
    write_zip(ARTIFACTS / 'InvariantLedger-0.1.0-example.zip', example)
    (ROOT / 'docs/evidence.json').write_text(json.dumps(native, indent=2) + '\n')
    print('Native evidence and exact-path packages validated')


if __name__ == '__main__':
    build()
