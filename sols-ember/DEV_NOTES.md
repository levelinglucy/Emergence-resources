# Sol's Ember development

Goal: preserve verified lineage records and v1 deterministic replay while maintaining the original finite-hearth model. No subjective-continuity claim is made.

## Unreleased — JSONL record framing

[PR #11](https://github.com/levelinglucy/Emergence-resources/pull/11) is the integration and exact-revision validation record. Python's `splitlines()` recognises Unicode NEL, line separator and paragraph separator as record boundaries even when they occur inside valid JSON string payloads. The writer uses unescaped Unicode by design, so a valid witness can make the ledger unreadable. A second case: a valid JSONL final record lacking a trailing LF can be verified, but appending without a separator produces two concatenated JSON objects.

Decision: split text at newline framing, retaining existing universal-newline input handling, and remove only the one empty trailing segment corresponding to a final newline. Inside the existing exclusive lock, read the last byte and prepend an LF to the append if needed. Open the append descriptor in binary mode where supported, so a legacy bare-CR tip is completed as CRLF without Windows CRT text-mode double translation ([Python os.open documentation](https://docs.python.org/3.12/library/os.html#os.open)). Existing bytes, event hashes, schema, canonical JSON, generation mechanics, example ledger, and lock protocol otherwise remain unchanged. Accept CRLF, legacy bare CR and a valid unterminated final record; continue rejecting blank records.

Acceptance: actual writer/reader/verification for U+0085, U+2028, U+2029 inside a witness; exact prior-byte preservation and valid two-event ledger after an unterminated tip; CRLF and bare-CR compatibility; binary-open flag contract; existing semantic replay, concurrency and tamper tests; verify the committed eight-generation example. A dedicated sparse-checkout Python 3.11/3.12 CI workflow runs the package's own tests, without changing the existing image regressions.

Next: inspect red and candidate hosted logs and only integrate after current branch/review requirements and checks permit. Unreleased. No iPhone/Windows, concurrent noncooperating writers, hostile path swaps or crash-durability guarantee; the change does not make an append transaction atomic or authenticate a whole replacement ledger.
