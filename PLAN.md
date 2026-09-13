# FLOP Evidence-First Execution Plan

## Objective
Convert the existing Technocore footprint into a defensible, public-ready contribution under the main NAK DID without publishing secrets or claiming unverified FLOP eligibility.

## Scope
1. Stop and persistently disable the generic Kibble worker.
2. Preserve state/code evidence with checksums.
3. Produce deterministic aggregate statistics from local state and campaign logs.
4. Write a transparent flagship report describing method, findings, limitations, and quality failure.
5. Replace the generic worker with a fail-closed quality-gated v2 that defaults to dry-run and never posts automatically.
6. Prepare, but do not externally publish, the contribution announcement and creator application package.

## Safety boundaries
- Never read or publish identity.pem, .tc_pass, account private material, wallet identifiers, IPs, or host details.
- Aggregate 50K campaign data only.
- A posted DELIVER is not an ATTEST, ACCEPT, allocation, or token receipt.
- External publication and creator-form submission remain separate reviewed actions.

## Verification
- Unit tests for aggregation, redaction, source/citation gating, build-evidence gating, and dry-run behavior.
- Fresh local analysis output with SHA-256 checksums.
- Secret-pattern scan of the public-ready bundle.
- PM2 readback proving the legacy worker is stopped and persisted.
