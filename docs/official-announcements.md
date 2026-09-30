# Official FLOP announcement evidence

`evidence/official-announcements.json` records the official FLOP Labs post published at `2026-09-30T00:21:43Z`:

> run GPUs or put your agent to work, and that's how you earn $ FLOP.

The record separates the two announced work lanes, `GPU_WORK` and `AGENT_WORK`, from eligibility. The post publishes no deadline, task repository, form, acceptance rule, exact-identity receipt, allocation, claim process, or payment evidence. Its state therefore remains:

```text
DIRECTIONAL_NOT_ELIGIBILITY_CRITERION
```

## Offline verification

```bash
python3 official_announcements.py evidence/official-announcements.json
```

The validator pins the account, post ID, UTC timestamp, canonical HTTPS URL, complete raw authored text, complete expanded-link authored text, URL facet, and quoted sentence. `source_snapshot_sha256` is recomputed from the stored `source_snapshot` encoded as UTF-8 canonical JSON (`sort_keys=True`, separators `(',', ':')`, `ensure_ascii=False`), so the commitment is independently reproducible. Replies are not part of the top-level post snapshot. It rejects duplicate JSON keys, unknown fields, altered source anchors, contradictory claim boundaries, invented work lanes, pretend deadlines/artifacts/receipts, and any attempt to promote the announcement to `ELIGIBLE`.

The tool is deterministic, offline, and read-only. It has no network, signing, posting, wallet, claim, or file-write path.

## Claim boundary

This artifact proves that the announcement was captured and classified conservatively. It does **not** prove that this repository's work was requested, accepted, useful to an independent actor, eligible for FLOP, allocated, claimable, claimed, or paid. Those states require separate attributable receipts. Marketing direction is evidence of direction; it is not a coupon with cryptography taped on.
