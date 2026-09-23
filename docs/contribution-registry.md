# Curated contribution registry

`evidence/contributions.json` curates ten strongest public results in this repository. Every entry binds one repository-relative artifact to its SHA-256 digest, the full commit that published that version, and a commit-pinned public URL.

Run the verifier offline:

```bash
python3 contribution_registry.py evidence/contributions.json
```

A successful run reports ten verified result hashes and separate `attest` and `accept` counts. The verifier is fail-closed: it rejects fewer than 10 or more than 20 entries, changed artifacts, duplicate results, malformed commits, branch-relative URLs, unknown status values, and `VERIFIED` external states without both an independent DID and HTTPS evidence.

## Status boundary

`attest` means an independent actor attested that the exact result was useful. `accept` means an independent job poster or maintainer accepted the exact result. They are not aliases for a self-signed publication message, a Git commit, tests passing, or a submitted form.

All twenty independent status fields currently remain `UNVERIFIED`. That is an evidence result, not an omission: no exact-result independent `ATTEST` or `ACCEPT` receipt is present in the reviewed public records. The registry therefore improves auditability without inventing endorsement.

Likewise, this package does not prove FLOP eligibility, allocation, claimability, payment, or financial value. Official allocation remains `UNVERIFIED` until an authoritative exact-identity receipt exists.
