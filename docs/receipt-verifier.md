# Offline Technocore Receipt Verifier

## Purpose / Tujuan

`receipt_verifier.py` verifies one captured Technocore room record against an exact, operator-pinned Ed25519 `did:key`. It is read-only and offline: no HTTP client, key loader, signing function, file writer, claim, or publish path is present.

`receipt_verifier.py` memverifikasi satu record room Technocore terhadap Ed25519 `did:key` yang dipin secara eksplisit. Tool ini read-only dan offline; tidak ada pemuatan private key, signing, maupun jalur network/write.

## Signed bytes / Byte yang ditandatangani

The signature covers the exact UTF-8 bytes below:

```text
<room>|<nonce>|<text>
```

The verifier does not trim or normalize `text`. A whitespace or Unicode change is a different payload and must fail. `seq` is checked for shape but is server metadata, not part of the signed payload.

## Receipt schema

```json
{
  "schema": "nanaz.technocore.signed-receipt.v1",
  "room": "technocore",
  "record": {
    "seq": 11217239,
    "from": "did:key:...",
    "nonce": 1790042529463,
    "text": "exact message text",
    "sig": "unpadded-base64url-ed25519-signature"
  }
}
```

Unknown or missing fields fail closed. The `from` field must equal the pinned DID before cryptographic verification runs.

## Usage

```bash
python3 receipt_verifier.py \
  evidence/fixtures/technocore-valid.json \
  --did did:key:z6MkgjQRmahVjPgCBdoHDPEoUwAMG2KisqjoNDMiH1B68Wcs
```

Success exits `0` and emits compact JSON with `"verified":true`. Any malformed input, DID mismatch, payload mutation, or invalid signature exits `1` and writes `receipt_invalid:...` to stderr.

Run all deterministic positive/negative checks:

```bash
python3 -m unittest tests.test_receipt_verifier -v
```

## Fixtures

The positive fixture is a public signed room record captured from the Technocore JSON read endpoint. Negative fixtures deterministically preserve one failure each:

- `technocore-invalid-text.json`: signed text changed;
- `technocore-invalid-signature.json`: signature changed;
- `technocore-wrong-signer.json`: valid record from another DID, rejected against the pinned DID.

No private key or wallet identifier is included.

## Claim boundary / Batas klaim

A passing result proves only that the pinned DID signed the exact `room|nonce|text` payload. It does **not** prove usefulness, independent `ATTEST`/`ACCEPT`, official eligibility, allocation, claimability, payment, or on-chain activity. Status resmi tetap **UNVERIFIED** sampai ada authoritative exact-DID receipt. Crypto is allergic to implied conclusions; this tool is too.
