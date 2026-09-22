# FLOP Allocation Evidence Roadmap

This roadmap measures completed, checkable work. It does **not** estimate or guarantee a FLOP allocation.

## Scoring policy

- Total: 100 points, earned in fixed 5-point tranches.
- Daily operating target: attempt one complete 5-point tranche.
- Points move only when the named acceptance criteria and evidence exist.
- Administrative activity, message volume, drafts, pending reviews, and self-claims earn zero points.
- `evidence/progress.json` is the score ledger; every scored tranche names concrete repository artifacts.
- Official eligibility, allocation, and payment remain separate external decisions.

## Scorecard

| ID | Workstream | Weight | Current | Evidence / next gate |
|---|---|---:|---:|---|
| evidence | Evidence foundation and claim boundaries | 20 | 10 | Published report/metrics and deterministic analyzer/tests are ledgered below. Next: independently verifiable receipt fixtures. |
| flagship_tooling | Quality-gated flagship tooling | 20 | 10 | Offline quality gate plus pinned-DID receipt verifier, fixtures, docs, and tests are ledgered below. |
| independent_validation | Independent validation and adoption | 20 | 0 | Next: independently attributable useful attestations, users, issues, forks, or accepted contributions. |
| community | Public education and community activity | 15 | 0 | Application/thread existence is not scored without auditable adoption evidence. |
| flipt_case_study | Flipt lifecycle engineering case study | 15 | 5 | Public-safe Arc Testnet references, state-machine validator, docs, and adversarial tests are ledgered below. |
| official_readiness | Official-program and testnet readiness | 10 | 0 | Identity and registrations are not scored as allocation readiness without an auditable tranche. |
| **Total** |  | **100** | **25** | Conservative score backed by the completed-tranche ledger. |

## Completed evidence ledger — 25 points

### evidence_report_v1 — Claim-boundary report and metrics (5 points)

- Workstream: `evidence`
- Status: `verified`
- Artifact: `README.md` — sha256 `56cbb3ede789bcad1b5f0e044d5595909fbb04b320cb7c064cf29740f8f5d4b5`
- Artifact: `evidence/metrics.json` — sha256 `05a0d1346f14ead8141d14591befc5d0bbfa5beb6239fe64097354f893fdedf6`

Evidence boundary: the public report publishes aggregate metrics and source commitments while explicitly refusing to treat local delivery volume as useful work, eligibility, allocation, or payment.

### deterministic_analyzer_v1 — Deterministic analyzer (5 points)

- Workstream: `evidence`
- Status: `verified`
- Artifact: `analyze.py` — sha256 `b8004fb8487793f36a4847ece200ab2db5af0e078a8cbdb3439b71064e2d7444`
- Artifact: `tests/test_analyze.py` — sha256 `ac89b5dbc7fa3fdbb472456847a09199661213815f3a9717819ba9f86d36a74f`

Evidence boundary: tests cover DID derivation, aggregate-state calculation, shape-valid delivery counts, and exclusion of private fields from public output.

### offline_quality_gate_v1 — Offline quality gate (5 points)

- Workstream: `flagship_tooling`
- Status: `verified`
- Artifact: `quality_worker.py` — sha256 `e54b4750f0202a2c70d25a8efa9136fe0f890fb643c41ffb22a288f7064f8d7e`
- Artifact: `tests/test_quality_worker.py` — sha256 `d78bd0b45dd155d7663ffb29ce0f48ed9ed8bba566213cc0ae7bf34cf60eb814`

Evidence boundary: tests reject boilerplate, sensitive credential shapes, private URLs, and unsupported build/research claims. Passing the structural gate never approves publication.

### signed_receipt_verifier_v1 — Signed Technocore receipt verifier (5 points)

