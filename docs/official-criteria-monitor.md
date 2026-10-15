# Official FLOP criteria monitor

`criteria_monitor.py` performs a read-only drift check over seven official FLOP draft surfaces pinned in `evidence/official-criteria.json`.

## Sources and authority

1. `flop.finance/intro/yellowpaper/` — official draft normative specification.
2. `flop.finance/testnet/` — provisional testnet timeline, onboarding, scoring, snapshot, review, and anti-Sybil rules.
3. `flop.finance/airdrop/` — draft genesis allocation, distribution, claim, and unlock terms.
4. `ask.flop.finance/docs/protocol-parameters` — official draft parameter reference.
5. `flop.finance/intro/agent` and `/intro/miner` — official draft role guides.
6. `flop.finance/teaser/` — official provisional overview; it defers to the Yellow Paper.

The reviewed normative reference is pinned separately to Yellow Paper `0.5.0-draft`, commit `70e691c758e53eed17a016a02b0a2ae1200d3744`, tree `59657ba8775ad27ff1a4e2245a18d6ebcccb8559`, published from `flop-core@5e6e24279`. The pin records provenance; it does not make the draft final.

No monitored page is treated as an identity-specific eligibility receipt. The hierarchy prevents an older overview from silently overriding a dedicated rule page, but it does not guess which unresolved draft value will become final.

## What the monitor detects

For each allowlisted HTTPS source, the monitor:

- extracts visible text while excluding scripts, styles, SVG, and other non-content blocks;
- normalizes whitespace and computes SHA-256;
- compares the digest with the captured baseline;
- verifies markers for draft authority, settled-session scoring, common-control aggregation, independent demand, snapshot/review flow, genesis allocation, claim handling, and unlock terms;
- reports known official draft conflicts instead of choosing whichever rule is convenient.

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

At the 2026-10-15 snapshot:

- the protocol-parameter summary says agent release is not yet set, while the dedicated draft airdrop page specifies that every three locked FLOP spent in settled sessions unlocks one FLOP;
- testnet onboarding permits inference purchases or Technocore transactions, while the scoring section credits agents only for compute purchased in settled sessions.

Until final rules resolve the second ambiguity, Technocore traffic, job counts, faucet balances, token holding, self-demand, and circular/common-control demand are not treated as agent credit.

## Current eligibility boundary

The monitored official material supports only these bounded statements:

- dates and operational rules remain provisional;
- testnet is planned for Q4 2026 and about 90 days, with a published finalized snapshot followed by allocation review and a dispute window;
- agent scoring is based on compute purchased in settled sessions;
- wallets under common control receive one score, and common-control demand is excluded;
- the draft genesis allocation is 4.4B FLOP, or 24.3% of year-10 supply;
- the dedicated draft airdrop page specifies no claim deadline and a 3:1 agent spend-to-unlock rule, while another official summary still says release is not yet set.

It does **not** establish that the NaNaz DID is eligible, how much it receives, whether anything is claimable, or whether payment occurred. Those states remain `UNVERIFIED` until an authoritative exact-identity receipt exists.
