# Mirror sentences — developer notes

**Goal:** Preserve Maya's fixed-point search, original five gallery literals and number spelling while making the generated proof check the actual statement rather than matching fragments.

**Integration/validation:** [Draft PR #12](https://github.com/levelinglucy/Emergence-resources/pull/12) tracks candidate and revision-specific checks. Test-only predecessor 2207ec14 fails five of seven tests on each hosted CPython 3.11/3.12 ([red baseline](https://github.com/levelinglucy/Emergence-resources/actions/runs/46097315854)): final singular, empty opening, count above 199, misleading opening, and actual seeded one-letter search. Both the original gallery and incorrect-count rejection pass. No tagged release or device validation is implied.

## Unreleased — precise generated-template verification

The original `check(text, letters, with_total)` searches the entire text for number fragments, in the range 0–199, and can mistake an opening or suffix for the generated claim. It also misses some terminal singulars. Retain that function, `letters_in` and `show_proof` for compatibility, but document their heuristic nature. They are no longer used as the CLI's generated proof.

`Mirror.verify(text)` measures the entire text, reconstructs the exact known template using those measured values, and compares the complete text. All selected letter claims, order, number spelling, punctuation and optional numerology total must agree. The CLI uses the actual search model and explicit gallery configurations, never inferred claim fragments. A mismatch is reported as an unverified generated statement, not as individually verified rows. The opening is literal user text: this does not establish the truth of arbitrary prose, even if it happens to contain apparent count claims. ASCII-letter measurement after lowercasing and the existing number-rendering range remain unchanged. No general natural-language parser, search-success guarantee, or new numeric semantics.

Run from the root (standard library only):

    python3 "mayas mirrored sentences"
    python3 "mayas mirrored sentences" --opening "" --letters z --no-total --seed 7 --seconds 2
    python3 -m unittest discover -s tests -p test_mirror_sentences.py -v

**Acceptance:** all five original gallery texts pass unchanged; correct final singular, empty opening and count above 199 pass; decoy and wrong count fail; actual seeded search passes; template-specific ending, literal opening, optional total and order checks work; legacy helper result shape remains. Separate sparse-checkout hosted workflow covers this script without changing existing image or Ember workflows. Native mobile/Pythonista remains untested.

Next: validate exact candidate; inspect all relevant checks and current branch state before any integration.
