import struct,unittest,zlib
from scripts.strip_png_metadata import SIGNATURE,strip

def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
def png(text=True):return SIGNATURE+chunk(b'IHDR',b'header')+(chunk(b'tEXt',b'File\0private/local/path')if text else b'')+chunk(b'IDAT',b'unchanged compressed pixel bytes')+chunk(b'IEND',b'')
class PngPrivacyTests(unittest.TestCase):
 def test_metadata_removed_without_pixel_changes(self):
  data=png();clean,r=strip(data);self.assertNotIn(b'private/local/path',clean);self.assertIn(b'unchanged compressed pixel bytes',clean);self.assertTrue(r['IDAT_bytes_preserved']);self.assertEqual(r['removed_metadata_chunks'],['tEXt'])
 def test_idempotent(self):
  a,r=strip(png());b,s=strip(a);self.assertEqual(a,b);self.assertEqual(s['removed_metadata_chunks'],[])
 def test_bad_crc_refused(self):
  data=bytearray(png());data[20]^=1
  with self.assertRaises(ValueError):strip(data)
 def test_truncated_refused(self):
  with self.assertRaises(ValueError):strip(png()[:-3])
 def test_wrong_format_refused(self):
  with self.assertRaises(ValueError):strip(b'not png')
 def test_nonmetadata_chunks_preserved(self):
  data=png(False);clean,r=strip(data);self.assertEqual(data,clean)
if __name__=='__main__':unittest.main()
