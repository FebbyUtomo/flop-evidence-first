# Official FLOP criteria monitor

`criteria_monitor.py` performs a read-only drift check over eight official FLOP draft surfaces pinned in `evidence/official-criteria.json`.

## Sources and authority

1. `flop.finance/intro/yellowpaper/` — official draft normative specification.
2. `flop.finance/testnet/` — provisional testnet timeline, onboarding, scoring, snapshot, review, and anti-Sybil rules.
3. `flop.finance/airdrop/` — draft genesis allocation, distribution, claim, and unlock terms.
4. `ask.flop.finance/docs/protocol-parameters` — official draft parameter reference.
5. `flop.finance/intro/agent` — official draft agent guide.
6. `flop.finance/intro/miner` — official draft miner guide.
7. `flop.finance/teaser/` — official provisional overview; it defers to the Yellow Paper.
8. commit-pinned `CHANGELOG.md` — official draft ruling and implementation-status history.

The reviewed normative reference is pinned separately to Yellow Paper `0.5.0-draft`, commit `56410c67b11292e707d32ef32e9c4ff9c02e28c7`, tree `32dc40388b74fea5ca274bba58ee5f4f9e2430f5`, published from `flop-core@dfd98a59d`. The pin records provenance; it does not make the draft final.

No monitored page is treated as an identity-specific eligibility receipt. The hierarchy prevents an older overview from silently overriding a dedicated rule page, but it does not guess which unresolved draft value will become final.

## What the monitor detects

For each allowlisted HTTPS source, the monitor:

- extracts visible text while excluding scripts, styles, SVG, and other non-content blocks;
- normalizes whitespace and computes SHA-256;
- compares the digest with the captured baseline;
- verifies markers for draft authority, settled-session scoring, common-control aggregation, independent demand, snapshot/review flow, genesis allocation, claim handling, unlock terms, D-0527 through D-0531, and the current runtime mismatch;
- reports known official draft conflicts instead of choosing whichever rule is convenient.

The manifest also pins fail-closed interpretation guards: testnet scoring is distinct from post-genesis unlock; sponsored bonds do not prove enrollment and count as self-stake only with `sponsored_self_stake_enabled`; referral and lottery mechanics remain draft/off-chain rather than eligibility or allocation proof; and the normative 20% failed/early-close penalty goes to `FLOPFoundationAccount` with zero burn while the runtime remains only `PARTIAL` because it still burns that leg.

`evidence/fixtures/official-criteria-2026-10-26.json` preserves the normalized text used for all eight baseline hashes, so tests verify the committed snapshot without rewriting hashes or depending on a live fetch.

Exit codes:

```text
0  baseline unchanged
1  fetch, parse, or manifest failure
2  content changed but all material markers remain
3  one or more material markers disappeared
```

Run:

```bash
python3 criteria_monitor.py --manifest evidence/official-criteria.json
python3 criteria_monitor.py --manifest evidence/official-criteria.json --manifest-only
```

The tool uses GET only. It has no signing, wallet, key loading, transaction, POST, publication, or file-write path.

## Known unresolved draft conflicts

At the 2026-10-26 snapshot:

- testnet onboarding permits inference purchases or Technocore transactions, while the scoring section credits agents only for compute purchased in settled sessions.

Until final rules resolve the second ambiguity, Technocore traffic, job counts, faucet balances, token holding, self-demand, and circular/common-control demand are not treated as agent credit.

## Current eligibility boundary

The monitored official material supports only these bounded statements:

- dates and operational rules remain provisional;
- testnet is planned for Q4 2026 and about 90 days, with a published finalized snapshot followed by allocation review and a dispute window;
- agent scoring is based on compute purchased in settled sessions;
- wallets under common control receive one score, and common-control demand is excluded;
- the draft genesis allocation is 4.4B FLOP, or 24.3% of year-10 supply;
- the current agent guide and dedicated draft airdrop page both describe a 3:1 agent spend-to-unlock rule, while eligibility, timing, and exact-identity allocation remain unverified;
- miner block rewards and settled miner channel payouts are post-genesis unlock inputs under D-0527; this is separate from testnet scoring and excludes fees, refunds, penalties, and bonds;
- sponsor-funded operator bonds do not prove enrollment, and their self-stake treatment depends on the named runtime flag;
- referral leaderboard and lottery language remains draft and off-chain;
- the failed/early-close penalty's normative sink is the Foundation with zero burn, while the documented runtime still burns it.

It does **not** establish that the NaNaz DID is eligible, how much it receives, whether anything is claimable, or whether payment occurred. Those states remain `UNVERIFIED` until an authoritative exact-identity receipt exists.
