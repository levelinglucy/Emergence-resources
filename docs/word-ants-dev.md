# Word ants — developer notes

## Goal and status

**Goal:** Preserve the numerology-to-turmite drawing algorithm, gallery and safe artwork publication while allowing every Unicode character recognized by `str.isdigit()` to become its numeric value without crashing image generation.

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

## Publication decision

Earlier, `sheet.save(args.out)` directly opened an existing output for writing and could truncate it before completing the new image. The repaired path stages the new image under a unique hidden file in the destination directory. Pillow still chooses format from the requested extension, so custom supported formats retain their prior behaviour; the default remains PNG. After encoding completes, `os.link` creates the final name exclusively. The stage is removed on success and on handled failure.

An early `lexists` check avoids spending time drawing when a destination is already occupied, including a dangling symlink. The final hard-link call protects against a late collision between the early check and publication. The implementation doesn't delete or rewrite old art.

**Trade-offs:** This fails closed on output directories/filesystems where hard links are unavailable; no unsafe overwrite fallback is used. Same-directory publication is not a durable `fsync` transaction, does not prevent hostile directory races, and does not prove that a full production gallery renders well or that Pythonista supports hard links. Those require separate evidence and may motivate a different, explicitly scoped publication design.

## Unreleased changes

- Decode Unicode superscript and circled single digits consistently with decimal digits, avoiding `ValueError` during rendering; keep original rule, visual algorithm and safe publication.

- Prevent Word ants reruns from overwriting existing art; refuse collisions before rendering and at publication.
- Stage completely encoded images before exposing their final name, cleaning up failed or colliding stages.
- Run disposable real drawing, encoder failure and late-collision regressions alongside the existing Fairy Ring checks on hosted Python.
- Correct example invocation to use the actual no-extension source filename.

## Next

Optional future iPhone/Pythonista checks should cover both hard-link publication and the Unicode text path. Consider supporting Unicode numeric symbols of more than one digit only with a clear, backward-compatible specification and tested reason; avoid incidental changes to rule, palette or rendering semantics.
