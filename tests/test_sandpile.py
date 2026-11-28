"""Bounded real-encoder and output-publication regression checks."""
import contextlib
import io
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "The sandpile"


class SandpilePublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.main = runpy.run_path(str(SOURCE))["main"]
        self.env = self.main.__globals__
        # Short synthetic generation, not a change to the original defaults.
        self.env.update(TARGET=12.0, WARMUP=3000)
        self.target = self.root / "piece.mp3"

    def generate(self, target=None):
        target = self.target if target is None else target
        with patch.object(sys, "argv", [str(SOURCE), "--seed", "31", "--out", str(target)]):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.main()

    def test_real_encoding_and_repeat(self):
        self.generate()
        original = self.target.read_bytes()
        self.assertGreater(len(original), 1000)
        self.assertEqual(original[:2], b"\xff\xfb")
        with self.assertRaises(SystemExit) as exc:
            self.generate()
        self.assertEqual(exc.exception.code, 2)
        self.assertEqual(self.target.read_bytes(), original)
        self.assertEqual(list(self.root.iterdir()), [self.target])

    def test_existing_file_refused_before_synthesis(self):
        self.target.write_bytes(b"previous recording")
        with patch.object(self.env["np"].random, "default_rng", side_effect=AssertionError("synthesis started")):
            with self.assertRaises(SystemExit):
                self.generate()
        self.assertEqual(self.target.read_bytes(), b"previous recording")

    def test_existing_and_dangling_symlinks(self):
        existing = self.root / "existing.mp3"
        existing.write_bytes(b"previous recording")
        absent = self.root / "absent.mp3"
        for destination in (existing, absent):
            with self.subTest(destination=destination):
                self.target.symlink_to(destination)
                try:
                    with self.assertRaises(SystemExit):
                        self.generate()
                    self.assertTrue(self.target.is_symlink())
                finally:
                    self.target.unlink()
        self.assertEqual(existing.read_bytes(), b"previous recording")
        self.assertFalse(absent.exists())

    def test_late_collision_preserves_competing_output(self):
        link = os.link

        def competing_writer(stage, target):
            Path(target).write_bytes(b"competing recording")
            link(stage, target)

        with patch.object(os, "link", side_effect=competing_writer):
            with self.assertRaises(SystemExit):
                self.generate()
        self.assertEqual(self.target.read_bytes(), b"competing recording")
        self.assertEqual(list(self.root.iterdir()), [self.target])

    def test_link_failure_leaves_no_output_or_stage(self):
        with patch.object(os, "link", side_effect=OSError("publication unavailable")):
            with self.assertRaisesRegex(OSError, "publication unavailable"):
                self.generate()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_partial_stage_write_leaves_no_output(self):
        make_temp = tempfile.NamedTemporaryFile

        @contextlib.contextmanager
        def broken_stage(*args, **kwargs):
            with make_temp(*args, **kwargs) as handle:
                write = handle.write

                def partial(data):
                    write(data[:20])
                    raise OSError("injected stage write error")

                with patch.object(handle, "write", side_effect=partial):
                    yield handle

        with patch.object(tempfile, "NamedTemporaryFile", side_effect=broken_stage):
            with self.assertRaisesRegex(OSError, "injected stage write error"):
                self.generate()
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
