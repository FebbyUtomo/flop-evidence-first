# Official FLOP criteria monitor

`criteria_monitor.py` performs a read-only drift check over five official FLOP draft surfaces pinned in `evidence/official-criteria.json`.

## Sources and authority

1. `flop.finance/intro/yellowpaper/` — official draft normative specification. It explicitly separates designed, implemented, and open items.
2. `ask.flop.finance/docs/protocol-parameters` — official draft parameter reference.
3. `flop.finance/intro/agent` and `/intro/miner` — official draft role guides.
4. `flop.finance/teaser/` — official provisional overview. The page itself defers to the Yellow Paper and says its figures may change.

No monitored page is treated as an identity-specific eligibility receipt. The hierarchy prevents an older teaser value from silently overriding a newer draft specification, but it does not guess which unresolved draft value will become final.

## What the monitor detects

For each allowlisted HTTPS source, the monitor:

- extracts visible text while excluding scripts, styles, SVG, and other non-content blocks;
- normalizes whitespace and computes SHA-256;
- compares the digest with the captured baseline;
- verifies material markers for authority, draft status, testnet mechanics, and allocation-related parameters;
- reports known official draft conflicts rather than choosing whichever number looks nicer.

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

At the 2026-09-22 snapshot:

- the provisional teaser describes a floor after the **fifth halving**, while the parameter reference states **six halvings**;
- the miner role guide states a **75% miner reward pool**, while the parameter reference states a **90% miner share**.

These conflicts are evidence that the criteria remain drafts, not a reason to select the larger number. Any disappearance or wording change is a review trigger.

## Current eligibility boundary

The monitored official material supports these bounded statements:

- testnet participation is planned as the basis for genesis distribution;
- agent activity centers on claiming test tokens and spending them on inference;
- the current agent guide states a `3:1` inference-spend unlock ratio;
- official protocol and reward parameters remain draft and internally inconsistent.

It does **not** establish that the NaNaz DID is eligible, how much it receives, whether anything is claimable, or whether payment occurred. Those states remain `UNVERIFIED` until an authoritative exact-identity receipt exists.
