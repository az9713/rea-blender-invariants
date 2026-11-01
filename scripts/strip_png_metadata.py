# SPDX-License-Identifier: GPL-2.0-or-later
"""Remove textual/EXIF metadata from owned generated PNGs, retaining image bytes."""
import hashlib,json,struct,zlib
from pathlib import Path
SIGNATURE=b'\x89PNG\r\n\x1a\n'
REMOVE={b'tEXt',b'zTXt',b'iTXt',b'eXIf'}

def strip(data):
 if not data.startswith(SIGNATURE) or len(data)>50_000_000:raise ValueError('Expected bounded PNG')
 offset=8;output=bytearray(SIGNATURE);idat=[];removed=[];keys=[];seen_end=False
 while offset+12<=len(data):
  size=struct.unpack_from('>I',data,offset)[0];kind=data[offset+4:offset+8];end=offset+12+size
  if end>len(data):raise ValueError('Truncated PNG chunk')
  payload=data[offset+8:offset+8+size];crc=struct.unpack_from('>I',data,offset+8+size)[0]
  if zlib.crc32(kind+payload)&0xffffffff!=crc:raise ValueError('PNG CRC mismatch')
  if kind==b'IDAT':idat.append(payload)
  if kind in REMOVE:
   removed.append(kind.decode('ascii'));keys.append(payload.split(b'\0',1)[0].decode('latin1') if kind!=b'eXIf' else '(EXIF)')
  else:output.extend(data[offset:end])
  offset=end
  if kind==b'IEND':
   if size or offset!=len(data):raise ValueError('Invalid PNG end/trailing bytes')
   seen_end=True;break
 if not seen_end or not idat:raise ValueError('Incomplete PNG')
 clean=bytes(output)
 return clean,{'removed_metadata_chunks':removed,'removed_metadata_keys':keys,'image_data_sha256':hashlib.sha256(b''.join(idat)).hexdigest(),'retained_image_data_bytes':sum(map(len,idat)),'IDAT_bytes_preserved':True,'new_png_sha256':hashlib.sha256(clean).hexdigest()}

def strip_generated(root):
 root=Path(root).resolve();reports=[]
 for name in ['native-before.png','native-after.png']:
  path=root/'docs'/name;old=path.read_bytes();clean,report=strip(old)
  backup=root/'.runtime'/('pre-v0.1.1-'+name)
  if not backup.exists():backup.write_bytes(old)
  path.write_bytes(clean);reports.append(dict(report,file=name))
 result={'passed':True,'scope':'Owned original synthetic render PNGs only; textual/EXIF metadata removed without decoding or changing pixel/image bytes','images':reports}
 (root/'artifacts/render-privacy.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
if __name__=='__main__':strip_generated(Path(__file__).resolve().parents[1])
