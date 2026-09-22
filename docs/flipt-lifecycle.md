# Flipt lifecycle evidence verifier

`flipt_lifecycle.py` validates the public-safe Arc Testnet lifecycle fixture in `evidence/fixtures/flipt-lifecycle-valid.json`.

## What it checks

- fixed Arc Testnet chain ID `5042002`;
- six successful, finalized transactions in increasing block/time order;
- each Arcscan source URL matches an exact pinned transaction hash;
- block, timestamp, selector, and SHA-256 of the raw transaction input match pinned Arcscan read-back evidence;
- graduation → unbond → release → liquidity → Auto-Sell create → Auto-Sell execute ordering;
- exact 90-second unbond and Auto-Sell maturity intervals;
- release occurs after unlock and is not represented as a swap;
- the executed tranche matches the created tranche and ends `filled`;
- Auto-Sell cannot be relabeled as Conditional Exit;
- fabricated hashes/selectors/input commitments, unknown fields, duplicate transactions, embedded addresses, and sensitive key names are rejected.

## Run

```bash
python3 flipt_lifecycle.py evidence/fixtures/flipt-lifecycle-valid.json
python3 -m unittest tests.test_flipt_lifecycle -v
```

The validator is offline and read-only. It performs no RPC calls, signing, transaction submission, or file writes. The fixture contains transaction hashes, immutable public Arcscan API URLs, and hashes of the exact calldata captured during read-back. It excludes literal account addresses, wallet balances, credentials, raw RPC payloads, and private infrastructure. With explicit operator approval, following the public testnet links can reveal the isolated burner and executor addresses; no private/mainnet identity is asserted or published.

The pinned Auto-Sell create calldata commitment covers mode code `2`; the pinned execution calldata commitment covers tranche `5170` and its input amount. The final settlement amount is also checked against the public fixture. This prevents relabeling arbitrary transaction metadata as lifecycle evidence while keeping raw address-bearing calldata out of the bundle.

## Evidence boundary

The public transaction references make the recorded testnet events independently inspectable. The deterministic validator checks the declared lifecycle relationships and privacy boundary; it does not establish FLOP eligibility, allocation, payment, mainnet value, or future rewards.
