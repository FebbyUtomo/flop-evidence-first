#!/usr/bin/env python3
"""Offline, read-only verifier for signed Technocore room receipts.

The verifier accepts public keys only through canonical Ed25519 did:key values.
It has no private-key loader, signing operation, or network/write path.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA = "nanaz.technocore.signed-receipt.v1"
MULTICODEC_ED25519 = b"\xed\x01"
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58_INDEX = {character: index for index, character in enumerate(BASE58)}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
NONCE_RE = re.compile(r"^[0-9]{1,19}$")
SIG_RE = re.compile(r"^[A-Za-z0-9_-]{86}$")
DID_RE = re.compile(r"^did:key:z6Mk[1-9A-HJ-NP-Za-km-z]{44}$")
TOP_KEYS = {"schema", "room", "record"}
RECORD_KEYS = {"seq", "from", "nonce", "text", "sig"}


class VerificationError(ValueError):
    """Receipt shape, identity pin, or signature verification failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def base58_decode(value: str) -> bytes:
    number = 0
    for character in value:
        try:
            number = number * 58 + BASE58_INDEX[character]
        except KeyError as exc:
            raise VerificationError("DID contains invalid base58btc") from exc
    decoded = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    zeroes = len(value) - len(value.lstrip("1"))
    return b"\x00" * zeroes + decoded


def public_key_from_did(did: str) -> Ed25519PublicKey:
    require(type(did) is str and DID_RE.fullmatch(did) is not None,
            "DID must be canonical Ed25519 did:key")
    decoded = base58_decode(did.removeprefix("did:key:z"))
    require(len(decoded) == 34 and decoded.startswith(MULTICODEC_ED25519),
            "DID must contain an Ed25519 public key")
    try:
        return Ed25519PublicKey.from_public_bytes(decoded[2:])
    except ValueError as exc:
        raise VerificationError("DID contains an invalid Ed25519 public key") from exc


def verify_receipt(receipt: Any, pinned_did: str) -> dict[str, Any]:
    """Validate one receipt and return public verification facts.

    Technocore signs the exact UTF-8 bytes ``room|nonce|text``. No text
    normalization is performed here: even a one-byte change must fail.
    """
    require(type(receipt) is dict, "receipt must be a JSON object")
    require(set(receipt) == TOP_KEYS, "receipt fields must match the schema exactly")
    require(receipt["schema"] == SCHEMA, "unsupported receipt schema")
    room = receipt["room"]
    require(type(room) is str and NAME_RE.fullmatch(room) is not None,
            "room has invalid shape")
    record = receipt["record"]
    require(type(record) is dict and set(record) == RECORD_KEYS,
            "record fields must match the schema exactly")
    seq = record["seq"]
    require(type(seq) is int and not isinstance(seq, bool) and seq > 0,
            "seq must be a positive integer")
    sender = record["from"]
    require(type(pinned_did) is str and sender == pinned_did,
            "record sender does not match pinned DID")
    public_key = public_key_from_did(pinned_did)
    nonce = record["nonce"]
    require((type(nonce) is int and not isinstance(nonce, bool)) or type(nonce) is str,
            "nonce must be an integer or digit string")
    nonce_text = str(nonce)
    require(NONCE_RE.fullmatch(nonce_text) is not None, "nonce has invalid shape")
    text = record["text"]
    require(type(text) is str and bool(text), "text must be a non-empty string")
    signature_value = record["sig"]
    require(type(signature_value) is str and SIG_RE.fullmatch(signature_value) is not None,
            "signature must be 86-character unpadded base64url")
    signature = cast(str, signature_value)
    try:
        raw_signature = base64.b64decode(signature + "==", altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise VerificationError("signature is not valid base64url") from exc
    require(len(raw_signature) == 64, "signature must decode to 64 bytes")
    payload = f"{room}|{nonce_text}|{text}".encode("utf-8")
    try:
        public_key.verify(raw_signature, payload)
    except InvalidSignature as exc:
        raise VerificationError("signature does not match pinned DID and exact payload") from exc
    return {
        "schema": SCHEMA,
        "verified": True,
        "room": room,
        "seq": seq,
        "from": sender,
        "signed_payload": "room|nonce|text",
        "claim_boundary": "authorship_and_integrity_only",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a signed Technocore receipt offline")
    parser.add_argument("receipt", type=Path, help="receipt JSON file")
    parser.add_argument("--did", required=True, help="exact pinned signer did:key")
    args = parser.parse_args(argv)
    try:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        result = verify_receipt(receipt, args.did)
    except (OSError, json.JSONDecodeError, VerificationError) as exc:
        print(f"receipt_invalid:{type(exc).__name__}:{exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
