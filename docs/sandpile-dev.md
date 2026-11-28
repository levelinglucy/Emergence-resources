# The sandpile — developer notes

**Goal:** Keep Maya's original sonification and seed, timing, synthesis, and encoder defaults intact while avoiding accidental loss of prior recordings. The tracked script has no extension: `The sandpile`.

**Integration:** proposal only, review branch; main unchanged. **Validation:** bounded local real-encoder tests, details and exact blobs in the associated PR. **Release:** unreleased.

## Unreleased — proposed recording preservation

The original binary write truncates an existing output, including through a final-component symlink. A different seed still defaults to the same filename. This candidate refuses existing destinations before synthesis and uses a closed same-directory staging file plus an exclusive hard link to prevent replacement if the name appears during synthesis. This follows the publication convention in this repository's Word ants tool. Ordinary caught staging/link failures remove the temporary file. Choose distinct filenames, e.g.:

    python3 "The sandpile" --seed 31 --out seed31.mp3
    python3 "The sandpile" --seed 7 --out seed7.mp3

**Compatibility decision pending:** no automatic overwrite, even for an intentional rerun. Keep the original default name; no new overwrite flag is proposed. Hard-link support is required and the resulting file has tempfile's restrictive permissions on POSIX. Unsupported filesystems fail rather than falling back to destructive publication. Neither this pattern nor the test asserts crash/power-loss durability, cleanup after process death, hostile parent-directory replacement safety, or support on iOS/Windows. Cleanup failures after successful publication can still report an error despite a complete final file.

## Reproduce

Install numpy and lameenc in an isolated environment, then from the repository root run:

    python -m unittest discover -s tests -p test_sandpile.py -v

The tests use disposable paths, seed 31, TARGET=12, WARMUP=3000 and the real encoder. They cover fresh output, refusal before synthesis, both symlink cases, simulated late name collision, link failure and partial staging write. The full default-length piece and other environments are not validated.

## Next steps

1. Ask for review of the no-replace contract, permissions and filesystem support before integration; preserve the author attribution.
2. Consider target-platform tests and existing CI requirements before merging. Do not equate unrelated workflow passes with sandpile coverage.
