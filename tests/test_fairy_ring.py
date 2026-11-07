"""Bounded synthetic geometry and message validation; no expensive image rendering."""
import importlib.machinery
import importlib.util
import math
from pathlib import Path
import random
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "the fairy ring cipher"
loader = importlib.machinery.SourceFileLoader("fairy_ring_cipher", str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
cipher = importlib.util.module_from_spec(spec)
loader.exec_module(cipher)


class FairyRingTests(unittest.TestCase):
    def test_default_message_places_all_rings_deterministically(self):
        text = cipher.DEFAULT
        counts = [0 if c == " " else ord(c) - 64 for c in text]
        a = cipher.layout(counts, random.Random(cipher.SEED))
        b = cipher.layout(counts, random.Random(cipher.SEED))
        self.assertEqual(a, b)
        self.assertEqual(len(a), len(counts))
        for i, (x, y, r) in enumerate(a):
            self.assertTrue(r + 40 < x < cipher.W - r - 40)
            self.assertTrue(r + 40 < y < cipher.H - r - 140)
            for xx, yy, rr in a[:i]:
                self.assertGreater(math.hypot(x - xx, y - yy), r + rr + cipher.GAP)

    def test_impossible_long_message_terminates_explicitly(self):
        with self.assertRaisesRegex(ValueError, "30,000 attempts"):
            cipher.layout([26] * 80, random.Random(cipher.SEED))

    def test_layout_is_not_randomly_reseeded_by_guard(self):
        self.assertEqual(cipher.layout([1, 0, 2], random.Random(31)),
                         cipher.layout([1, 0, 2], random.Random(31)))

    def test_empty_and_punctuation_only_message_refused_without_writing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "image.png"
            for message in ("", "   ", "123?!"):
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError, "at least one"):
                        cipher.render(message, str(path))
                    self.assertFalse(path.exists())

    def test_unsupported_unicode_letters_refused_without_writing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "image.png"
            with self.assertRaisesRegex(ValueError, "Only A-Z"):
                cipher.render("étoile", str(path))
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
