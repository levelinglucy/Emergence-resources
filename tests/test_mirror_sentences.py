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
