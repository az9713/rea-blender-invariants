# SPDX-License-Identifier: GPL-2.0-or-later
"""Exact corresponding-source archive; no runtime, SDK, private handoff or caches."""
import hashlib,json,zipfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.scrub_synthetic_fixture import marker_values
from scripts.strip_png_metadata import strip
ROOT=Path(__file__).resolve().parents[1]
ROOTS=['.gitignore','LICENSE','NOTICE.md','README.md','blender_invariants','tests','scripts','docs','investigation/COMPARISON.md','investigation/public-source','artifacts/integration-results.json','artifacts/gui-status.json','artifacts/render-results.json','artifacts/fixture-privacy.json','artifacts/render-privacy.json','artifacts/release-v0.1.1-tests.json','artifacts/release-v0.1.1-privacy.json']

def build_source():
 files=[]
 for name in ROOTS:
  path=ROOT/name
  if path.is_dir():files.extend(p for p in path.rglob('*')if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'})
  elif path.is_file():files.append(path)
  else:raise RuntimeError('Missing public source: '+name)
 files=sorted(set(files));manifest=[];markers=marker_values(ROOT)
 for path in files:
  name=path.relative_to(ROOT).as_posix()
  if path.is_symlink() or not path.resolve().is_relative_to(ROOT) or any(p in {'.runtime','.git','__pycache__','node_modules'}for p in path.parts) or '.private.'in name:raise RuntimeError('Unsafe source path: '+name)
  data=path.read_bytes();lower=data.lower()
  for marker in markers:
   if marker.lower()in lower or marker.decode('utf-8').encode('utf-16le').lower()in lower:raise RuntimeError('Private marker in public source: '+name)
  if path.suffix.lower()=='.png':
   clean,report=strip(data)
   if clean!=data or report['removed_metadata_chunks']:raise RuntimeError('PNG textual/EXIF metadata remains: '+name)
  manifest.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
 output=ROOT/'artifacts/InvariantLedger-0.1.1-source.zip'
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,strict_timestamps=False)as archive:
  for path in files:archive.write(path,'InvariantLedger-source/'+path.relative_to(ROOT).as_posix())
  archive.writestr('InvariantLedger-source/SOURCE-MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
 with zipfile.ZipFile(output)as archive:
  if archive.testzip():raise RuntimeError('Source ZIP CRC failure')
 digest=hashlib.sha256(output.read_bytes()).hexdigest();output.with_suffix('.zip.sha256').write_text(digest+'  '+output.name+'\n')
 print(json.dumps({'name':output.name,'size':output.stat().st_size,'sha256':digest,'source_files':len(files),'runtime_or_private_handoff_included':False,'PNG_metadata_removed_and_pixel_bytes_preserved':True},indent=2))
if __name__=='__main__':build_source()
