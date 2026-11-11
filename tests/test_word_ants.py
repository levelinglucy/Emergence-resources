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


if __name__ == "__main__":
    unittest.main()
