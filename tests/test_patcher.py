import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

from bps import PatchError, apply_bps, encode_number
import casino_patcher as app

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_patch import create_patch


def bps(source, target, actions):
    data = b"BPS1" + encode_number(len(source)) + encode_number(len(target)) + encode_number(0) + actions
    data += struct.pack("<II", zlib.crc32(source), zlib.crc32(target))
    return data + struct.pack("<I", zlib.crc32(data))


class BpsTests(unittest.TestCase):
    def test_roundtrip_chunk_boundaries(self):
        source = bytes(140000)
        target = bytearray(source)
        target[65534:65539] = b"hello"
        target[130000] = 1
        target = bytes(target)
        self.assertEqual(apply_bps(source, create_patch(source, target), max_size=len(target)), target)

    def test_source_copy_and_overlapping_target_copy(self):
        source, target = b"abcdef", b"cdefzzzz"
        actions = encode_number((3 << 2) | 2) + encode_number(4)
        actions += encode_number(1) + b"z"
        actions += encode_number((2 << 2) | 3) + encode_number(8)
        self.assertEqual(apply_bps(source, bps(source, target, actions), max_size=8), target)

    def test_corrupt_patch_and_wrong_source(self):
        source, target = b"abcd", b"abXd"
        data = create_patch(source, target)
        with self.assertRaises(PatchError):
            apply_bps(source, data[:-1] + bytes([data[-1] ^ 1]), max_size=4)
        with self.assertRaises(PatchError):
            apply_bps(b"efgh", data, max_size=4)

    def test_invalid_target_copy_and_oversized_output(self):
        with self.assertRaises(PatchError):
            apply_bps(b"a", bps(b"a", b"a", encode_number(3) + encode_number(0)), max_size=1)
        with self.assertRaises(PatchError):
            apply_bps(b"ab", create_patch(b"ab", b"cd"), max_size=1)


class IOTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_never_overwrites_existing_output(self):
        dest = self.root / "original.nds"
        dest.write_bytes(b"keep")
        with self.assertRaises(PatchError):
            app.write_output(dest, "original.nds", b"new")
        self.assertEqual(dest.read_bytes(), b"keep")

    def test_zip_output_preserves_rom_name(self):
        dest = self.root / "restored.zip"
        app.write_output(dest, "Original Name.nds", b"test")
        with zipfile.ZipFile(dest) as archive:
            self.assertEqual(archive.namelist(), ["Original Name.nds"])
            self.assertEqual(archive.read("Original Name.nds"), b"test")

    def test_zip_validation_without_large_fixture(self):
        data = bytes(12) + b"CPUS" + bytes(16)
        dest = self.root / "input.zip"
        with zipfile.ZipFile(dest, "w") as archive:
            archive.writestr("folder/game.nds", data)
        with patch.object(app, "ROM_SIZE", len(data)), patch.object(app, "SOURCE_SHA256", hashlib.sha256(data).hexdigest()):
            self.assertEqual(app.read_rom(dest), (data, "game.nds"))
        with zipfile.ZipFile(dest, "a") as archive:
            archive.writestr("second.nds", data)
        with self.assertRaises(PatchError):
            app.read_rom(dest)

    def test_rejects_wrong_and_already_patched_roms(self):
        data = bytes(32)
        dest = self.root / "input.nds"
        dest.write_bytes(data)
        with patch.object(app, "ROM_SIZE", 32):
            with self.assertRaisesRegex(PatchError, "edición española"):
                app.read_rom(dest)
            with patch.object(app, "TARGET_SHA256", hashlib.sha256(data).hexdigest()):
                with self.assertRaisesRegex(PatchError, "ya tiene"):
                    app.read_rom(dest)

    def test_installed_patch_integrity(self):
        data = (Path(__file__).resolve().parents[1] / "patches" / app.PATCH_NAME).read_bytes()
        self.assertEqual(data[:4], b"BPS1")
        self.assertEqual(zlib.crc32(data[:-4]), struct.unpack_from("<I", data, len(data) - 4)[0])


if __name__ == "__main__":
    unittest.main()
