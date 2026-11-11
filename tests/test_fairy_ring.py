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

    def test_disposable_full_canvas_render_with_short_diffusion(self):
        """Exercise real diffusion, drawing, and exclusive PNG publication together.

        Only the field simulation is shortened to keep CI fast. This is not a
        visual check of the production 6,000-step reaction-diffusion artwork.
        """
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "smoke.png"
            original_diffusion = cipher.gray_scott

            def quick_field(rings):
                return original_diffusion(rings, size=32, steps=12)

            with patch.object(cipher, "gray_scott", side_effect=quick_field):
                counts, rings = cipher.render("A B", str(target))

            self.assertEqual(counts, [1, 0, 2])
            self.assertEqual(len(rings), 3)
            self.assertTrue(target.read_bytes().startswith(b"\\x89PNG\\r\\n\\x1a\\n"))
            with cipher.Image.open(target) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (cipher.W, cipher.H))
                image.verify()
            self.assertEqual([p.name for p in target.parent.iterdir()], ["smoke.png"])

    def test_completed_png_saved_without_overwriting_existing_art(self):
        """An earlier generated image must survive a second run unchanged."""
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "fairy.png"
            cipher.save_png_exclusively(cipher.Image.new("RGB", (3, 2), "red"), path)
            original = path.read_bytes()
            with cipher.Image.open(path) as saved:
                self.assertEqual(saved.size, (3, 2))
                saved.verify()
            with self.assertRaisesRegex(ValueError, "already exists"):
                cipher.save_png_exclusively(cipher.Image.new("RGB", (3, 2), "blue"), path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["fairy.png"])

    def test_failed_png_encode_leaves_no_published_or_staged_file(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "fairy.png"
            with patch.object(cipher.Image.Image, "save", side_effect=OSError("encode failed")):
                with self.assertRaisesRegex(OSError, "encode failed"):
                    cipher.save_png_exclusively(cipher.Image.new("RGB", (3, 2)), path)
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_late_collision_does_not_replace_other_writer_file(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "fairy.png"
            def competing_writer(source, dest):
                Path(dest).write_bytes(b"another writer won")
                raise FileExistsError(dest)
            with patch.object(cipher.os, "link", side_effect=competing_writer):
                with self.assertRaisesRegex(ValueError, "already exists"):
                    cipher.save_png_exclusively(cipher.Image.new("RGB", (3, 2)), path)
            self.assertEqual(path.read_bytes(), b"another writer won")
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["fairy.png"])

    def test_existing_output_rejected_before_expensive_field_simulation(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "fairy.png"
            path.write_bytes(b"old original art")
            with patch.object(cipher, "gray_scott", side_effect=AssertionError("should not run")):
                with self.assertRaisesRegex(ValueError, "already exists"):
                    cipher.render("A", path)
            self.assertEqual(path.read_bytes(), b"old original art")


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

    def test_ascii_case_and_punctuation_map_to_original_ring_counts(self):
        self.assertEqual(cipher.message_counts("aZ ? b!"), [1, 26, 0, 0, 2])
        self.assertEqual(
            cipher.message_counts(cipher.DEFAULT),
            [0 if c == " " else ord(c) - 64 for c in cipher.DEFAULT],
        )

    def test_unicode_letters_that_uppercase_to_ascii_are_refused(self):
        """Unicode case expansions must not silently change a user's message."""
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "image.png"
            for message in ("straße", "ı", "ﬃ", "ſ", "e\u0301"):
                with self.subTest(message=message):
                    with patch.object(cipher, "gray_scott",
                                      side_effect=AssertionError("field simulation must not run")):
                        with self.assertRaisesRegex(ValueError, "Only A-Z"):
                            cipher.render(message, str(path))
                    self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
