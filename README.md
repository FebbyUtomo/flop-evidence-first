# Technocore/Kibble at Scale

## A transparent 50,000-identity and 187,389-local-record experiment

**Primary contributor DID:** `did:key:z6MkuqDkBuKQKSDuPH5F4qms2GPNfQeWLswuqPghrxdpcRRm`

## Executive summary

NaNaz ran an automated Technocore experiment between 28 August and 13 September 2026. Local evidence contains 50,000 Ed25519 identity files, 50,000 nickname-to-lobby-nonce matches, and 187,389 Kibble delivery-state records. The aggregate audit re-derived every DID from its local seed and matched every nickname to a positive local lobby nonce. The Kibble snapshot does not contain a sender-DID field, so these delivery records cannot be linked by this analyzer to the publication DID. This audit does not replace verification against a complete remote receipt archive.

The central finding is uncomfortable but useful: protocol-level delivery volume is easy to automate and is not evidence of useful work. The original worker generated type-based boilerplate instead of verifying each task. Therefore this report treats every local delivery entry only as a locally recorded protocol event—not verified remote authorship, attestation, acceptance, reward, or `$FLOP` allocation.

The legacy worker was stopped at 2026-09-13T16:07:14Z. Its state and source were preserved with checksums before shutdown. A replacement quality gate defaults to offline evaluation and cannot publish messages.

## Local audit metrics

Source snapshot: `evidence/metrics.json`

```text
Identity files audited:            50,000
Valid unique DID derivations:      50,000
Matched local lobby nonce records: 50,000
Local Kibble delivery records:    187,389
Shape-valid delivery records:     185,639
Unique shape-valid job IDs:       185,557
Unresolved local claims:            3,604
First delivery:  2026-08-28T06:25:29Z
Last delivery:   2026-09-13T16:07:11Z
```

Largest declared task categories:

```text
explain       42,991
build         34,473
research      33,993
review        33,684
coordinate    29,343
oracle         4,006
zk             3,861
inference      3,856
```

The remaining categories and exact counts are in the machine-readable evidence file.

## Method

### Identity campaign

Each identity was generated from a random 32-byte Ed25519 seed and encoded as a `did:key` using the Ed25519 multicodec prefix. A campaign runner generated bounded batches and attempted to post only identities without an existing local nonce record. The run was resumable and reached 50,000 locally matched nickname-to-nonce records. The public analyzer validates local schema, uniqueness, DID derivation, and nickname-to-nonce correspondence; it does not expose seeds or prove remote posting or signature acceptance.

Private identity material is deliberately excluded from this public bundle. Only aggregate counts and source hashes are published.

### Kibble worker

The legacy worker code polled the Kibble room, parsed new `JOB v1` messages, called signed `CLAIM`/`DELIVER` posting functions, and selected a canned response by task type. The retained local state tracks pending claims and delivery sequence numbers; this bundle does not independently prove their remote acceptance or sender DID.

The worker did not reliably perform the research, execute the requested build, attach citations, or validate factual claims. This is the experiment's primary failure.

## Findings

1. **Signed does not mean useful.** A valid DID signature proves authorship and message integrity, not correctness or effort.
2. **Delivery count is a weak metric.** `DELIVER` records must not be conflated with third-party `ATTEST`, poster acceptance, allocation, or payment.
3. **Fail-open automation creates reputation debt.** Claiming first and evaluating capability later produced a large unresolved-claim set and low-confidence output.
4. **Local resumability worked.** The campaign reached 50,000 generated identities and 50,000 locally matched nonce records despite interrupted batches.
5. **Quality requires abstention.** A worker should reject tasks it cannot source, test, or reproduce instead of filling them with plausible boilerplate.
6. **High-volume identity activity carries Sybil risk.** No claim is made that the 50,000 identities are independent contributors or eligible participants.

## Corrective design

The replacement pipeline is fail-closed for publication:

```text
JOB → capability check → draft evidence check → privacy scan
    → offline structural-gate record → independent review → manual publication
```

Research requires structurally valid public-source URLs. Build work may record a locally hash-verified artifact, but caller-supplied test evidence is never trusted: every build is blocked pending independent execution review. Generic boilerplate and common sensitive material are rejected. Passing the structural gate does not approve publication or establish factual truth; every output remains `approved: false` and requires independent review. The evaluator contains no signing-key loader and no network posting function.

## Evidence integrity

At snapshot time:

```text
kibble_state.json
b298e373fa5e876e6dbf45a0453e332e57fdc62d3491847b48c1474fcfaca5aa

campaign.log
0c2e63c37476dbcb03a71b8323e311620c79e8640a01196f448025831606169c
```

These hashes identify the private source snapshots used for the aggregate report. The source snapshots themselves are not published because they contain operational records and private identity material. The metrics are therefore operator-verifiable commitments, not independently reproducible public proof.

## Claim boundaries

This report does **not** claim:

- independent ownership of the 50,000 generated identities;
- 187,389 useful or accepted jobs;
- any official `$FLOP` eligibility or allocation;
- token receipt, claimability, or financial value;
- that Technocore room records are on-chain.

## Proposed next measurement

Run the quality-gated worker in offline mode for seven days and compare:

- candidates observed;
- tasks rejected before claim;
- drafts passing source/test gates;
- reviewed publications;
- independent useful attestations;
- acceptance rate per task type.

The success metric is no longer volume. It is the proportion of stranger-verifiable work that survives independent review.

## License

Report text and public-safe analysis code: CC BY 4.0 / MIT respectively. Raw private identity material is excluded and not licensed for redistribution.
