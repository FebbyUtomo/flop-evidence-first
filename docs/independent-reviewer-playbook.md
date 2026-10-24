# Independent FLOP Reviewer Playbook

> Reproduce, audit, and publicly attest `flop-evidence-first` at one exact Git commit.
>
> **Target commit:** `f47143668521ede1aee7dc3c37746fb00d9eee24`  
> **Baseline for review:** `cccbf9bfc6fa526007f8da512dbfd47b46e3f3ce`  
> **Repository:** <https://github.com/FebbyUtomo/flop-evidence-first>

This guide is for a genuinely independent reviewer: a person or organization not controlled by the repository owner. It produces a reproducible transcript and a public, signed receipt whose verdict can be `ATTEST`, `ACCEPT`, or `REJECT`.

The workflow is read-only. It does **not** require a wallet, token, payment, seed phrase, private key belonging to someone else, API key, login, or interaction with a FLOP contract. Review code, not vibes—the latter has terrible test coverage.

## 1. What this review can and cannot prove

A valid receipt can prove that an independent actor:

- checked out one exact source commit;
- hashed a deterministic source archive;
- ran the documented validators and tests in a stated environment;
- recorded the exact outputs and exit codes;
- published a verdict bound to the commit, artifact hash, and transcript hash;
- signed the receipt using a reviewer-controlled key.

It does **not** prove:

- official FLOP Labs recognition;
- token eligibility, allocation, claimability, payment, or future value;
- that testnet or public operator enrollment is live;
- that a token, mint, presale, claim, or contract address is official.

At the pinned revision, recognition, eligibility, allocation, claim, and payment remain **UNVERIFIED**. Current safety state: `SECURITY_WARNING_NO_LIVE_TOKEN`. FLOP's official security position is that there is no live FLOP token. Treat every token/claim/contract route as invalid unless it appears on <https://flop.finance/official> and is confirmed by `@flop_labs`. The announced 3 November 2026 testnet date is a working target, not a fixed date or proof that testnet/enrollment is live.

## 2. Verdict definitions

Choose exactly one verdict after reviewing the evidence:

- **`ATTEST`** — you independently reproduced the stated result at the exact commit and found the recorded outcome accurate.
- **`ACCEPT`** — you reproduced the result and adopted a named artifact for a real, disclosed use. State the exact artifact and acceptance scope.
- **`REJECT`** — reproduction failed or a material claim is unsupported. Include commands, outputs, and a precise reason. A good rejection is useful evidence; it must not be relabeled as `ATTEST` or `ACCEPT`.

A GitHub account, wallet, bot, or DID controlled by the repository owner is **not** an independent reviewer.

## 3. Prerequisites

Required:

