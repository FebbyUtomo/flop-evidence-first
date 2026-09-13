# Publication Package

## Artifact title
Technocore/Kibble at Scale: A Transparent 50,000-Identity and 187,389-Local-Record Experiment

## Public repository contents
- `README.md` — flagship report.
- `evidence/metrics.json` — aggregate machine-readable snapshot.
- `analyze.py` — deterministic local aggregation code.
- `quality_worker.py` — offline fail-closed draft evaluator.
- `tests/` — unit tests.
- `examples/` — structural-gate-pass/rejected offline examples.

## Excluded from publication
- Identity seeds, PEM files, passphrases, account JSON records.
- Raw Kibble state and raw operational logs.
- Hostnames, IP addresses, wallet identifiers, private balances.
- Any claim of official FLOP allocation.

## Pre-publication sequence
1. Create a clean public repository.
2. Copy only the reviewed files listed above.
3. Run the unit tests and public-bundle secret scan.
4. Commit and record the exact commit SHA.
5. Publish the repository and record its immutable URL.
6. Announce that exact URL from the declared publication DID in the `technocore` room.
7. Save returned room, sequence, nonce, and sender DID.
8. Publish the reviewed X thread with the same DID and repository URL.
9. Submit the creator form and save a receipt.

No external publication or form submission is performed by this package.
