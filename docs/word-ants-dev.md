# Word ants — developer notes

## Goal and status

**Goal:** Keep the original numerology-to-turmite drawing algorithm and default gallery, while protecting previously generated artwork and ensuring a failed image encode cannot leave a partial final output.

**Integration:** Follow [PR #5](https://github.com/levelinglucy/Emergence-resources/pull/5) for observed merge status. **Validation:** Test-first predecessor CI [43029373105](https://github.com/levelinglucy/Emergence-resources/actions/runs/43029373105) failed the three expected new cases on both Python versions. Candidate CI [43029711953](https://github.com/levelinglucy/Emergence-resources/actions/runs/43029711953) then passed 12 existing Fairy Ring and 3 new Word ants tests, with both script syntax checks, per Python 3.11 and 3.12; all four test logs inspected. Further revisions must be validated separately. **Release:** Unreleased; no iPhone/Pythonista or power-loss durability claim.

**Acceptance:** A short real CLI run produces a readable image in a disposable directory. A second run at the same path exits with status 2 without replacing the first image. Encoder failures leave no partial final or staging image. If another writer wins the filename race during publication, their bytes remain unchanged. Run both artwork tests on hosted Python 3.11/3.12; preserve the historical rule, grid, palette and drawing logic.

## Run

Install Pillow, then from the repository root:

```sh
python3 -m pip install pillow
python3 "Word ants" --steps 1000 ember --out ember.png
python3 -m unittest discover -s tests -p 'test_word_ants.py' -v
```

The original script's introductory command examples named a nonexistent filename; the tracked entry point is `Word ants` (no extension). By default it writes `word-ants.png` next to the source. A destination that already exists is **not** replaced. Choose a fresh `--out` name or move the old file to keep both.

## Publication decision

Earlier, `sheet.save(args.out)` directly opened an existing output for writing and could truncate it before completing the new image. The repaired path stages the new image under a unique hidden file in the destination directory. Pillow still chooses format from the requested extension, so custom supported formats retain their prior behaviour; the default remains PNG. After encoding completes, `os.link` creates the final name exclusively. The stage is removed on success and on handled failure.

An early `lexists` check avoids spending time drawing when a destination is already occupied, including a dangling symlink. The final hard-link call protects against a late collision between the early check and publication. The implementation doesn't delete or rewrite old art.

**Trade-offs:** This fails closed on output directories/filesystems where hard links are unavailable; no unsafe overwrite fallback is used. Same-directory publication is not a durable `fsync` transaction, does not prevent hostile directory races, and does not prove that a full production gallery renders well or that Pythonista supports hard links. Those require separate evidence and may motivate a different, explicitly scoped publication design.

## Unreleased changes

- Prevent Word ants reruns from overwriting existing art; refuse collisions before rendering and at publication.
- Stage completely encoded images before exposing their final name, cleaning up failed or colliding stages.
- Run disposable real drawing, encoder failure and late-collision regressions alongside the existing Fairy Ring checks on hosted Python.
- Correct example invocation to use the actual no-extension source filename.

## Next

Track the final integration and exact revision in PR #5. Consider an opt-in fresh-filename mode only if there is evidence users need it; do not change historical rule or colour semantics incidentally.
