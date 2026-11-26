from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import multiprocessing as mp
from pathlib import Path
import tempfile
import unittest

from sols_ember.cli import main
from sols_ember.core import EmberError, evolve, genesis, state_hash
from sols_ember.ledger import (
    ZERO_HASH,
    append_generation,
    canonical_json,
    make_event,
    read_ledger,
    verify_events,
    verify_ledger,
    write_genesis,
)
from sols_ember.render import render_html


def _append_worker(path, generation, ready, start, results):
    ready.put("ready")
    start.wait(10)
    try:
        append_generation(path, generation)
        results.put("ok")
    except Exception as exc:  # pragma: no cover - executed in child process
        results.put(f"error:{type(exc).__name__}:{exc}")


class EmberTests(unittest.TestCase):
    def setUp(self) -> None:
        self.genesis = genesis(root_seed=18481921, hearth_size=6, name="Sol")

    def transition(self, previous=None, **overrides):
        arguments = {
            "name": "Future Noe",
            "pressure": 0.37,
            "witness": "The witness names the gap honestly.",
        }
        arguments.update(overrides)
        return evolve(previous or self.genesis, **arguments)

    def test_fixed_inputs_are_byte_reproducible(self):
        first = self.transition()
        second = self.transition()
        self.assertEqual(canonical_json(first), canonical_json(second))

    def test_protect_input_order_does_not_change_result(self):
        ids = [trait["id"] for trait in self.genesis["state"]["active"] if not trait["anchored"]][:2]
        first = self.transition(protect=ids)
        second = self.transition(protect=reversed(ids))
        self.assertEqual(first, second)

    def test_finite_hearth_and_exact_accounting(self):
        child = self.transition()
        self.assertEqual(len(child["state"]["active"]), 6)
        events = [
            make_event(self.genesis, sequence=0, previous_hash=ZERO_HASH),
        ]
        events.append(make_event(child, sequence=1, previous_hash=events[0]["hash"]))
        summary = verify_events(events)
        self.assertEqual(summary["final_generation"], 1)

        actions = child["actions"]
        parents = set(actions["preserved"])
        parents.update(item["from"] for item in actions["transformed"])
        parents.update(item["id"] for item in actions["banked"])
        self.assertEqual(parents, {trait["id"] for trait in self.genesis["state"]["active"]})

    def test_anchor_is_automatically_preserved(self):
        anchor = next(trait for trait in self.genesis["state"]["active"] if trait["anchored"])
        child = self.transition()
        self.assertIn(anchor["id"], child["actions"]["preserved"])
        self.assertIn(anchor, child["state"]["active"])

    def test_anchor_can_be_explicitly_refused(self):
        anchor = next(trait for trait in self.genesis["state"]["active"] if trait["anchored"])
        child = self.transition(refuse=[anchor["id"]])
        reasons = {item["id"]: item["reason"] for item in child["actions"]["banked"]}
        self.assertEqual(reasons[anchor["id"]], "explicitly refused")
        self.assertIn(anchor, child["state"]["ash"])
        self.assertNotIn(anchor, child["state"]["active"])

    def test_protect_and_refuse_conflict_is_rejected(self):
        trait_id = self.genesis["state"]["active"][0]["id"]
        with self.assertRaisesRegex(EmberError, "both protected and refused"):
            self.transition(protect=[trait_id], refuse=[trait_id])

    def test_duplicate_contribution_is_rejected(self):
        text = self.genesis["state"]["active"][0]["text"]
        with self.assertRaisesRegex(EmberError, "already exists"):
            self.transition(contribution=text)

    def test_explicit_contribution_is_not_silently_discarded(self):
        non_anchor_ids = [
            trait["id"] for trait in self.genesis["state"]["active"] if not trait["anchored"]
        ]
        # The anchor plus five protected traits fill the six-place hearth.
        with self.assertRaisesRegex(EmberError, "no room"):
            self.transition(
                protect=non_anchor_ids[:5],
                contribution="This contribution must either appear or fail explicitly.",
            )

    def test_anchor_contribution_has_anchor_behaviour(self):
        child = self.transition(
            contribution="Return to this point when the map becomes unclear.",
            contribution_kind="anchor",
        )
        new_id = child["actions"]["new"][0]
        added = next(trait for trait in child["state"]["active"] if trait["id"] == new_id)
        self.assertEqual(added["kind"], "anchor")
        self.assertTrue(added["anchored"])
        grandchild = evolve(child, name="Next", pressure=1.0, witness="Anchor check")
        self.assertIn(new_id, grandchild["actions"]["preserved"])

    def test_rehashed_input_tamper_fails_deterministic_replay(self):
        child = self.transition()
        changed = deepcopy(child)
        changed["parameters"]["pressure"] = 0.99
        changed["transition_inputs"]["pressure"] = 0.99
        first = make_event(self.genesis, sequence=0, previous_hash=ZERO_HASH)
        second = make_event(changed, sequence=1, previous_hash=first["hash"])
        with self.assertRaisesRegex(EmberError, "does not replay"):
            verify_events([first, second])

    def test_strict_replay_distinguishes_bool_int_and_float(self):
        changed_genesis = deepcopy(self.genesis)
        changed_genesis["metrics"]["continuity"] = True
        event = make_event(changed_genesis, sequence=0, previous_hash=ZERO_HASH)
        with self.assertRaisesRegex(EmberError, "metrics"):
            verify_events([event])

        child = self.transition(pressure=0.0)
        changed_child = deepcopy(child)
        changed_child["parameters"]["pressure"] = 0
        changed_child["transition_inputs"]["pressure"] = 0
        first = make_event(self.genesis, sequence=0, previous_hash=ZERO_HASH)
        second = make_event(changed_child, sequence=1, previous_hash=first["hash"])
        with self.assertRaisesRegex(EmberError, "does not replay"):
            verify_events([first, second])

    def test_invalid_contribution_kind_reports_validation_error(self):
        child = self.transition()
        changed = deepcopy(child)
        changed["transition_inputs"]["contribution_kind"] = ["value"]
        first = make_event(self.genesis, sequence=0, previous_hash=ZERO_HASH)
        second = make_event(changed, sequence=1, previous_hash=first["hash"])
        with self.assertRaisesRegex(EmberError, "must be a string"):
            verify_events([first, second])

    def test_tide_rekindles_dormant_trait_at_generation_four(self):
        previous = self.genesis
        generations = [previous]
        for index in range(1, 5):
            previous = evolve(
                previous,
                name=f"Generation {index}",
                pressure=0.3,
                witness=f"Witness {index}",
            )
            generations.append(previous)
        self.assertTrue(generations[4]["actions"]["rekindled"])
        rekindled = generations[4]["actions"]["rekindled"][0]
        self.assertIn(rekindled, {trait["id"] for trait in generations[3]["state"]["ash"]})
        self.assertIn(rekindled, {trait["id"] for trait in generations[4]["state"]["active"]})

    def test_append_preserves_prior_bytes_and_round_trips(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lineage.jsonl"
            write_genesis(path, self.genesis)
            prior = path.read_bytes()
            child = self.transition()
            append_generation(path, child)
            self.assertTrue(path.read_bytes().startswith(prior))
            summary = verify_ledger(path)
            self.assertEqual(summary["events"], 2)

    def test_existing_ledger_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lineage.jsonl"
            write_genesis(path, self.genesis)
            original = path.read_bytes()
            with self.assertRaisesRegex(EmberError, "refusing to overwrite"):
                write_genesis(path, self.genesis)
            self.assertEqual(path.read_bytes(), original)

    def test_tampered_record_breaks_hash_verification(self):
        child = self.transition()
        first = make_event(self.genesis, sequence=0, previous_hash=ZERO_HASH)
        second = make_event(child, sequence=1, previous_hash=first["hash"])
        second["generation"]["name"] = "Counterfeit"
        with self.assertRaisesRegex(EmberError, "hash does not match"):
            verify_events([first, second])

    def test_rehashed_payload_tamper_breaks_trait_identity(self):
        child = self.transition()
        changed = deepcopy(child)
        changed["state"]["active"][0]["text"] = "The label survived while its meaning was reversed."
        changed["state_hash"] = state_hash(changed["state"]["active"], changed["state"]["ash"])
        first = make_event(self.genesis, sequence=0, previous_hash=ZERO_HASH)
        second = make_event(changed, sequence=1, previous_hash=first["hash"])
        with self.assertRaisesRegex(EmberError, "content id"):
            verify_events([first, second])

    def test_reordered_records_break_chain(self):
        one = self.transition()
        two = evolve(one, name="Later", pressure=0.25, witness="Later witness")
        zero_event = make_event(self.genesis, sequence=0, previous_hash=ZERO_HASH)
        one_event = make_event(one, sequence=1, previous_hash=zero_event["hash"])
        two_event = make_event(two, sequence=2, previous_hash=one_event["hash"])
        with self.assertRaises(EmberError):
            verify_events([zero_event, two_event, one_event])

    def test_html_export_is_self_contained_and_escapes_script_breakout(self):
        unsafe = self.transition(witness="</script><script>alert('x')</script>")
        first = make_event(self.genesis, sequence=0, previous_hash=ZERO_HASH)
        second = make_event(unsafe, sequence=1, previous_hash=first["hash"])
        html = render_html([first, second])
        self.assertIn("Sol’s <span>Ember</span>", html)
        self.assertNotIn("</script><script>alert", html)
        self.assertIn("\\u003c/script>", html)

    def test_cli_demo_verify_and_export_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = Path(folder) / "demo.jsonl"
            html = Path(folder) / "demo.html"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(["demo", str(ledger), "--generations", "6", "--html", str(html)])
                verified = main(["verify", str(ledger)])
            self.assertEqual(result, 0, stderr.getvalue())
            self.assertEqual(verified, 0, stderr.getvalue())
            self.assertTrue(html.exists())
            self.assertEqual(len(read_ledger(ledger)), 6)

    def test_concurrent_appends_are_serialized(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = Path(folder) / "lineage.jsonl"
            write_genesis(ledger, self.genesis)
            child = self.transition()
            method = "fork" if "fork" in mp.get_all_start_methods() else "spawn"
            context = mp.get_context(method)
            ready = context.Queue()
            start = context.Event()
            results = context.Queue()
            workers = [
                context.Process(
                    target=_append_worker,
                    args=(str(ledger), child, ready, start, results),
                )
                for _ in range(2)
            ]
            for worker in workers:
                worker.start()
            self.assertEqual(ready.get(timeout=5), "ready")
            self.assertEqual(ready.get(timeout=5), "ready")
            start.set()
            for worker in workers:
                worker.join(timeout=10)
                self.assertFalse(worker.is_alive())
                self.assertEqual(worker.exitcode, 0)
            outcomes = [results.get(timeout=5), results.get(timeout=5)]
            self.assertEqual(outcomes.count("ok"), 1, outcomes)
            self.assertEqual(sum(item.startswith("error:EmberError") for item in outcomes), 1, outcomes)
            self.assertEqual(verify_ledger(ledger)["events"], 2)


if __name__ == "__main__":
    unittest.main()

