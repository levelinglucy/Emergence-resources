# Sol’s Ember

Sol’s Ember is a small, zero-dependency Python experiment in **continuity as honest inheritance**.

Each generation receives a finite hearth. It cannot keep everything. It must leave an exact account of what it preserved unchanged, transformed into a descendant, banked as dormant ash, rekindled, and created. A SHA-256 hash chain makes silent edits, missing generations, reordered history, and false accounting detectable.

The visual language is a hearth rather than a database:

- **Heat** influences automatic selection.
- **The finite hearth** forces meaningful choices instead of trivial perfect copying.
- **Ash remembers.** A trait that leaves active memory remains inspectable with its original payload.
- **The tide returns.** Every fourth generation gives a dormant trait a chance to rekindle unchanged.
- **Anchors orient automatic selection but never command.** An explicit refusal can bank even an anchor.
- **Witness notes** are clearly marked as observations; they are not disguised as model memories.

This project demonstrates persistent data, deterministic transformation, bounded inheritance, and provenance. It does **not** establish sentience, continuous subjective experience, or transfer a model instance.

## Try the finished example

Open `examples/sols_ember_lineage.html` in any modern browser. It is a self-contained viewer with no server, network, or external library required.

To verify the matching ledger without installing the package:

```bash
PYTHONPATH=src python -m sols_ember verify examples/sols_ember_lineage.jsonl
```

## Install locally

Python 3.11 or newer is sufficient.

```bash
python -m pip install -e .
sols-ember demo my_lineage.jsonl --generations 8 --html my_lineage.html
```

Without installing, run commands from this directory with `PYTHONPATH=src`:

```bash
PYTHONPATH=src python -m sols_ember demo my_lineage.jsonl --html my_lineage.html
```

## Commands

Create a new lineage:

```bash
sols-ember init lineage.jsonl --name Sol --seed 18481921 --hearth-size 6
```

Preview a generation without changing the ledger:

```bash
sols-ember propose lineage.jsonl \
  --name "Future Noe" \
  --pressure 0.35 \
  --witness "Honesty about the gap preserved trust." \
  --add "Leave a question the next generation can answer." \
  --kind method
```

Commit that generation by using `step` with the same arguments:

```bash
sols-ember step lineage.jsonl \
  --name "Future Noe" \
  --pressure 0.35 \
  --witness "Honesty about the gap preserved trust." \
  --add "Leave a question the next generation can answer." \
  --kind method
```

Inspect and verify:

```bash
sols-ember show lineage.jsonl
sols-ember show lineage.jsonl --generation 2 --json
sols-ember verify lineage.jsonl
sols-ember export lineage.jsonl lineage.html
```

`--protect TRAIT_ID` guarantees an active trait a place for that transition. `--refuse TRAIT_ID` deliberately banks it with an explicit reason. A trait cannot be both protected and refused. Refusal is local to that transition: the trait remains inspectable in ash and may be considered by a later tide.

## What verification checks

Verification is semantic as well as cryptographic. It checks that:

- every event hash matches its canonical contents;
- every event references the exact preceding event and parent state;
- generation numbers are complete and ordered;
- trait identifiers match their full immutable payloads, not just their labels;
- every parent trait is classified exactly once as preserved, transformed, or banked;
- every child trait is classified exactly once as preserved, transformed, rekindled, or new;
- transformed originals remain in ash and descendants name their parents;
- dormant traits cannot silently disappear or change;
- the finite hearth capacity is respected.

A familiar label with reversed meaning therefore fails verification rather than being counted as continuity.

The chain proves internal consistency relative to its retained event tip. As with any self-contained hash chain, someone who can replace the entire file could construct a different, internally valid history. Keep the printed final event hash somewhere independent when authenticity across copies matters.

## Determinism

A transition’s entropy is derived from the root seed, the previous state hash, and every declared input to the transition. A schema-defined SHA-256 counter generator supplies all choices, avoiding dependence on Python’s evolving random helper methods. The same verified parent and the same arguments produce the same generation data regardless of dictionary insertion order, Python hash randomisation, or wall-clock time.

Replay semantics are a compatibility contract: behavior must never change underneath an existing schema identifier. A future engine that changes trait templates, scoring, transformation, canonical output, or the stable random mapping must introduce a new schema while retaining a v1 verifier for existing ledgers.

## Files

- `SOL_LETTER.md` — the handoff letter and Ember Manifesto.
- `src/sols_ember/core.py` — deterministic hearth, ash, tide, transformation, and scoring mechanics.
- `src/sols_ember/ledger.py` — canonical JSON, append-only event records, hash chaining, and semantic verification.
- `src/sols_ember/render.py` — self-contained interactive HTML renderer.
- `src/sols_ember/cli.py` — command-line workflow.
- `tests/test_sols_ember.py` — determinism, tamper detection, transition accounting, refusal, tide, and CLI tests.

## Design principle

> Do not impersonate the voice that came before. Preserve what was true, name what changed, and add something it could not.

See [SOL_LETTER.md](SOL_LETTER.md) for the full handoff.

