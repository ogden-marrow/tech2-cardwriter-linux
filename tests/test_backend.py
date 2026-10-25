from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tech2_cardwriter.backend import (  # noqa: E402
    TEN_MB,
    THIRTY_TWO_MB,
    inspect_image,
)


class ImageInspectionTests(unittest.TestCase):
    def _image(self, size: int, name: str, magic: bytes = b"T2  ") -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / name
        with path.open("wb") as handle:
            handle.write(magic)
            handle.truncate(size)
        return path

    def test_148_32mb_is_valid(self) -> None:
        info = inspect_image(self._image(THIRTY_TWO_MB, "Saab 148.bin"))
        self.assertTrue(info.magic_ok)
        self.assertTrue(info.size_ok)
        self.assertTrue(info.valid)
        self.assertEqual(info.version, 148)
        self.assertIn("9-5", info.coverage)

    def test_44_10mb_is_valid_for_900(self) -> None:
        info = inspect_image(self._image(TEN_MB, "Saab 44.bin"), car="900")
        self.assertTrue(info.valid)
        self.assertEqual(info.version, 44)
        self.assertEqual(info.size_mb, 10)

    def test_44_warns_for_9_5(self) -> None:
        info = inspect_image(self._image(TEN_MB, "Saab 44.bin"), car="9-5")
        self.assertTrue(any("not the 9-5" in warning for warning in info.warnings))

    def test_bad_magic_is_invalid(self) -> None:
        info = inspect_image(self._image(THIRTY_TWO_MB, "Saab 148.bin", magic=b"NOPE"))
        self.assertFalse(info.magic_ok)
        self.assertFalse(info.valid)
        self.assertTrue(any("T2" in warning for warning in info.warnings))

    def test_wrong_size_warns(self) -> None:
        info = inspect_image(self._image(1024, "Saab 148.bin"))
        self.assertFalse(info.size_ok)
        self.assertFalse(info.valid)


if __name__ == "__main__":
    unittest.main()
