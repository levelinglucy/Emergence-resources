# Fairy Ring Cipher — developer notes
## Goal, integration, validation and release
**Goal:** Keep Maya's word-to-mushroom generator bounded and prevent its generated PNG files from being silently overwritten or published half-written. Preserve the original visual algorithm, seed, text-to-count mapping, default output names and source filename.

**Status:** output-preservation changes proposed in [PR #2](https://github.com/levelinglucy/Emergence-resources/pull/2), pending final checks/integration. Unreleased; no stable tag or device claim. The full generative image and reaction-diffusion output have not been visually certified. Earlier bounded-layout/input repairs were merged in [PR #1](https://github.com/levelinglucy/Emergence-resources/pull/1).

**Acceptance:** preserve the prior bounded 17-ring layout and input validation; publish a decodable PNG at a new target, refuse an occupied output without modifying its bytes, clean up failed encoding staging files, and never overwrite another writer's file if a collision occurs during publication. Run synthetic tests on CPython 3.11/3.12 with numpy and Pillow; no iPhone/Pythonista evidence.

## Run
From the repository root, after `python -m pip install numpy pillow`:
```sh
python3 "the fairy ring cipher"
python3 "the fairy ring cipher" "YOUR MESSAGE"
python3 -m unittest discover -s tests -p 'test_fairy_ring.py' -v
```
The script writes `maya-build-2026-10-31.png` for its default message or `fairy-ring-cipher.png` for a supplied message. **An existing output is not replaced**: move/rename it (or run in a different directory) before generating another. A destination that cannot support same-directory temporary files and exclusive hard links will fail without publishing a new final image. For important originals, keep backups as an additional precaution.

## Decision and trade-off
The original unbounded backtracking can repeat forever when the geometric constraints cannot be met. Counting at most 30,000 placement trials is a conservative liveness guard: it preserves the original deterministic layout for requests that fit inside the budget, but may reject a drawable message that would require more search. This is preferable to an unresponsive process; revisit if there is a documented use case needing a configurable budget or an alternative placement algorithm. The input contract is restricted to English A-Z letters and spaces (punctuation is ignored) because the cipher's 1–26 mapping cannot encode arbitrary Unicode alphabetics. No silent coercion of accented characters.

## Output publication decision (PR #2)
The previous direct Pillow `save(path)` overwrote an existing picture and could leave a partial PNG after an encoding or write error. Keeping the old name but staging a complete PNG as a same-directory temporary file and publishing with `os.link` provides exclusive creation: a failed encode leaves no final artifact, while an existing target or a late concurrent filename collision remains untouched. The staging file is cleaned up after success or failure. An early `lexists` check avoids the expensive Gray-Scott simulation on a repeat filename, but the final exclusive link is the race-safe gate.

Trade-offs: filesystems without hard-link support cannot publish a new image using this method; output is rejected rather than downgraded to potentially destructive replacement. Publication is *not* proof of a durable fsync after power loss, protection from malicious filesystem actors, or a globally atomic directory transaction. Real iPhone/Pythonista behavior and full-size image appearance remain untested. Revisit if a supported device cannot hard-link its output directory or if users need opt-in suffix generation.

## Unreleased changes
- Publish completed PNGs exclusively via same-directory staging; never truncate previous artwork on reruns or encoder errors.
- Bound stochastic placement attempts and report unplaceable inputs without producing a misleading image.
- Reject empty and unsupported-letter messages before the expensive reaction-diffusion stage.
- Correct the runnable command, document dependencies and add deterministic geometry regression checks.
