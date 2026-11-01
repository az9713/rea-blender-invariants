"""Acquire a separate official Blender portable; all state remains in this checkout."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
NAME = 'blender-5.2.3-windows-x64.zip'
BASES = ['https://mirror.blender.org/release/Blender5.2/',
         'https://mirrors.ocf.berkeley.edu/blender/release/Blender5.2/']


def acquire():
    RUNTIME.mkdir(exist_ok=True)
    errors = []
    for base in BASES:
        try:
            checksums = urllib.request.urlopen(base + 'blender-5.2.3.sha256', timeout=45).read().decode()
            expected = next(line.split()[0] for line in checksums.splitlines() if NAME in line)
            break
        except Exception as error:
            errors.append(str(error))
    else:
        raise RuntimeError('No upstream checksum source available: ' + '; '.join(errors))
    archive = RUNTIME / NAME
    if not archive.exists():
        with urllib.request.urlopen(base + NAME, timeout=120) as source, archive.open('wb') as dest:
            while chunk := source.read(4 * 1024 * 1024):
                dest.write(chunk)
        print('Downloaded', NAME, flush=True)
    actual = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    if actual != expected.lower():
        raise RuntimeError('Publisher SHA256 mismatch')
    output = RUNTIME / 'blender'
    output.mkdir(exist_ok=True)
    if not list(output.rglob('blender.exe')):
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if not (output / name).resolve().is_relative_to(output.resolve()):
                    raise RuntimeError('Archive path escapes portable directory')
            bundle.extractall(output)
    data = {'version': '5.2.3', 'url': base + NAME, 'sha256': actual,
            'checksum_url': base + 'blender-5.2.3.sha256'}
    (RUNTIME / 'portable-manifest.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps(data), flush=True)


if __name__ == '__main__':
    acquire()
