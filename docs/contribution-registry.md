# Curated contribution registry

`evidence/contributions.json` curates ten strongest public results in this repository. Every entry binds one repository-relative artifact to its SHA-256 digest, the full commit that published that version, and a commit-pinned public URL.

Run the verifier offline:

```bash
uv run --isolated --no-project --python 3.14 \
  --with 'cryptography>=46,<47' \
  python contribution_registry.py evidence/contributions.json
```

A successful run reports ten verified result hashes and separate `attest` and `accept` counts. The verifier is fail-closed: it rejects fewer than 10 or more than 20 entries, changed artifacts, duplicate results, malformed commits, branch-relative URLs, unknown status values, and `VERIFIED` external states without both an independent DID and HTTPS evidence.

## Status boundary

`attest` means an independent actor reproduced or reviewed the exact result and signed an attributable receipt for the recorded outcome. `accept` means an independent adopter, job poster, or maintainer accepted the exact result for a concrete use. They are not aliases for a self-signed publication message, a Git commit, tests passing, or a submitted form.

## Verified external receipt

One `ATTEST` is verified for `roadmap_integrity_validator`; the other nine `ATTEST` fields and all ten `ACCEPT` fields remain `UNVERIFIED`.

- Reviewer: [`putrikeme`](https://github.com/putrikeme), GitHub account `107520232`, account created in 2022.
- Actor DID: `did:key:z6MkuzkFDAwgSXgSVhxruVD4DGzuxCieeXonpsgCApd9o6Ms`.
- Reviewed source commit: [`f47143668521ede1aee7dc3c37746fb00d9eee24`](https://github.com/FebbyUtomo/flop-evidence-first/commit/f47143668521ede1aee7dc3c37746fb00d9eee24).
- Immutable receipt snapshot: [`6d931570047ba065a83702083efd08d615da9686`](https://github.com/putrikeme/flop-evidence-first/tree/6d931570047ba065a83702083efd08d615da9686/reviews/f471436).
- Contribution mapping and independence statement: [issue comment `6387074008`](https://github.com/FebbyUtomo/flop-evidence-first/issues/1#issuecomment-6387074008).
- Artifact SHA-256: `1f8628721dbafe4e8cc60817d5ceb8349c27cc83725b10bce4f071b0526e4c6b`.
- Transcript SHA-256: `4248e1f4439eef275e75e9bddc6253d2fbc234cd8f0738c92b66354572c2c636`.

The detached Ed25519 signature verifies against the published key, the key derives to the stated DID, and both published file hashes match. The signed receipt binds the repository commit, source-archive hash, transcript hash, actor DID, environment, and PASS result. The authenticated public GitHub comment separately binds that receipt snapshot to `roadmap_integrity_validator` and declares independent account/key control; its exact API response is preserved and hash-checked as `mapping-comment.json`. The immutable reviewer commit and exact issue-comment URL are pinned fail-closed by the validator. The artifact hash is reproduced with the receipt's exact archive recipe—`git archive --format=tar --prefix=flop-evidence-first-f47143668521ede1aee7dc3c37746fb00d9eee24/ f47143668521ede1aee7dc3c37746fb00d9eee24`—not with an unprefixed archive or GitHub codeload defaults. The transcript records 99 normal and 99 optimized tests passing plus registry, roadmap, compile, and diff checks. This composite evidence establishes one independent exact-result attestation—not official FLOP Labs acceptance.

Likewise, this package does not prove FLOP eligibility, allocation, claimability, payment, or financial value. Official allocation remains `UNVERIFIED` until an authoritative exact-identity receipt exists.
