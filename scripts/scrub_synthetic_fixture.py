# SPDX-License-Identifier: GPL-2.0-or-later
"""Release-only sanitation of our exact synthetic Blender 5.2 fixture.

This is not an arbitrary .blend privacy scrubber. It accepts only the pinned
uncompressed 17-byte-header/32-byte-block format, searches explicit local path
markers and clears bounded printable, NUL-terminated byte spans in known
metadata/image blocks. It never changes block lengths, pointers or addresses.
The active //assets/fixture.png string precedes stale image-path padding and is
preserved. Real Blender loading, external identity checks and replay must pass.
"""
import hashlib,json,struct
from pathlib import Path
HEADER=b'BLENDER17-01v0502'
ALLOWED={b'DATA',b'IM\0\0',b'GLOB'}

def marker_values(root):
 root=Path(root).resolve();values=[str(root),root.as_posix()]
 parts=root.parts
 for i,p in enumerate(parts[:-1]):
  if p.lower()=='users':
   prefix=Path(*parts[:i+2]);values.extend([str(prefix),prefix.as_posix()])
 if root.parent.name=='projects':values.append(root.parent.parent.name)
 return [x.lower().encode('utf-8') for x in values if x]

def blocks(data):
 if not data.startswith(HEADER):raise ValueError('Only our pinned uncompressed Blender5.2 fixture format is accepted')
 offset=len(HEADER);result=[]
 while offset+32<=len(data):
  length=struct.unpack_from('<Q',data,offset+16)[0]
  end=offset+32+length
  if end>len(data):raise ValueError('Block length exceeds file')
  code=bytes(data[offset:offset+4]);result.append((code,offset+32,end));offset=end
  if code==b'ENDB':
   if length!=0 or offset!=len(data):raise ValueError('Invalid end block')
   return result
 raise ValueError('No complete end block')

def sanitize(data,markers):
 data=bytearray(data);layout=blocks(data);spans=set();lower=bytes(data).lower()
 for marker in markers:
  if not marker:raise ValueError('Empty marker')
  start=0
  while True:
   hit=lower.find(marker.lower(),start)
   if hit<0:break
   block=next((b for b in layout if b[1]<=hit and hit+len(marker)<=b[2]),None)
   if block is None or block[0] not in ALLOWED:raise ValueError('Marker is outside reviewed metadata/image blocks')
   code,left,right=block
   begin=lower.rfind(b'\0',left,hit)+1
   if begin<left:raise ValueError('No bounded string/padding start')
   end=lower.find(b'\0',hit+len(marker),right)
   if end<0 or end-begin>2048:raise ValueError('No bounded string/padding end')
   if not all(32<=b<=126 for b in data[begin:end]):raise ValueError('Marker intersects non-printable structured data')
   spans.add((begin,end,code));start=hit+len(marker)
 for begin,end,code in spans:data[begin:end]=b'\0'*(end-begin)
 after=bytes(data)
 if len(after)!=len(lower) or blocks(after)!=layout:raise AssertionError('Structural block layout changed')
 for marker in markers:
  if marker.lower() in after.lower() or marker.decode('utf-8').encode('utf-16le').lower() in after.lower():raise ValueError('A marker remains after sanitation')
 return after,{'format':'Pinned uncompressed Blender5.2 fixture','bytes':len(after),'cleared_spans':len(spans),'cleared_bytes':sum(b-a for a,b,c in spans),'blocks':[{'code':c.rstrip(b'\0').decode('ascii'),'bytes_cleared':b-a}for a,b,c in sorted(spans)],'new_sha256':hashlib.sha256(after).hexdigest(),'structural_layout_unchanged':True,'known_local_markers_remaining':False,'scope':'Exact synthetic fixture only; clears matched printable metadata/path-padding spans, not an arbitrary user scene sanitizer'}

def scrub(path,root):
 path=Path(path);data=path.read_bytes();clean,report=sanitize(data,marker_values(root))
 path.write_bytes(clean)
 return report
