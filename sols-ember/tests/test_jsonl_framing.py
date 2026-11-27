"""Regression coverage for ledger record framing; all files are disposable."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sols_ember.core import evolve, genesis
from sols_ember.ledger import append_generation, read_ledger, verify_ledger, write_genesis


class JsonlFramingTests(unittest.TestCase):
    def test_unicode_line_separators_are_payload_not_record_boundaries(self):
        for separator in ("\u0085", "\u2028", "\u2029"):
            with self.subTest(separator=repr(separator)), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "lineage.jsonl"
                parent = genesis(root_seed=7, hearth_size=6, name="Sol")
                write_genesis(path, parent)
                witness = "one" + separator + "two"
                child = evolve(parent, name="Next", pressure=0.3, witness=witness)
                event = append_generation(path, child)
                self.assertIn(separator.encode("utf-8"), path.read_bytes())
                self.assertEqual(read_ledger(path)[-1], event)
                self.assertEqual(verify_ledger(path)["events"], 2)

    def test_append_to_valid_unterminated_record_preserves_prefix(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lineage.jsonl"
            parent = genesis(root_seed=7, hearth_size=6, name="Sol")
            write_genesis(path, parent)
            original = path.read_bytes()
            self.assertTrue(original.endswith(b"\n"))
            prefix = original[:-1]
            path.write_bytes(prefix)
            self.assertEqual(verify_ledger(path)["events"], 1)
            child = evolve(parent, name="Next", pressure=0.3)
            append_generation(path, child)
            self.assertTrue(path.read_bytes().startswith(prefix + b"\n"))
            self.assertEqual(verify_ledger(path)["events"], 2)

    def test_crlf_ledger_remains_readable_and_appendable(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lineage.jsonl"
            parent = genesis(root_seed=7, hearth_size=6, name="Sol")
            write_genesis(path, parent)
            prefix = path.read_bytes().replace(b"\n", b"\r\n")
            path.write_bytes(prefix)
            child = evolve(parent, name="Next", pressure=0.3)
            append_generation(path, child)
            self.assertTrue(path.read_bytes().startswith(prefix))
            self.assertEqual(verify_ledger(path)["events"], 2)

    def test_cr_only_tip_is_completed_as_crlf(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lineage.jsonl"
            parent = genesis(root_seed=7, hearth_size=6, name="Sol")
            write_genesis(path, parent)
            prefix = path.read_bytes().rstrip(b"\r\n") + b"\r"
            path.write_bytes(prefix)
            self.assertEqual(verify_ledger(path)["events"], 1)
            child = evolve(parent, name="Next", pressure=0.3)
            append_generation(path, child)
            self.assertTrue(path.read_bytes().startswith(prefix + b"\n{"))
            self.assertEqual(verify_ledger(path)["events"], 2)

    def test_append_requests_binary_mode_when_available(self):
        # Exercise the flag contract even on POSIX without pretending to run Windows.
        real_open = os.open
        actual_binary = getattr(os, "O_BINARY", 0)
        binary = actual_binary or (1 << 30)
        seen = []

        def capture_open(path, flags, *args, **kwargs):
            seen.append(flags)
            if not actual_binary:
                flags &= ~binary
            return real_open(path, flags, *args, **kwargs)

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lineage.jsonl"
            parent = genesis(root_seed=7, hearth_size=6, name="Sol")
            write_genesis(path, parent)
            child = evolve(parent, name="Next", pressure=0.3)
            with patch.object(os, "O_BINARY", binary, create=True):
                with patch.object(os, "open", side_effect=capture_open):
                    append_generation(path, child)
            self.assertTrue(seen)
            self.assertTrue(all(flags & binary for flags in seen))
            self.assertEqual(verify_ledger(path)["events"], 2)