- a clean Linux/macOS/WSL environment;
- Git;
- Python 3.11 or newer;
- [`uv`](https://docs.astral.sh/uv/) for an isolated Python environment;
- Bash;
- SHA-256 tooling (`sha256sum`; macOS can use `shasum -a 256`);
- an HTTPS location you control for publishing the receipt package.

The source has one runtime dependency, `cryptography`. The commands below use
an isolated `uv` environment and constrain it to `cryptography>=46,<47`; they
do not modify the repository or the reviewer's system Python.

Record tool versions before starting:

```bash
uname -a
 git --version
python3 --version
uv --version
```

## 4. Use a fresh workspace and pin the exact commit

Set immutable review identifiers:

```bash
export REPO_URL="https://github.com/FebbyUtomo/flop-evidence-first.git"
export TARGET_COMMIT="f47143668521ede1aee7dc3c37746fb00d9eee24"
export BASELINE_COMMIT="cccbf9bfc6fa526007f8da512dbfd47b46e3f3ce"
export REVIEW_DIR="$PWD/flop-independent-review"

mkdir -p "$REVIEW_DIR"
cd "$REVIEW_DIR"
git clone --no-checkout "$REPO_URL" source
cd source
git fetch --force origin "$TARGET_COMMIT"
git checkout --detach "$TARGET_COMMIT"
```

Fail closed if the checked-out revision differs:

```bash
actual_commit="$(git rev-parse HEAD)"
test "$actual_commit" = "$TARGET_COMMIT" || {
  printf 'WRONG COMMIT: expected %s, got %s\n' "$TARGET_COMMIT" "$actual_commit" >&2
  exit 1
}

test -z "$(git status --porcelain=v1)" || {
  echo "WORKTREE IS NOT CLEAN" >&2
  git status --short >&2
  exit 1
}

printf 'commit=%s\n' "$actual_commit"
printf 'tree=%s\n' "$(git rev-parse 'HEAD^{tree}')"
```

Review the exact change range in a browser or locally:

- Commit: <https://github.com/FebbyUtomo/flop-evidence-first/commit/f47143668521ede1aee7dc3c37746fb00d9eee24>
- Compare: <https://github.com/FebbyUtomo/flop-evidence-first/compare/cccbf9bfc6fa526007f8da512dbfd47b46e3f3ce...f47143668521ede1aee7dc3c37746fb00d9eee24>

```bash
git diff --stat "$BASELINE_COMMIT...$TARGET_COMMIT"
git diff --check "$BASELINE_COMMIT...$TARGET_COMMIT"
```

Do not continue if Git cannot resolve either commit or if the worktree is dirty.

## 5. Build a deterministic source artifact

Create a tar archive directly from Git. Do not archive the mutable working directory.

```bash
cd "$REVIEW_DIR/source"
git archive --format=tar \
  --prefix="flop-evidence-first-${TARGET_COMMIT}/" \
  "$TARGET_COMMIT" > "$REVIEW_DIR/source-${TARGET_COMMIT}.tar"

sha256sum "$REVIEW_DIR/source-${TARGET_COMMIT}.tar" \
  | tee "$REVIEW_DIR/artifact.sha256"
```

On macOS, replace the final command with:

```bash
shasum -a 256 "$REVIEW_DIR/source-${TARGET_COMMIT}.tar" \
  | tee "$REVIEW_DIR/artifact.sha256"
```

The first 64 hexadecimal characters in `artifact.sha256` are the **artifact SHA-256** to include in the receipt.

Optional cross-check: create the archive a second time and compare it.

```bash
git archive --format=tar \
  --prefix="flop-evidence-first-${TARGET_COMMIT}/" \
  "$TARGET_COMMIT" > "$REVIEW_DIR/source-second.tar"
cmp "$REVIEW_DIR/source-${TARGET_COMMIT}.tar" "$REVIEW_DIR/source-second.tar"
rm "$REVIEW_DIR/source-second.tar"
```

`cmp` must exit `0`.

## 6. Run the offline verification and capture one transcript

The core review uses only repository bytes. It deliberately excludes the online criteria monitor because official webpages can drift after the pinned commit.

From the repository root, run this Bash block exactly:

```bash
cd "$REVIEW_DIR/source"
set -o pipefail

{
  echo "review_schema=nanaz.flop-independent-review.v1"
  echo "target_commit=$TARGET_COMMIT"
  echo "baseline_commit=$BASELINE_COMMIT"
  echo "head=$(git rev-parse HEAD)"
  echo "tree=$(git rev-parse 'HEAD^{tree}')"
  echo "worktree_status_begin"
  git status --porcelain=v1
  echo "worktree_status_end"
  echo "environment_begin"
  uname -a
  git --version
  python3 --version
  uv --version
  echo "environment_end"

  run() {
    echo
    printf 'COMMAND:'
    printf ' %q' "$@"
    echo
    "$@"
    rc=$?
    echo "EXIT_CODE:$rc"
    return "$rc"
  }

  PY=(uv run --isolated --no-project --python 3.14 --with 'cryptography>=46,<47' python)
  run "${PY[@]}" -m unittest discover -s tests -p 'test_*.py' || exit 101
  run "${PY[@]}" -O -m unittest discover -s tests -p 'test_*.py' || exit 102
  run "${PY[@]}" contribution_registry.py || exit 103
  run "${PY[@]}" -O contribution_registry.py || exit 104
  run "${PY[@]}" scripts/verify_roadmap.py || exit 105
  run "${PY[@]}" -O scripts/verify_roadmap.py || exit 106
  run "${PY[@]}" -m compileall -q . || exit 107
  run git diff --check || exit 108

  test -z "$(git status --porcelain=v1)" || exit 109
  echo
  echo "CORE_VERDICT:PASS"
} 2>&1 | tee "$REVIEW_DIR/transcript.txt"

core_rc=${PIPESTATUS[0]}
printf 'CORE_EXIT_CODE:%s\n' "$core_rc" | tee -a "$REVIEW_DIR/transcript.txt"
test "$core_rc" -eq 0
```

Expected properties at the pinned commit:

- normal test suite passes;
- optimized (`python3 -O`) test suite also passes;
- contribution registry validates in normal and optimized modes;
- roadmap validator reports score `45`, target `100`, completed tranches `9`, and pending tranches `2`;
- registry reports `ATTEST VERIFIED = 0` and `ACCEPT VERIFIED = 0` before any independent receipt is accepted;
- Python compilation succeeds;
- `git diff --check` succeeds;
- transcript ends with `CORE_VERDICT:PASS` and `CORE_EXIT_CODE:0`.

Test counts may increase on later commits, but this review concerns only the pinned commit. Record what your machine actually prints; never edit the transcript to match this guide.

Hash the immutable transcript:

```bash
sha256sum "$REVIEW_DIR/transcript.txt" \
  | tee "$REVIEW_DIR/transcript.sha256"
```

On macOS:

```bash
shasum -a 256 "$REVIEW_DIR/transcript.txt" \
  | tee "$REVIEW_DIR/transcript.sha256"
```

The first 64 hexadecimal characters are the **transcript/result SHA-256**.

## 7. Optional online criteria check

This step is informative and must not overwrite the offline result.

```bash
cd "$REVIEW_DIR/source"
set +e
python3 criteria_monitor.py --manifest evidence/official-criteria.json \
  2>&1 | tee "$REVIEW_DIR/criteria-monitor.txt"
criteria_rc=${PIPESTATUS[0]}
echo "CRITERIA_MONITOR_EXIT_CODE:$criteria_rc" \
  | tee -a "$REVIEW_DIR/criteria-monitor.txt"
set -e
```

Interpretation:

- exit `0`: pinned official content is unchanged;
- exit `2`: content drift was detected;
- exit `3`: a material marker was lost;
- another nonzero code: execution/network failure.

Content drift is **not** a score event, token event, testnet-live event, or proof of allocation. Inspect the exact diff and official source before making any claim.

## 8. Audit checklist

Do not issue `ATTEST` or `ACCEPT` based only on green tests. Review at least:

- `README.md` — claim boundaries and current status;
- `ROADMAP.md` and `evidence/progress.json` — score provenance;
- `contribution_registry.py` and `evidence/contributions.json` — external evidence gates;
- `criteria_monitor.py` and `evidence/official-criteria.json` — official-source drift handling;
- `official_announcements.py` and `evidence/official-announcements.json` — pinned announcement handling;
- the tests covering the artifact you are attesting;
- the compare range between the baseline and target commits.

Confirm these fail-closed boundaries:

- no score increase merely because a file exists;
- no `VERIFIED` external state without an independent DID and HTTPS evidence URL;
- no claim of official allocation, claimability, or payment;
- no wallet signing or transaction path is required by this review;
- network drift cannot silently become proof of eligibility;
- target dates cannot silently become `LIVE` network status.

If a boundary fails, issue `REJECT` with evidence. Do not “fix” the transcript. The transcript is a witness, not a marketing intern.

## 9. Create the receipt

Copy the hashes first:

```bash
export ARTIFACT_SHA256="$(cut -d' ' -f1 "$REVIEW_DIR/artifact.sha256")"
export TRANSCRIPT_SHA256="$(cut -d' ' -f1 "$REVIEW_DIR/transcript.sha256")"
printf 'artifact=%s\ntranscript=%s\n' "$ARTIFACT_SHA256" "$TRANSCRIPT_SHA256"
```

Choose a reviewer identity. A public `did:key:` controlled by the reviewer is preferred. The optional recipe in section 10 creates one without a wallet.

Set receipt fields:

```bash
export REVIEWER_NAME="YOUR PUBLIC NAME OR ORGANIZATION"
export ACTOR_DID="did:key:REPLACE_WITH_REVIEWER_DID"
export VERDICT="ATTEST"  # ATTEST, ACCEPT, or REJECT
export ACCEPTANCE_SCOPE="none"  # required detail if VERDICT=ACCEPT
export REVIEW_NOTES="Independent reproduction completed; see transcript."
export CORE_EXIT_CODE="0"  # use the observed nonzero value for REJECT
export CORE_VERDICT="PASS" # use FAIL for a failed core run
export PUBLIC_RECEIPT_URL="https://example.org/flop-review-f471436/"
export REVIEW_OS="$(uname -a)"
export REVIEW_GIT="$(git --version)"
export REVIEW_PYTHON="$(python3 --version 2>&1)"
export REVIEW_UV="$(uv --version)"
```

Generate deterministic JSON using Python rather than hand-editing it:

```bash
python3 - <<'PY'
import json
import os
from pathlib import Path

review_dir = Path(os.environ["REVIEW_DIR"])
verdict = os.environ["VERDICT"]
if verdict not in {"ATTEST", "ACCEPT", "REJECT"}:
    raise SystemExit("VERDICT must be ATTEST, ACCEPT, or REJECT")
actor_did = os.environ["ACTOR_DID"]
if not actor_did.startswith("did:key:"):
    raise SystemExit("ACTOR_DID must be a public did:key identity")
acceptance_scope = os.environ["ACCEPTANCE_SCOPE"]
if verdict == "ACCEPT" and acceptance_scope == "none":
    raise SystemExit("ACCEPT requires a concrete ACCEPTANCE_SCOPE")
core_exit_code = int(os.environ["CORE_EXIT_CODE"])
core_verdict = os.environ["CORE_VERDICT"]
if (core_exit_code == 0) != (core_verdict == "PASS"):
    raise SystemExit("CORE_EXIT_CODE and CORE_VERDICT disagree")
if verdict in {"ATTEST", "ACCEPT"} and core_verdict != "PASS":
    raise SystemExit("ATTEST/ACCEPT require a passing core run")
public_url = os.environ["PUBLIC_RECEIPT_URL"]
if not public_url.startswith("https://"):
    raise SystemExit("PUBLIC_RECEIPT_URL must use HTTPS")

receipt = {
    "schema": "nanaz.flop-independent-review.v1",
    "verdict": verdict,
    "reviewer": {
        "name": os.environ["REVIEWER_NAME"],
        "actor_did": actor_did,
        "independence_statement": (
            "I am not controlled by the repository owner and did not use an "
            "owner-controlled alternate account, wallet, bot, or signing key."
        ),
    },
    "source": {
        "repository": "https://github.com/FebbyUtomo/flop-evidence-first",
        "commit": os.environ["TARGET_COMMIT"],
        "baseline_commit": os.environ["BASELINE_COMMIT"],
        "commit_url": (
            "https://github.com/FebbyUtomo/flop-evidence-first/commit/"
            + os.environ["TARGET_COMMIT"]
        ),
        "compare_url": (
            "https://github.com/FebbyUtomo/flop-evidence-first/compare/"
            + os.environ["BASELINE_COMMIT"] + "..." + os.environ["TARGET_COMMIT"]
        ),
    },
    "artifact": {
        "format": "git-archive-tar",
        "sha256": os.environ["ARTIFACT_SHA256"],
    },
    "result": {
        "transcript_file": "transcript.txt",
        "transcript_sha256": os.environ["TRANSCRIPT_SHA256"],
        "core_exit_code": core_exit_code,
        "core_verdict": core_verdict,
    },
    "environment": {
        "os": os.environ["REVIEW_OS"],
        "git": os.environ["REVIEW_GIT"],
        "python": os.environ["REVIEW_PYTHON"],
        "uv": os.environ["REVIEW_UV"],
        "python_runtime": "3.14",
        "cryptography_constraint": ">=46,<47",
    },
    "public_receipt_url": public_url,
    "acceptance_scope": acceptance_scope,
    "notes": os.environ["REVIEW_NOTES"],
    "boundaries": {
        "official_recognition": "UNVERIFIED",
        "eligibility": "UNVERIFIED",
        "allocation": "UNVERIFIED",
        "claim": "UNVERIFIED",
        "payment": "UNVERIFIED",
        "financial_advice": False,
    },
    "signature": {
        "mode": "detached-ed25519",
        "signed_file": "receipt.json",
        "signature_file": "receipt.sig",
        "public_key_file": "reviewer-ed25519-public.pem",
    },
}

(review_dir / "receipt.json").write_text(
    json.dumps(receipt, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

python3 -m json.tool "$REVIEW_DIR/receipt.json" >/dev/null
sha256sum "$REVIEW_DIR/receipt.json" | tee "$REVIEW_DIR/receipt.sha256"
```

For `REJECT`, set `CORE_EXIT_CODE` and `CORE_VERDICT=FAIL` to the observed result before generating the receipt, and make `REVIEW_NOTES` identify the exact failing command and evidence. Never publish a fabricated `PASS`.

## 10. Sign without using a wallet

Skip key generation if you already have a suitable public identity and signing
process. Otherwise, this recipe creates a dedicated Ed25519 review key using
the same isolated Python dependency as the test run. It is **not** a wallet key.

Generate the key locally and derive its matching Ed25519 `did:key`:

```bash
cd "$REVIEW_DIR"
umask 077
uv run --isolated --no-project --python 3.14 --with 'cryptography>=46,<47' \
  python - <<'PY'
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()
Path("reviewer-ed25519-private.pem").write_bytes(private_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
))
Path("reviewer-ed25519-public.pem").write_bytes(public_key.public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
))
raw_public = public_key.public_bytes(
    serialization.Encoding.Raw,
    serialization.PublicFormat.Raw,
)
payload = bytes.fromhex("ed01") + raw_public
n = int.from_bytes(payload, "big")
out = ""
while n:
    n, r = divmod(n, 58)
    out = alphabet[r] + out
leading = len(payload) - len(payload.lstrip(b"\0"))
Path("actor-did.txt").write_text(
    "did:key:z" + alphabet[0] * leading + out + "\n",
    encoding="utf-8",
)
PY

export ACTOR_DID="$(tr -d '\n' < "$REVIEW_DIR/actor-did.txt")"
printf '%s\n' "$ACTOR_DID"
```

Return to section 9 and regenerate `receipt.json` using this exact `ACTOR_DID`. Then sign the exact receipt bytes:

```bash
cd "$REVIEW_DIR"
uv run --isolated --no-project --python 3.14 --with 'cryptography>=46,<47' \
  python - <<'PY'
from pathlib import Path
from cryptography.hazmat.primitives import serialization

private_key = serialization.load_pem_private_key(
    Path("reviewer-ed25519-private.pem").read_bytes(), password=None
)
public_key = serialization.load_pem_public_key(
    Path("reviewer-ed25519-public.pem").read_bytes()
)
message = Path("receipt.json").read_bytes()
signature = private_key.sign(message)
Path("receipt.sig").write_bytes(signature)
public_key.verify(signature, message)
print("SIGNATURE_LOCAL_VERIFY:PASS")
PY
```

Verification must print `SIGNATURE_LOCAL_VERIFY:PASS` and exit `0`.

**Never publish or send `reviewer-ed25519-private.pem`.** Back it up privately or delete it after deciding whether the identity must remain reusable. Do not email it with the public receipt package.

## 11. Privacy and secret scan

The public package should contain only:

- `receipt.json`;
- `receipt.sig`;
- `receipt.sha256`;
- `reviewer-ed25519-public.pem`;
- `transcript.txt`;
- `transcript.sha256`;
- `artifact.sha256`;
- optionally the deterministic source tar.

Before publication, inspect every public file and scan for obvious secret patterns:

```bash
cd "$REVIEW_DIR"
python3 - <<'PY'
from pathlib import Path

files = [
    "receipt.json", "receipt.sha256", "transcript.txt", "transcript.sha256",
    "artifact.sha256", "reviewer-ed25519-public.pem",
]
needles = [
    "BEGIN PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY", "seed phrase",
    "mnemonic", "api_key", "api-key", "password=", "authorization: bearer",
]
failed = False
for name in files:
    text = Path(name).read_text(encoding="utf-8", errors="replace")
    for needle in needles:
        if needle.lower() in text.lower():
            print(f"POSSIBLE SECRET: {name}: {needle}")
            failed = True
raise SystemExit(1 if failed else 0)
PY
```

Also manually remove private hostnames, usernames, home-directory paths, IP addresses, email addresses, internal repository URLs, or unrelated environment variables if they appear. Do not redact commands, exit codes, hashes, commit IDs, or failure output needed to reproduce the verdict. If redaction changes `transcript.txt`, recompute its hash and regenerate/sign the receipt.

Privacy boundary: **no secrets, credentials, private keys, seed phrases, wallet material, OTPs, private conversations, or private operator context.**

## 12. Publish an HTTPS receipt

Publish the public package at the exact stable HTTPS URL already bound in
`PUBLIC_RECEIPT_URL`, for example:

```text
https://example.org/flop-review-f471436/
  receipt.json
  receipt.sig
  receipt.sha256
  reviewer-ed25519-public.pem
  transcript.txt
  transcript.sha256
  artifact.sha256
```

A public GitHub repository, immutable Git commit, GitHub Gist, or institutional archive is acceptable if all files are directly retrievable. A screenshot, private DM, mutable social post without files, or “trust me, it passed” is not enough.

After publication, verify from a fresh directory:

```bash
mkdir receipt-readback && cd receipt-readback
curl -fL -O https://example.org/flop-review-f471436/receipt.json
curl -fL -O https://example.org/flop-review-f471436/receipt.sig
curl -fL -O https://example.org/flop-review-f471436/reviewer-ed25519-public.pem
curl -fL -O https://example.org/flop-review-f471436/transcript.txt

uv run --isolated --no-project --python 3.14 --with 'cryptography>=46,<47' \
  python - <<'PY'
import hashlib
import json
from pathlib import Path
from cryptography.hazmat.primitives import serialization

r = json.loads(Path("receipt.json").read_text())
actual = hashlib.sha256(Path("transcript.txt").read_bytes()).hexdigest()
assert actual == r["result"]["transcript_sha256"], (actual, r["result"]["transcript_sha256"])
public_key = serialization.load_pem_public_key(
    Path("reviewer-ed25519-public.pem").read_bytes()
)
public_key.verify(Path("receipt.sig").read_bytes(), Path("receipt.json").read_bytes())
alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
raw_public = public_key.public_bytes(
    serialization.Encoding.Raw,
    serialization.PublicFormat.Raw,
)
payload = bytes.fromhex("ed01") + raw_public
n = int.from_bytes(payload, "big")
out = ""
while n:
    n, remainder = divmod(n, 58)
    out = alphabet[remainder] + out
leading = len(payload) - len(payload.lstrip(b"\0"))
derived_did = "did:key:z" + alphabet[0] * leading + out
assert derived_did == r["reviewer"]["actor_did"], (
    derived_did, r["reviewer"]["actor_did"]
)
print("PUBLIC_RECEIPT_READBACK:PASS")
PY
```

Do not claim publication succeeded until this readback passes.

## 13. Send the maintainer only the public evidence

Send:

- verdict: `ATTEST`, `ACCEPT`, or `REJECT`;
- reviewer public name/organization;
- reviewer `did:key`;
- exact commit `f47143668521ede1aee7dc3c37746fb00d9eee24`;
- artifact SHA-256;
- transcript SHA-256;
- public HTTPS receipt URL;
- for `ACCEPT`, the concrete artifact and use scope;
- for `REJECT`, the exact failure and evidence.

Suggested message:

```text
Independent FLOP artifact review

Verdict: ATTEST
Commit: f47143668521ede1aee7dc3c37746fb00d9eee24
Actor DID: did:key:...
Artifact SHA-256: ...
Transcript SHA-256: ...
Public signed receipt: https://...

I am independent of the repository owner. This receipt attests only to the
pinned artifact and recorded execution. It does not assert official FLOP
recognition, eligibility, allocation, claimability, payment, or token status.
```

Never send a private signing key, seed phrase, wallet connection, payment, or credential. None is needed.

## 14. Maintainer acceptance gate

The repository maintainer should not mark a registry state `VERIFIED` until all of these pass:

1. receipt URL is public HTTPS and survives fresh readback;
2. source commit is exactly pinned;
3. artifact and transcript SHA-256 values match downloaded bytes;
4. signature verifies against the published public key;
5. public key derives to the claimed `did:key`;
6. reviewer is genuinely independent;
7. verdict semantics match the evidence;
8. no secret/private context is exposed;
9. `ACCEPT` includes concrete real-world adoption scope;
10. no official recognition, token, eligibility, allocation, claim, or payment claim is smuggled into the receipt.

A receipt can improve external evidence. It does not automatically increase the roadmap score; the repository's validators and evidence policy remain authoritative.

## 15. Troubleshooting

### Wrong commit

Stop. Delete the clone or fetch and detach-checkout the exact target commit. Do not review `main` by name because it can move.

### Tests fail

Preserve the full transcript, record Python/OS/Git/uv versions, and rerun once in a fresh clone. If reproducible, publish `REJECT` with the failing command and output. Do not patch the source and call it the same artifact.

### `uv` or dependency resolution fails

Record the exact resolver/network output. Retry only in a fresh environment or
with an approved internal package mirror while keeping Python 3.14 and the
`cryptography>=46,<47` constraint unchanged. If dependencies cannot be
resolved, report an environment blocker; do not claim the test suite passed.

### Optimized tests fail but normal tests pass

Treat this as a material failure. The optimized run checks that validation does not depend on removable Python `assert` statements.

### Criteria monitor exits `2`

That means official page content drifted. It is not automatically a core failure. Review the official delta separately and do not convert it into eligibility, allocation, token, or testnet-live claims.

### Receipt signature fails after publication

The receipt bytes changed after signing, often because a web editor normalized whitespace. Upload the original bytes or regenerate the receipt, recompute its hash, sign again, and repeat public readback.

### Reviewer does not want to create a DID

Use an existing independently controlled public `did:key` and a verifiable signing method tied to it. If identity/signature binding cannot be publicly verified, publish feedback as an unsigned review—but it does not satisfy the signed `ATTEST`/`ACCEPT` gate.

---

## Completion checklist

- [ ] Fresh clone used
- [ ] Exact commit checked out in detached HEAD
- [ ] Worktree clean before and after execution
- [ ] Deterministic Git archive hashed
- [ ] Normal tests pass
- [ ] Optimized tests pass
- [ ] Registry normal/optimized pass
- [ ] Roadmap normal/optimized pass
- [ ] Compile and diff checks pass
- [ ] Transcript hashed without hidden edits
- [ ] Audit checklist reviewed
- [ ] Verdict chosen honestly
- [ ] Independent actor DID recorded
- [ ] Receipt signed and locally verified
- [ ] Privacy/secret scan passed
- [ ] Public HTTPS files read back
- [ ] Public signature and transcript hash reverified
- [ ] No wallet, payment, token, claim, or credential requested

**Final rule:** exact evidence first, score second, token stories never.