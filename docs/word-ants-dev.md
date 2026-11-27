# Word ants — developer notes

## Goal and status

**Goal:** Preserve the numerology-to-turmite drawing algorithm, gallery and safe artwork publication while interpreting Unicode `isdigit()` characters correctly and supporting mixed turning rules whose colour indices exceed a byte without crashing image generation. Keep long captions readable without changing the underlying simulation or sheet dimensions.

**Integration and validation:** Artwork preservation was merged in [PR #5](https://github.com/levelinglucy/Emergence-resources/pull/5). [PR #6](https://github.com/levelinglucy/Emergence-resources/pull/6) is the authoritative record for the Unicode digit change's integration status and revision-specific green checks. Test-first `4fedb72f` demonstrated two new `ValueError` failures per Python 3.11 and 3.12 run while all 12 Fairy Ring and three previous Word ants tests passed ([red CI](https://github.com/levelinglucy/Emergence-resources/actions/runs/43118835744)). **Publication:** no verified release or iPhone/Pythonista or power-loss durability claim.

**Acceptance:** ASCII and Arabic-Indic digits keep their original values; digit-like Unicode characters such as superscript `²`, circled `⑨` and circled zero `⓿` map to their numeric digit values. A real disposable PNG drawn from a compatibility-digit word succeeds without residual staging files; all existing output collision, failed encode, Fairy Ring and Word ants tests remain green on Python 3.11/3.12. Preserve ant movement, grid, palette and the output publication contract.

## Run

Install Pillow, then from the repository root:

```sh
python3 -m pip install pillow
python3 "Word ants" --steps 1000 ember --out ember.png
python3 "Word ants" --steps 1000 'A²' --out unicode-example.png
python3 -m unittest discover -s tests -p 'test_word_ants.py' -v
```

The original script's introductory command examples named a nonexistent filename; the tracked entry point is `Word ants` (no extension). By default it writes `word-ants.png` next to the source. A destination that already exists is **not** replaced. Choose a fresh `--out` name or move the old file to keep both.

## Unicode digit interpretation

Previously `numerology()` called `int(ch)` whenever `ch.isdigit()` was true. Python's `isdigit()` also accepts superscripts and circled digits, but `int()` does not, so otherwise valid words could crash image generation before publication. We now use `unicodedata.digit(ch)` for every `isdigit()` character, retaining decimal values and accepting compatibility digits. Ordinary letters, signs and unsupported numeric symbols (such as the circled number `⑩`, which is not a single digit) retain their prior treatment. The word's characters are not rewritten or normalized; only the numeric rule is derived. This is a compatibility broadening for input characters, not a rule or art-renderer redesign. Reconsider only if a concrete ambiguity requires a stricter documented ASCII-only mode.

## Long mixed-rule colour states (2026-11-17)

The original ant grid always used one byte per square. However the rule length determines the colour range: a valid 257-character mixed turning rule needs state 256 after enough revisits, and the original writer raises `ValueError: byte must be in range(0, 256)` before an image can be published. A test-first failure on the exact source was observed for 257- and 65,537-state rules, including a full disposable PNG attempt ([red hosted regression](https://github.com/levelinglucy/Emergence-resources/actions/runs/44135922367)).

**Decision:** Preserve `bytearray` for rules of up to 256 symbols, switch to `array('H')` for 257–65,536 states, and use a verified at-least-32-bit unsigned array for longer rules. The ant's coordinates, turn sequence, modular state update, palette and publish-exclusively protocol are unchanged. If a rule exceeds the chosen native array's representable state range, explicitly reject it rather than silently wrap. This increases world-grid memory from approximately 1.44 MB to 2.88 MB for the 16-bit tier, and normally 5.76 MB for the 32-bit tier (native `itemsize` is platform-dependent).

**Validation contract:** Compare short-rule output type, 257-state advancement above byte range, 65,537-state storage width, real 257-letter PNG creation, second-run refusal, and preexisting Fairy Ring/Word ants regressions. [PR #7](https://github.com/levelinglucy/Emergence-resources/pull/7) holds revision-specific merge and hosted-test evidence; do not infer a tagged release from PR or source integration.

**Limits:** No iPhone/Pythonista, huge-rule practical performance, memory-pressure, adversarial word, non-PNG publication, power-loss or hardware-rendering certification. `array('L')` is used only if `array('I')` is too narrow on the host. This does not change user artwork or historical output.

## Measured caption previews (2026-11-25)

[Draft PR #8](https://github.com/levelinglucy/Emergence-resources/pull/8) investigates long inputs whose captions previously clipped or collided with the steps label. The test-only predecessor's [hosted run](https://github.com/levelinglucy/Emergence-resources/actions/runs/45585160260) reproduces both problems on Python 3.11 and 3.12. Candidate validation and integration are recorded in the PR; no release is implied.

**Decision:** Preserve the existing 380-pixel panel and 92-pixel caption area. Use four separately measured rows (word, digits, rule, steps); place measured ink within its row with 14-pixel horizontal margins. Fit a prefix and explicit ASCII `...` when a caption does not fit, including an upper bound on text sent to the font engine. Escape non-printing characters in the word preview. This is a prefix preview, not a Unicode grapheme-aware layout or guaranteed maximal prefix. Short labels retain their content but move vertically. The simulation, crop, palette, gallery dimensions and exclusive output publication remain unchanged.

**Full input retrieval (opt-in):** Ordinary PNG output does not embed the original input strings. Add `--embed-inputs` to intentionally store the ordered originals (including repeats) as JSON in the PNG text key `word_ants_inputs`. For example, create a new image with `python3 "Word ants" --embed-inputs ember --out ember.png`, then read it with:

```python
import json
from PIL import Image
with Image.open("ember.png") as image:
    print(json.loads(image.info["word_ants_inputs"]))
```

Use the existing numerology and rule functions to reconstruct full digits and turns. This metadata can reveal input characters not visible in the caption. Opt-in rather than default storage preserves the previous publication boundary and avoids surprising disclosure when sharing art; ordinary images still show visible captions and derived artwork, so they are not anonymous. Metadata can be stripped by other software and is not authentication. Other supported output formats retain their normal encoding; requesting `--embed-inputs` with a non-PNG destination is rejected before rendering. Retain the original command/inputs separately if exact retrieval is important. Existing files are never rewritten.

**Acceptance:** Verify the test-first overlap and clipping failures, bounds and explicit markers for long labels under TrueType and default fonts, exact short label text, explicit ordered PNG input round-trip, default absence of that field, early non-PNG opt-in refusal and ordinary non-PNG encoding, unchanged dimensions and existing publication and simulation tests. The sheet-wide heading/subheading, arbitrary glyph shaping, device fonts and metadata retention through third-party image processing are outside this panel-caption repair.

## Sheet heading layout (2026-11-26)

[PR #9](https://github.com/levelinglucy/Emergence-resources/pull/9) extends the earlier panel-caption repair to the fixed 120-pixel sheet header. Its test-only predecessor failed for a 416-pixel single-panel gallery on both hosted Python versions: the title's measured right edge was 562 ([red CI](https://github.com/levelinglucy/Emergence-resources/actions/runs/45747994001)); the two- and three-panel cases passed.

**Decision:** Keep the full title, choose the largest fitting size up to 44 for the installed scalable title face, and place measured ink with 18-pixel side margins. Use the complete explanatory subtitle on one line when it fits, otherwise split it at its existing logical transitions into three rows. Built-in fallback fonts retain their small size and use ASCII arrows so the explanation does not depend on Unicode arrow support. Unlike variable input captions, fixed heading text is never shortened. If a heading cannot fit its allotted row, fail explicitly rather than publishing clipped text. The existing canvas, panel positions, movement, palette, metadata opt-in and exclusive publication are unchanged.

**Acceptance:** Real disposable PNGs at each of the three gallery widths, with DejaVu, built-in defaults and the platform-selected fonts; verify exact heading and complete subtitle text (equivalent arrow spelling), ink bounds and nonoverlap, original dimensions and existing output tests. See PR #9 for revision-specific validation and integration; no release, all-font, mobile or power-loss certification is implied.

## Exact boundary-exit caption (2026-11-27)

[PR #10](https://github.com/levelinglucy/Emergence-resources/pull/10) corrects an ambiguity in the steps caption: `taken < steps` detected an early exit but not one on the last requested move. The internal walker now returns an explicit boundary-exit flag; the public `walk(rule, steps, size)` still returns its original three values. No movement, colour, crop or publication behavior changes. The uniform-rule illustration remains unchanged.

**Acceptance:** Render real panels for rule RL (word `ab`) at budgets 40,268, 40,269 and 40,270 on the default grid. The first must have no exit note, the latter two must include the full note within the existing row. Existing simulation and publication regressions must pass. See PR #10 for exact validation and integration; no release or device certification is implied.

## Publication decision

Earlier, `sheet.save(args.out)` directly opened an existing output for writing and could truncate it before completing the new image. The repaired path stages the new image under a unique hidden file in the destination directory. Pillow still chooses format from the requested extension, so custom supported formats retain their prior behaviour; the default remains PNG. After encoding completes, `os.link` creates the final name exclusively. The stage is removed on success and on handled failure.

An early `lexists` check avoids spending time drawing when a destination is already occupied, including a dangling symlink. The final hard-link call protects against a late collision between the early check and publication. The implementation doesn't delete or rewrite old art.

**Trade-offs:** This fails closed on output directories/filesystems where hard links are unavailable; no unsafe overwrite fallback is used. Same-directory publication is not a durable `fsync` transaction, does not prevent hostile directory races, and does not prove that a full production gallery renders well or that Pythonista supports hard links. Those require separate evidence and may motivate a different, explicitly scoped publication design.

## Unreleased changes

- Report actual boundary exits even when they occur on the final requested move; retain the public three-value walker API.

- Fit the complete sheet title and explanation within the existing header of narrow and wide galleries; preserve the original artwork dimensions.

- Fit Word ants caption previews into separate rows, marking truncated labels and optionally embedding the full ordered inputs in PNG output via `--embed-inputs`; preserve the original dimensions and simulation.

- Support mixed rules with more than 256 colour states by using wider unsigned cell storage, retaining the byte grid for ordinary rules; reject unrepresentable lengths instead of overflowing. 

- Decode Unicode superscript and circled single digits consistently with decimal digits, avoiding `ValueError` during rendering; keep original rule, visual algorithm and safe publication.

- Prevent Word ants reruns from overwriting existing art; refuse collisions before rendering and at publication.
- Stage completely encoded images before exposing their final name, cleaning up failed or colliding stages.
- Run disposable real drawing, encoder failure and late-collision regressions alongside the existing Fairy Ring checks on hosted Python.
- Correct example invocation to use the actual no-extension source filename.

## Next

Optional future iPhone/Pythonista checks should cover both hard-link publication and the Unicode text path. Consider supporting Unicode numeric symbols of more than one digit only with a clear, backward-compatible specification and tested reason; avoid incidental changes to rule, palette or rendering semantics.
