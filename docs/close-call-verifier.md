# Close Call official package verifier

`close_call_verifier.py` implements the new official participation gate announced by Arthur Hayes on [25 September 2026](https://x.com/CryptoHayes/status/2103453504513937720) and published by [`flop-labs/technocore-close-call-challenge`](https://github.com/flop-labs/technocore-close-call-challenge).

## Trust anchors

- Official repository commit: [`66c1da36538e4b1c685417d2f66922906b13fea0`](https://github.com/flop-labs/technocore-close-call-challenge/commit/66c1da36538e4b1c685417d2f66922906b13fea0)
- Manifest SHA-256: `bae09812e25eb6f1369c611f24964f7ea0acafddfc45301a16f33f941296dafa`
- Launch seed: `d-close1-price` sequence `1`, package hash equal to the manifest hash, reference trade timestamp `2026-09-25T11:59:42.666000Z`, trade ID `626256716983248`

The repository still labels the package `draft`, but the public launch seed pins that exact manifest and the referee is posting live sweeps. The verifier preserves both facts rather than editing reality until it behaves.

## Deterministic checks

The offline command:

```bash
python3 close_call_verifier.py
```

1. verifies the full manifest hash against both the commit pin and launch seed;
2. verifies exact bytes and manifest entries for the official fold, contest configuration, and sample season input;
3. enforces the live rules that matter to replay: 5% limit window, 1% fee, closing-price clawback, lock at `2026-10-04T09:00:00Z`, final price at `2026-10-04T10:00:00Z`;
4. executes the exact official fold over the official three-sweep sample;
5. compares the complete result to a deterministic JSON snapshot and confirms six owners plus exact zero-sum accounting.

The vendored subset is intentionally minimal. The complete upstream package was independently checked at the pinned commit with `scripts/verify.py` (15 artifacts), `scripts/build.py --check`, and 18 upstream tests.

## Evidence boundary

This tranche verifies package integrity and deterministic replay for a newly announced official contest. It does **not** register a DID, sign or post a trade, claim the operator participated, or infer a result from an omitted referee list.

Lifecycle remains separate:

`package verified → registration UNVERIFIED → mint UNVERIFIED → settlement UNVERIFIED → ranking UNVERIFIED → prize eligibility UNVERIFIED → claimable UNVERIFIED → claimed UNVERIFIED → paid UNVERIFIED`

Registration and trading require key use and are **MANUAL REQUIRED**. The live contest prize is conditional on future mainnet launch and final ranking; no token value or financial return is asserted. No financial advice.
