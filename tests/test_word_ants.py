"""Fast, disposable tests of Word ants' actual PNG output path."""
import importlib.machinery
import importlib.util
import io
from contextlib import redirect_stderr
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "Word ants"
loader = importlib.machinery.SourceFileLoader("word_ants", str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
ants = importlib.util.module_from_spec(spec)
loader.exec_module(ants)


class WordAntPublicationTests(unittest.TestCase):
    def test_disposable_real_drawing_and_no_overwrite_on_second_run(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ants.png"
            args = ["--steps", "4", "--out", str(path), "ember"]
            with redirect_stderr(io.StringIO()):
                ants.main(args)
            first = path.read_bytes()
            with ants.Image.open(path) as art:
                self.assertEqual(art.format, "PNG")
                self.assertEqual(art.size, (416, 668))
                art.verify()
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as refused:
                    ants.main(args)
            self.assertEqual(refused.exception.code, 2)
            self.assertEqual(path.read_bytes(), first)
            self.assertEqual([p.name for p in Path(folder).iterdir()], ["ants.png"])

    def test_png_encoder_failure_never_publishes_partial_art(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "failed.png"
            with patch.object(ants.Image.Image, "save", side_effect=OSError("encode interrupted")):
                with self.assertRaisesRegex(OSError, "encode interrupted"):
                    ants.save_png_exclusively(ants.Image.new("RGB", (3, 3)), path)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_late_filename_collision_preserves_other_writers_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "shared.png"
            def competing_writer(staged, dest):
                Path(dest).write_bytes(b"OTHER WRITER")
                raise FileExistsError("target appeared")
            with patch.object(ants.os, "link", side_effect=competing_writer):
                with self.assertRaises(FileExistsError):
                    ants.save_png_exclusively(ants.Image.new("RGB", (3, 3)), path)
            self.assertEqual(path.read_bytes(), b"OTHER WRITER")
            self.assertEqual([p.name for p in Path(folder).iterdir()], ["shared.png"])


    def test_compatibility_digits_have_their_numeric_value(self):
        # Existing ASCII and Arabic-Indic digits keep their values.
        # Superscripts, circled numerals and circled zero are also isdigit().
        numbers = ants.numerology("A²٣⑨⓿z")
        self.assertEqual(numbers, [1, 2, 3, 9, 0, 8])
        self.assertEqual(ants.rule_from(numbers), "RLRRLL")

    def test_compatibility_digit_draws_a_real_disposable_image(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "unicode.png"
            with redirect_stderr(io.StringIO()):
                ants.main(["--steps", "12", "--out", str(path), "A²"])
            with ants.Image.open(path) as art:
                self.assertEqual(art.format, "PNG")
                art.verify()
            self.assertEqual([p.name for p in Path(folder).iterdir()], ["unicode.png"])


    def test_short_mixed_rule_keeps_compact_byte_cells(self):
        grid, _, taken = ants.walk("LR", 80, size=32)
        self.assertIsInstance(grid, bytearray)
        self.assertEqual(taken, 80)

    def test_257_colour_rule_keeps_states_above_255(self):
        # A legitimate numerology word with 256 left turns and one right.
        word = "b" * 256 + "a"
        rule = ants.rule_from(ants.numerology(word))
        self.assertEqual(rule, "L" * 256 + "R")
        grid, _, taken = ants.walk(rule, 1032, size=32)
        self.assertEqual(taken, 1032)
        self.assertGreaterEqual(max(grid), 256)
        self.assertGreaterEqual(grid.itemsize, 2)  # widened cell representation

    def test_65537_colour_rule_uses_at_least_32_bit_cells(self):
        rule = "L" * 65536 + "R"
        grid, _, taken = ants.walk(rule, 1032, size=32)
        self.assertEqual(taken, 1032)
        self.assertGreaterEqual(max(grid), 256)
        self.assertGreaterEqual(grid.itemsize, 4)

    def test_257_colour_word_publishes_a_complete_png_once(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wide.png"
            args = ["--steps", "1032", "--out", str(path), "b" * 256 + "a"]
            with redirect_stderr(io.StringIO()):
                ants.main(args)
            with ants.Image.open(path) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (416, 668))
                image.verify()
            original = path.read_bytes()
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    ants.main(args)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual([p.name for p in Path(folder).iterdir()], ["wide.png"])



class WordAntCaptionTests(unittest.TestCase):
    def capture_captions(self, word, fonts):
        # Observe real drawing calls, measuring using the very same fonts,
        # positions and anchors. The original renderer still produces pixels.
        original = ants.ImageDraw.ImageDraw.text
        labels = []
        def observe(draw, xy, text, *args, **kwargs):
            if xy[1] >= 380:
                bounds = draw.textbbox(xy, text, font=kwargs["font"],
                                       anchor=kwargs.get("anchor"))
                labels.append((text, bounds))
            return original(draw, xy, text, *args, **kwargs)
        with patch.object(ants.ImageDraw.ImageDraw, "text", observe):
            panel = ants.render_panel(word, 1032, 380, fonts)
        return panel, labels

    def test_long_caption_calls_fit_without_overlap(self):
        fonts = (ants.ImageFont.truetype("DejaVuSans.ttf", 30),
                 ants.ImageFont.truetype("DejaVuSans.ttf", 18),
                 ants.ImageFont.truetype("DejaVuSansMono.ttf", 17))
        for word in ("interoperability", "b" * 256 + "a"):
            with self.subTest(word=word):
                panel, labels = self.capture_captions(word, fonts)
                self.assertEqual(len(labels), 4)
                for text, (left, top, right, bottom) in labels:
                    self.assertTrue(0 <= left <= right <= panel.width,
                                    (text, left, right))
                    self.assertTrue(380 <= top <= bottom <= panel.height,
                                    (text, top, bottom))
                for i, (a, (l, t, r, b)) in enumerate(labels):
                    for other, (ol, ot, or_, ob) in labels[i+1:]:
                        self.assertFalse(l < or_ and ol < r and t < ob and ot < b,
                                         (a, other))

    def test_short_caption_preserves_original_text(self):
        panel, labels = self.capture_captions("ember", ants.load_fonts())
        texts = [text for text, _ in labels]
        nums = ants.numerology("ember")
        self.assertIn("ember", texts)
        self.assertIn(" ".join(map(str, nums)), texts)
        self.assertIn(ants.rule_from(nums), texts)
        self.assertEqual(panel.width, 380)


if __name__ == "__main__":
    unittest.main()