- Workstream: `flagship_tooling`
- Status: `verified`
- Artifact: `receipt_verifier.py` — sha256 `9a6fd3fd1a968c64c9bfe9c40f22978caeac3dcb62048dc808cee98948dffa54`
- Artifact: `tests/test_receipt_verifier.py` — sha256 `dcd046b4f29e30b541083492116351915617c5e608c9d6074e77001559010952`
- Artifact: `docs/receipt-verifier.md` — sha256 `2bc70df07803f6ab4a8611e57ee90e3b392879acdd8f95deecec6a184f5a9f9b`
- Artifact: `evidence/fixtures/technocore-valid.json` — sha256 `a3e94e03fbab39d2fc7de4cbc375658b077c17ec546d9d11cc957bcda85f1d52`
- Artifact: `evidence/fixtures/technocore-invalid-text.json` — sha256 `827ea304d8383d9e1d9061f70153599fa175c99a6a65ec9c246ea63d22a28f96`
- Artifact: `evidence/fixtures/technocore-invalid-signature.json` — sha256 `bc61b0a13690008aa3a293224284d183504ac1b7efb9806dc5ec870003ab16a8`
- Artifact: `evidence/fixtures/technocore-wrong-signer.json` — sha256 `d4dc54122b6ae2d0b0965335f4e87e99900e103a76572db4c8990bd6ae969fb5`

Evidence boundary: the offline verifier checks exact `room|nonce|text` bytes against an operator-pinned Ed25519 DID. Deterministic fixtures cover valid, tampered-text, tampered-signature, and wrong-signer records. Verification proves authorship and integrity only—not usefulness, acceptance, eligibility, allocation, payment, or on-chain activity.

### flipt_case_study_v1 — Flipt lifecycle case study (5 points)

- Workstream: `flipt_case_study`
- Status: `verified`
- Artifact: `FLOP_FLIPT_CASE_STUDY.md` — sha256 `b2bce836054afc202e2fdab268fbf148292d60bb61f744846750459ff80e6757`
- Artifact: `flipt_lifecycle.py` — sha256 `5c7c84d956152c2290c642653ffd729bede5ce48aad55dbf22b9a9cd5201f230`
- Artifact: `tests/test_flipt_lifecycle.py` — sha256 `7e63d28503d4a3aabd8c3f00bad82ccbeddb27c1ec7e5eae82dee26d70532683`
- Artifact: `evidence/fixtures/flipt-lifecycle-valid.json` — sha256 `fb998cfdc18d88e8249fddd5d8bf38a6c180d0b420010520eb7c6bd9d8d65eea`
- Artifact: `docs/flipt-lifecycle.md` — sha256 `846626dc61bdbb0f96d271af8a760ffdca6605187c97e3ed8ad5e94ad1311126`

Evidence boundary: six immutable Arc Testnet transaction references support graduation, unbond, release, liquidity, and one Auto-Sell tranche through filled settlement. The offline validator enforces ordering, exact maturity, classification, source binding, and exclusion of literal addresses/balances. The explicitly approved public testnet links can reveal isolated burner/executor addresses. This does not prove FLOP eligibility, allocation, payment, mainnet value, or future rewards.

## Pending evidence ledger — 0 unscored points

No pending tranche is scored.

## Next 5-point tranches

1. **Independent validation package (5 points)**
   - Curate 10–20 strongest contributions.
   - Bind each to evidence, result hash, and external ATTEST/ACCEPT state.
   - Unverified entries remain explicitly unverified.

2. **Community adoption evidence (5 points)**
   - Publish a bilingual tutorial or demo.
   - Record real, non-Sybil use: issue, fork, installation receipt, or independent feedback.

3. **Official criteria monitor and testnet readiness (5 points)**
   - Detect material changes in official Flop Labs sources.
   - Prepare receipt-first tooling without wallet signing or irreversible actions.

## Daily execution rules

- Prefer one complete 5-point tranche over five unfinished tasks.
- Never revive generic Kibble volume farming.
- Never create identity farms or fake engagement.
- Never expose keys, private/mainnet wallet identifiers, private balances, host details, or raw private logs. Isolated testnet transaction references require explicit operator approval and a written disclosure boundary.
- Public writes require privacy review, tests, exact-target verification, and read-back.
- If an external dependency blocks a tranche, work on the next independent tranche and report the blocker honestly.
