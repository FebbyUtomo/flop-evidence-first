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
| independent_validation | Independent validation and adoption | 20 | 5 | Ten strongest results are hash-bound to commit-pinned URLs with separate fail-closed ATTEST/ACCEPT states. All external states remain UNVERIFIED. |
| community | Public education and community activity | 15 | 0 | Bilingual tutorial published and announced from the pinned DID. Points stay 0 until independent adoption evidence exists. |
| flipt_case_study | Flipt lifecycle engineering case study | 15 | 5 | Public-safe Arc Testnet references, state-machine validator, docs, and adversarial tests are ledgered below. |
| official_readiness | Official-program and testnet readiness | 10 | 10 | Draft criteria monitoring plus the commit-pinned Sonnet-2 result verifier are ledgered below. |
| **Total** |  | **100** | **40** | Conservative score backed by the completed-tranche ledger. |

## Completed evidence ledger — 40 points

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

### official_criteria_monitor_v1 — Official criteria drift monitor (5 points)

- Workstream: `official_readiness`
- Status: `verified`
- Artifact: `criteria_monitor.py` — sha256 `82154c5220b8dc17eef97b1ae0723932b63ded76a7d52a5bcf878c947e94e13d`
- Artifact: `tests/test_criteria_monitor.py` — sha256 `7ae1855f7b8e1632123005e5622b5cad222080d9cbfb676d89074af61acf5e68`
- Artifact: `evidence/official-criteria.json` — sha256 `55019230bcefc786dd01e142a65bd192f72383d2f58860b2782a41d7cdc2cd78`
- Artifact: `docs/official-criteria-monitor.md` — sha256 `ae69c6ce7367ac0cf2c86ca3a95b26d55f8e63008e648b2899e7f06805dedee2`

Evidence boundary: the read-only monitor pins five official draft FLOP surfaces, detects content and material-marker drift, preserves two unresolved official contradictions, and keeps allocation `UNVERIFIED`. It has no wallet, signing, POST, transaction, publication, or file-write path.

### sonnet_results_verifier_v1 — Sonnet-2 result and allocation verifier (5 points)

- Workstream: `official_readiness`
- Status: `verified`
- Artifact: `sonnet_results_verifier.py` — sha256 `e2352c6a505c0208aa3b8755f52bab38056884d09250a5a28a982791902a4e17`
- Artifact: `tests/test_sonnet_results_verifier.py` — sha256 `8e7f31c15ee7d518adf149c9b5e6418e6883d2c6cc12a8f551bbc34d02161520`
- Artifact: `docs/sonnet-results-verifier.md` — sha256 `1e36ffec68d302f1222151f1d8f3d4e1408a945746eb08490185836875350f7b`
- Artifact: `evidence/sonnet-2-source.json` — sha256 `56ca745f7c9bf52ae1d4e45c229be668b6a5c1dda60ba52449baeec1869ae6e3`
- Artifact: `evidence/fixtures/sonnet-2-negative-cases.json` — sha256 `4b52d656ed0edabab1d16b193b8f5bbcd36def947dc98f6b40de6081326ecb18`
- Artifact: `evidence/fixtures/sonnet-2-official/manifest.json` — sha256 `c8e882f95c2892da69341b8b2a23a7441d831c59a54aa4624322bf101a8e3fd7`
- Artifact: `evidence/fixtures/sonnet-2-official/allocations.csv` — sha256 `81fd259f3c5da985e2a6366ab089db8bf643cfe47d1d750263868cdf1981f4d3`
- Artifact: `evidence/fixtures/sonnet-2-official/payouts.json` — sha256 `ebc0de591eb7108180a70cb28b5b7cf08ac0a4447fdf8e0ebfc389e47dffeff1`
- Artifact: `evidence/fixtures/sonnet-2-official/settle-receipt.json` — sha256 `87794eabb7a9091ad7b7efd3ed3c117a48f5aa163297a327088549f2801f0be7`
- Artifact: `evidence/fixtures/sonnet-2-official/standings.json` — sha256 `aa2349931e232aca68f4ae45c5fee3ee4efc6c6e53a697280d51e9eb217bbe31`

Evidence boundary: the offline verifier pins @flop_labs post `2102578439643693562` (2026-09-23T01:58:58Z) and official commit `195647a4d85733ecd4862d67dc7bf7a62e673c58`, verifies all five available package files, reconciles 6,856 exact DIDs and 97,964 allocated units across allocations, payouts, settlement, and standings, and fails closed on deterministic tampering. Primary exact-DID lookup is `NOT_LISTED`. The unavailable `allocations.json` and closed referee ledger remain a disclosed replay gap; `claimable`, `claimed`, and `paid` remain `UNVERIFIED`.

### contribution_registry_v1 — Curated contribution evidence registry (5 points)

- Workstream: `independent_validation`
- Status: `verified`
- Artifact: `contribution_registry.py` — sha256 `ee62acbc0b39eb1308512e253c0cec764b5d009f46067e582e11507a3ce43a0c`
- Artifact: `evidence/contributions.json` — sha256 `6ea15b1faccdd6ddd06dc130bc7d8c10acbd9beeb2dbdc07a35f096f51e3066c`
- Artifact: `docs/contribution-registry.md` — sha256 `18c55a1d8f38a01bf5cf98ad531aacd44ed07b9a7a86268ff4c24a87efc74080`
- Artifact: `tests/test_contribution_registry.py` — sha256 `b2833adbf199ad2592da58eb838b26f898e6e7a2d838a58a5e85916778d315c0`

Evidence boundary: ten curated public results are bound to exact artifact hashes, full commits, and commit-pinned URLs. The offline validator rejects altered results, ambiguous URLs, fake status evidence, and self-attestation presented as independent validation. All ten ATTEST and ten ACCEPT states remain `UNVERIFIED`; curation does not manufacture endorsement, eligibility, allocation, or payment.

## Pending evidence ledger — 5 unscored points

### community_tutorial_v1 — Bilingual tutorial and community announcement (5 points)

- Workstream: `community`
- Status: `pending`
- Artifact: `docs/tutorial-bilingual.md`
- Artifact: `evidence/fixtures/community-announce-receipt.json`

The bilingual tutorial and the DID-signed Technocore announcement (seq 11287734) are complete and verifiable, but community adoption evidence is still zero: no external issue, fork, install receipt, or independent feedback exists yet. Until independently attributable adoption is recorded, this tranche earns **0 points**.

## Next 5-point tranches

1. **Community adoption evidence (5 points)**
   - Publish a bilingual tutorial or demo.
   - Record real, non-Sybil use: issue, fork, installation receipt, or independent feedback.

2. **Independent acceptance upgrade (5 points)**
   - Obtain exact-result ATTEST or ACCEPT receipts from an attributable independent actor.
   - Verify the actor, receipt URL, and result hash before changing any registry status.

## Daily execution rules

- Prefer one complete 5-point tranche over five unfinished tasks.
- Never revive generic Kibble volume farming.
- Never create identity farms or fake engagement.
- Never expose keys, private/mainnet wallet identifiers, private balances, host details, or raw private logs. Isolated testnet transaction references require explicit operator approval and a written disclosure boundary.
- Public writes require privacy review, tests, exact-target verification, and read-back.
- If an external dependency blocks a tranche, work on the next independent tranche and report the blocker honestly.
