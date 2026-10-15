# Official FLOP announcement evidence

`evidence/official-announcements.json` is a multi-announcement, offline-verifiable record of two distinct classes of official communication:

1. the 2026-09-30 FLOP Labs work-direction post;
2. the 2026-10-15 KOL leaderboard preview thread and FLOP Labs quote-post.

## States

The work-direction post remains:

```text
DIRECTIONAL_NOT_ELIGIBILITY_CRITERION
```

The four KOL records remain:

```text
PREVIEW_PROVISIONAL_INACTIVE
```

The preview state is mandatory because the captured UI says its identities and balances are sample data, the weekly payout pool is to be announced, signup is simulated, payouts and the work-weighted lottery are inactive, and period boundaries, eligibility, and reward caps still require agreement. The sample date is not a deadline. The caption says social connection is optional while the UI requires at least one verified handle; the artifact preserves that inconsistency rather than silently resolving it.

## Pinned provenance

The validator pins:

- post IDs, accounts, UTC timestamps, canonical X URLs, and exact authored text;
- quote-post relation from FLOP Labs post `2110628169476981128` to `2110624608890282056`;
- media URLs, byte sizes, content types, and SHA-256 hashes for the three preview screenshots;
- fail-closed markers for provisional/sample status, pool TBA, simulated verification, inactive payout/lottery, and unresolved rules/caps.

The media hashes identify the reviewed screenshot bytes. Exact local copies live in `evidence/media/`; the validator recomputes their byte sizes and SHA-256 values. It is intentionally offline and does not download them during validation.

## Offline verification

```bash
python3 official_announcements.py evidence/official-announcements.json
python3 -O official_announcements.py evidence/official-announcements.json
```

For every announcement, `source_snapshot_sha256` is recomputed from UTF-8 canonical JSON (`sort_keys=True`, separators `(',', ':')`, `ensure_ascii=False`). The validator rejects duplicate JSON keys, unknown announcements or fields, altered source anchors, media-hash tampering, invented deadlines/artifacts/receipts, missing provisional markers, and any promotion to eligibility.

The tool has no network, signing, posting, wallet, claim, or file-write path.

## Claim boundary

This artifact proves that the cited posts and preview facets were captured and classified conservatively. It does **not** prove that KOL signup is live, any referral tracks activity, a payout pool exists, a lottery is active, this repository's work was requested or accepted, or any identity is eligible, allocated, claimable, claimed, or paid. Preview UI is evidence of a preview—screenshots do not become payroll by achieving sufficient resolution.
