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
| flagship_tooling | Quality-gated flagship tooling | 20 | 5 | Offline quality gate and tests are ledgered below. Next: release-quality signed-receipt verifier. |
| independent_validation | Independent validation and adoption | 20 | 0 | Next: independently attributable useful attestations, users, issues, forks, or accepted contributions. |
| community | Public education and community activity | 15 | 0 | Application/thread existence is not scored without auditable adoption evidence. |
| flipt_case_study | Flipt lifecycle engineering case study | 15 | 0 | Draft exists but is pending public-safe, independently checkable receipt evidence. |
| official_readiness | Official-program and testnet readiness | 10 | 0 | Identity and registrations are not scored as allocation readiness without an auditable tranche. |
| **Total** |  | **100** | **15** | Conservative score backed by the completed-tranche ledger. |

## Completed evidence ledger — 15 points

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

## Pending evidence ledger — 5 unscored points

### flipt_case_study_v1 — Flipt lifecycle case study (5 points)

- Workstream: `flipt_case_study`
- Status: `pending`
- Artifact: `FLOP_FLIPT_CASE_STUDY.md`

The narrative and privacy scan are useful but insufficient for evidence-only scoring. Before it can earn five points or be published, it needs public-safe receipt fixtures or other independently checkable evidence supporting the lifecycle claims. Until then its contribution is **0 points**.

## Next 5-point tranches

1. **Flagship receipt verifier (5 points)**
   - Verify signed Technocore records against a pinned DID.
   - Include deterministic positive and negative fixtures.
   - No key loading or network write/publish path.

2. **Flipt public evidence package (5 points)**
   - Add privacy-reviewed receipt/event fixtures and deterministic hashes.
   - Preserve claim boundaries and avoid wallet/private-balance disclosure.
   - Re-run independent evidence/security review before publication.

3. **Independent validation package (5 points)**
   - Curate 10–20 strongest contributions.
   - Bind each to evidence, result hash, and external ATTEST/ACCEPT state.
   - Unverified entries remain explicitly unverified.

4. **Community adoption evidence (5 points)**
   - Publish a bilingual tutorial or demo.
   - Record real, non-Sybil use: issue, fork, installation receipt, or independent feedback.

5. **Official criteria monitor and testnet readiness (5 points)**
   - Detect material changes in official Flop Labs sources.
   - Prepare receipt-first tooling without wallet signing or irreversible actions.

## Daily execution rules

- Prefer one complete 5-point tranche over five unfinished tasks.
- Never revive generic Kibble volume farming.
- Never create identity farms or fake engagement.
- Never expose keys, wallet identifiers, private balances, host details, or raw private logs.
- Public writes require privacy review, tests, exact-target verification, and read-back.
- If an external dependency blocks a tranche, work on the next independent tranche and report the blocker honestly.
