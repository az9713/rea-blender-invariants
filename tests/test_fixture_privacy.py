import struct,unittest
from scripts.scrub_synthetic_fixture import HEADER,blocks,sanitize

def fixture(code,payload):
 return HEADER+code+b'\0'*4+struct.pack('<QQII',16,len(payload),1,0)+payload+b'ENDB'+b'\0'*28
class FixturePrivacyTests(unittest.TestCase):
 def test_cached_folder_cleared(self):
  data=fixture(b'DATA',b'\0C:/LOCAL_PRIVATE/Documents\0padding')
  clean,report=sanitize(data,[b'local_private']);self.assertNotIn(b'LOCAL_PRIVATE',clean);self.assertEqual(report['cleared_spans'],1);self.assertEqual(len(data),len(clean));self.assertEqual(blocks(data),blocks(clean))
 def test_relative_asset_and_stale_padding(self):
  data=fixture(b'IM\0\0',b'\0//assets/fixture.png\0stale/PRIVATE_FOLDER/fixture.png\0')
  clean,report=sanitize(data,[b'private_folder']);self.assertIn(b'//assets/fixture.png\0',clean);self.assertNotIn(b'PRIVATE_FOLDER',clean);self.assertEqual(report['cleared_spans'],1)
 def test_unknown_block_refused(self):
  with self.assertRaises(ValueError):sanitize(fixture(b'DNA1',b'\0PRIVATE\0'),[b'private'])
 def test_nonprintable_refused(self):
  with self.assertRaises(ValueError):sanitize(fixture(b'DATA',b'\0PRIVATE\x01buffer\0'),[b'private'])
 def test_unterminated_refused(self):
  with self.assertRaises(ValueError):sanitize(fixture(b'DATA',b'\0PRIVATE'),[b'private'])
 def test_idempotent(self):
  a,r=sanitize(fixture(b'DATA',b'\0PRIVATE\0'),[b'private']);b,s=sanitize(a,[b'private']);self.assertEqual(a,b);self.assertEqual(s['cleared_spans'],0)
 def test_wrong_header_refused(self):
  with self.assertRaises(ValueError):sanitize(b'not a blend',[b'private'])
 def test_broken_length_refused(self):
  data=bytearray(fixture(b'DATA',b'\0PRIVATE\0'));struct.pack_into('<Q',data,len(HEADER)+16,9999999)
  with self.assertRaises(ValueError):sanitize(data,[b'private'])
if __name__=='__main__':unittest.main()
