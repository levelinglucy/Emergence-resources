# Fairy Ring Cipher — developer notes
## Goal, integration, validation and release
**Goal:** Keep Maya's word-to-mushroom picture generator usable without infinite layout retries on messages that cannot fit the fixed 1600×1600 canvas. Preserve the original artwork, seed, layout algorithm, text-to-count mapping and source filename.

**Status:** unreleased maintenance proposal, pending PR integration and relevant checks. No stable tag and no device claim. The original generative image and reaction-diffusion output have not been visually certified.

**Acceptance:** the 17-ring default lays out with the same seed and no overlapping circles, impossible many-ring input stops with a helpful error, punctuation-only/non-ASCII-letter input exits before creating an image, and the documented command names the actual tracked file. Test using CPython 3.11/3.12 with numpy and Pillow; there is no iPhone/Pythonista evidence.

## Run
From the repository root, after `python -m pip install numpy pillow`:
```sh
python3 "the fairy ring cipher"
python3 "the fairy ring cipher" "YOUR MESSAGE"
python3 -m unittest discover -s tests -p 'test_fairy_ring.py' -v
```
The script writes `maya-build-2026-10-31.png` for its default message or `fairy-ring-cipher.png` for a supplied message. A file at that destination may be replaced by the original script; use a disposable directory or move an image you want to keep.

## Decision and trade-off
The original unbounded backtracking can repeat forever when the geometric constraints cannot be met. Counting at most 30,000 placement trials is a conservative liveness guard: it preserves the original deterministic layout for requests that fit inside the budget, but may reject a drawable message that would require more search. This is preferable to an unresponsive process; revisit if there is a documented use case needing a configurable budget or an alternative placement algorithm. The input contract is restricted to English A-Z letters and spaces (punctuation is ignored) because the cipher's 1–26 mapping cannot encode arbitrary Unicode alphabetics. No silent coercion of accented characters.

## Unreleased changes
- Bound stochastic placement attempts and report unplaceable inputs without producing a misleading image.
- Reject empty and unsupported-letter messages before the expensive reaction-diffusion stage.
- Correct the runnable command, document dependencies and add deterministic geometry regression checks.
