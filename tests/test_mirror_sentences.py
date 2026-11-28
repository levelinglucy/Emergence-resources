"""Regression tests for the actual no-extension Mirror sentences CLI."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import runpy
import subprocess
import sys
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "mayas mirrored sentences"
MODULE = runpy.run_path(str(SOURCE))
Mirror = MODULE["Mirror"]
main = MODULE["main"]


class MirrorProofTests(unittest.TestCase):
    def proof_for(self, opening, text):
        output = io.StringIO()
        args = [str(SOURCE), "--opening", opening, "--letters", "z",
                "--no-total", "--seconds", "0"]
        # Inject the exact candidate to isolate proof display from search.
        with patch.object(Mirror, "search", return_value=(text, 1)):
            with patch.object(sys, "argv", args), redirect_stdout(output):
                main()
        return output.getvalue()

    def test_terminal_singular(self):
        out = self.proof_for("Here are ", "Here are one z.")
        self.assertIn("z: says 1, really 1  true", out)

    def test_empty_opening(self):
        out = self.proof_for("", "one z.")
        self.assertIn("z: says 1, really 1  true", out)

    def test_count_above_199(self):
        opening = "z" * 200 + " Here are "
        out = self.proof_for(opening, opening + "two hundred and one z's.")
        self.assertIn("z: says 201, really 201  true", out)

    def test_decoy_in_opening_does_not_verify_wrong_claim(self):
        opening = "There are two z's. Here are "
        out = self.proof_for(opening, opening + "nine z's.")
        self.assertNotIn("z: says 2, really 2  true", out)
        self.assertIn("FALSE", out)

    def test_wrong_count_rejected(self):
        out = self.proof_for("Here are ", "Here are two z's.")
        self.assertIn("FALSE", out)

    def test_literal_opening_and_custom_ending(self):
        model = Mirror("Here are ", "z", False, ending="!")
        self.assertTrue(model.verify("Here are one z!"))
        self.assertFalse(model.verify("Here are one z."))
        self.assertFalse(model.verify("here are one z!"))

    def test_decoy_opening_can_itself_contain_unverified_prose(self):
        opening = "There are nine z's. Here are "
        model = Mirror(opening, "z", False)
        self.assertTrue(model.verify(opening + "two z's."))
        self.assertFalse(model.verify(opening + "nine z's."))

    def test_gallery_template_checks_total_and_order(self):
        for letters, sentence in zip(MODULE["GALLERY_LETTERS"], MODULE["GALLERY"]):
            with self.subTest(letters=letters):
                model = Mirror(MODULE["GALLERY_OPENING"], letters)
                self.assertTrue(model.verify(sentence))
                self.assertFalse(model.verify(sentence[:-1] + "!"))
        first = MODULE["GALLERY"][0]
        model = Mirror(MODULE["GALLERY_OPENING"], "aeiou")
        self.assertFalse(model.verify(first.replace("forty-five", "forty-six")))
        self.assertFalse(Mirror(MODULE["GALLERY_OPENING"], "eaiou").verify(first))

    def test_legacy_check_keeps_original_return_shape(self):
        ok, rows, total = MODULE["check"]("Here are two z's.", "z", False)
        self.assertFalse(ok)
        self.assertEqual(rows, [("z", 2, 1, False)])
        self.assertIsNone(total)

    def test_original_gallery(self):
        result = subprocess.run([sys.executable, str(SOURCE)],
                                stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, check=True, timeout=10)
        self.assertEqual(result.stdout.count("-> all true"), 5)
        self.assertNotIn("FALSE", result.stdout)

    def test_real_seeded_single_letter_search(self):
        result = subprocess.run(
            [sys.executable, str(SOURCE), "--opening", "", "--letters", "z",
             "--no-total", "--seed", "7", "--seconds", "2"],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            check=True, timeout=10)
        self.assertIn("one z.", result.stdout)
        self.assertIn("z: says 1, really 1  true", result.stdout)
        self.assertNotIn("FALSE", result.stdout)


if __name__ == "__main__":
    unittest.main()
