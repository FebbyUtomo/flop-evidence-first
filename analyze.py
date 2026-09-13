#!/usr/bin/env python3
"""Build aggregate, public-safe evidence for the NAK FLOP experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

MAIN_DID = "did:key:z6MkuqDkBuKQKSDuPH5F4qms2GPNfQeWLswuqPghrxdpcRRm"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
MULTICODEC = b"\xed\x01"


def _base58(raw: bytes) -> str:
    number = int.from_bytes(raw, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = B58[remainder] + encoded
    leading = len(raw) - len(raw.lstrip(b"\0"))
    return ("1" * leading) + encoded


def did_from_key(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes_raw()
    return "did:key:z" + _base58(MULTICODEC + raw)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    completed = state.get("completed") or []
    pending = state.get("claimed") or {}
    types = Counter(str(item.get("type") or "unknown") for item in completed)
    valid = []
    for item in completed:
        if not isinstance(item, dict):
            continue
        job_id = str(item.get("job_id") or "")
        seq = item.get("result_seq")
        timestamp = item.get("ts")
        try:
            datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        if re.fullmatch(r"k[a-zA-Z0-9_-]{1,64}", job_id) and isinstance(seq, int) and seq > 0:
            valid.append(item)
    timestamps = sorted(str(item["ts"]) for item in valid)
    return {
        "last_seq": int(state.get("last_seq") or 0),
        "pending_claims": len(pending),
        "deliveries": len(completed),
        "delivery_records": len(completed),
        "valid_delivery_records": len(valid),
        "unique_job_ids": len({item["job_id"] for item in valid}),
        "unique_result_sequences": len({item["result_seq"] for item in valid}),
        "types": dict(sorted(types.items())),
        "first_delivery_at": timestamps[0] if timestamps else None,
        "last_delivery_at": timestamps[-1] if timestamps else None,
    }


def count_json_files(root: Path) -> int:
    return sum(1 for path in root.iterdir() if path.is_file() and path.suffix == ".json")


def count_post_records(path: Path) -> int:
    data = json.loads(path.read_text())
    if isinstance(data, (dict, list)):
        return len(data)
    raise ValueError("post-record file must contain an object or array")


def audit_identity_records(accounts: Path, post_records: dict[str, Any]) -> dict[str, Any]:
    total = valid = derived = matched = invalid = 0
    seen_dids: set[str] = set()
    seen_names: set[str] = set()
    commitment_rows: list[str] = []
    for path in sorted(accounts.glob("*.json")):
        if path.name == "INDEX.json":
            continue
        total += 1
        try:
            item = json.loads(path.read_text())
            nickname = str(item["nickname"])
            did = str(item["did"])
            seed = str(item["seed"])
            if path.stem != nickname or not re.fullmatch(r"[0-9a-f]{64}", seed):
                raise ValueError("invalid local identity schema")
            if nickname in seen_names or did in seen_dids:
                raise ValueError("duplicate identity")
            key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed))
            if did_from_key(key) != did:
                raise ValueError("DID derivation mismatch")
            derived += 1
            nonce = post_records.get(f"{nickname}:lobby")
            if not isinstance(nonce, int) or nonce <= 0:
                raise ValueError("missing lobby post record")
            matched += 1
            seen_names.add(nickname)
            seen_dids.add(did)
            valid += 1
            commitment_rows.append(f"{did}|{nonce}")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            invalid += 1
    commitment = hashlib.sha256("\n".join(sorted(commitment_rows)).encode()).hexdigest()
    return {
        "identity_files": total,
        "valid_identity_records": valid,
        "unique_dids": len(seen_dids),
        "did_derivation_matches": derived,
        "matched_lobby_post_records": matched,
        "invalid_records": invalid,
        "public_did_nonce_commitment_sha256": commitment,
    }


def build_public_summary(
    state_summary: dict[str, Any],
    identity_count: int,
    campaign_post_records: int,
    *,
    state_sha256: str | None = None,
    campaign_log_sha256: str | None = None,
    identity_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "nanaz.flop.evidence.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "declared_publication_did": MAIN_DID,
        "campaign": {
            "generated_identities": identity_count,
            "posted_identity_records": campaign_post_records,
            "local_integrity_audit": identity_audit,
        },
        "kibble": state_summary,
        "evidence_hashes": {
            "kibble_state_sha256": state_sha256,
            "campaign_log_sha256": campaign_log_sha256,
        },
        "claim_boundaries": {
            "delivery_records_are_local_state_only": True,
            "delivery_sender_did_not_present_in_local_snapshot": True,
            "deliveries_are_not_attestations": True,
            "deliveries_are_not_acceptances": True,
            "no_official_flop_allocation_verified": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--accounts", type=Path, required=True)
    parser.add_argument("--post-records", type=Path, required=True)
    parser.add_argument("--campaign-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    state = json.loads(args.state.read_text())
    post_records = json.loads(args.post_records.read_text())
    if not isinstance(post_records, dict):
        raise ValueError("post-record file must contain an object")
    identity_audit = audit_identity_records(args.accounts, post_records)
    summary = build_public_summary(
        summarize_state(state),
        count_json_files(args.accounts),
        len(post_records),
        state_sha256=sha256_file(args.state),
        campaign_log_sha256=sha256_file(args.campaign_log),
        identity_audit=identity_audit,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "deliveries": summary["kibble"]["deliveries"],
        "identities": summary["campaign"]["generated_identities"],
        "post_records": summary["campaign"]["posted_identity_records"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
