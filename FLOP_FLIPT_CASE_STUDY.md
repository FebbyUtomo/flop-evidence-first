# Flipt Phase Ø: Evidence-First Lifecycle Case Study

## Scope and claim boundary

This report summarizes a bounded Arc testnet experiment performed through the Flipt interface in September 2026. It documents observed protocol behavior and engineering findings. Test tokens, displayed balances, and testnet rewards are not income, mainnet assets, FLOP allocation, or proof of future eligibility.

Private/mainnet wallet identifiers, account balances, operator infrastructure, and credentials are intentionally excluded. A public-safe fixture retains six immutable Arc Testnet transaction references, block/timestamp facts, and bounded lifecycle fields. Following explicit operator approval, those links intentionally make the isolated testnet burner and public executor addresses discoverable through Arcscan; they are not represented as private or mainnet identities.

## Lifecycle coverage

The experiment verified these state transitions:

1. Token and pool creation with an initial bonding-curve purchase.
2. Graduation from the bonding curve into the post-graduation pool.
3. Post-graduation buy and partial sell.
4. Creator-reward collection with separate bonding-curve and trading-pool components.
5. Unbond initiation and an exact 90-second maturation interval.
6. Release of matured tokens without selling, repeated across three claims.
7. Post-graduation liquidity provision and receipt of an LP position token.
8. Creation of two Auto-Sell tranches.
9. Public maturation state followed by execution from an external keeper.
10. Final filled-state observation and test-USDC settlement.

## Important classification correction

An early UI interpretation treated a mode-2 operation as a Conditional Exit Order. Later UI evidence exposed the authoritative label `SELL TRANCHES`, and subsequent executor receipts showed the operation was an **Auto-Sell tranche**.

The evidence record was corrected instead of preserving the more interesting but inaccurate label. This matters because Auto-Sell and Conditional Exit have different trigger semantics, state transitions, and user expectations. A transaction succeeding does not prove the operator correctly understood the product action.

## Observed mechanics

### Unbond and release

- An unbond request moved tokens into a pending-release state.
- The recorded unlock interval was exactly 90 seconds.
- Releasing a matured request transferred the tokens without performing a pool swap.
- Three separate releases reproduced that behavior.

### Creator rewards

The collection action exposed distinct reward components from the bonding curve and the trading pool. The experiment records these only as testnet protocol outputs. No conversion to real-world value or FLOP entitlement is claimed.

### Liquidity position

A post-graduation liquidity-add action deposited both pool assets and returned an LP-position token. This established that the lifecycle continued beyond graduation and spot trading.

### Auto-Sell and keeper execution

Two equal-sized Auto-Sell tranches were created. For each observed tranche:

- the UI displayed a maturation state;
- keeper funding was attached;
- maturation preceded execution;
- an external address executed the ready tranche;
- the resulting test-USDC was delivered after fees/reward handling;
- the final state was `filled`.

This is consistent with an external keeper path. The public fixture establishes that a separate finalized execution transaction followed maturity, while deliberately excluding the executor address. It therefore supports external execution without claiming public identity attribution.

## Public evidence package

The case study is accompanied by:

- `evidence/fixtures/flipt-lifecycle-valid.json` — six public Arc Testnet transaction references covering graduation, unbond, release, liquidity, and an Auto-Sell tranche through filled settlement;
- `flipt_lifecycle.py` — offline, read-only state-machine and privacy validator;
- `tests/test_flipt_lifecycle.py` — deterministic positive and adversarial tests;
- `docs/flipt-lifecycle.md` — reproduction steps and evidence boundaries.

The validator rejects reordered events, premature release/execution, duplicate transaction hashes, source/hash mismatches, Conditional Exit misclassification, wallet addresses, balances, and sensitive key names. It does not fetch the network; each source URL is available for independent read-back.

## Engineering findings

1. **Action labels must be captured before signing.** Method selectors and successful receipts alone are insufficient to distinguish similar exit modes.
2. **State-machine evidence should span the whole transition.** Creation, maturation, execution, settlement, and final status are separate checkpoints.
3. **External execution is meaningful evidence.** A third-party keeper receipt distinguishes protocol liveness from an operator manually completing both sides.
4. **Balance deltas need semantic context.** A token release and a token sale may both change balances but represent different product actions.
5. **Testnet output must stay clearly labeled.** Large displayed numbers are especially easy to misrepresent as rewards or profit.
6. **Corrections improve evidence quality.** Updating the report after stronger UI evidence is more useful than defending an early assumption.

## Remaining test gaps

The following were not established by this experiment and remain separate future tests:

- a genuine Conditional Exit Order with its trigger parameters captured before signing;
- partial conditional-order execution;
- cancellation while an Auto-Sell tranche is still pending;
- wallet rejection recovery without creating a ghost order;
- authoritative leaderboard placement or tier;
- official Flop Labs eligibility, allocation, claimability, or payment.

## Reusable verification checklist

For each future state-changing test:

1. Capture the exact UI action label and all parameters before approval.
2. Use a bounded test amount and finite approval.
3. Record the pre-action state.
4. Verify the transaction receipt and decoded events.
5. Observe intermediate state transitions and timestamps.
6. Confirm settlement with token-transfer and balance-delta evidence.
7. Read back the final application state.
8. Record contradictions and corrections rather than normalizing them away.
9. Keep testnet units separate from financial value and reward projections.
10. Publish only after privacy and secret scanning.

## Outcome

The experiment produced a broad lifecycle trace and one especially useful correction: the tested automated exit path was Auto-Sell, not Conditional Exit. Its value is technical evidence and reusable testing methodology—not a promise of FLOP rewards.
