#!/usr/bin/env python3
"""Offline verifier and exact-DID lookup for the official Sonnet-2 result package.

The module reads a pinned local package only. It has no network, private-key,
signing, claiming, transaction, or file-write path.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

SCHEMA = "nanaz.sonnet-2-source.v1"
OFFICIAL_COMMIT = "195647a4d85733ecd4862d67dc7bf7a62e673c58"
OFFICIAL_POST_ID = "2102578439643693562"
OFFICIAL_POST_TIMESTAMP = "2026-09-23T01:58:58Z"
REFEREE_DID = "did:key:z6MkowHQwsx9xr84WbWN3YCnKutyBnBXkT1ChKY4uEAAMzte"
DID_RE = re.compile(r"^did:key:z6Mk[1-9A-HJ-NP-Za-km-z]{44}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
AVAILABLE_FILES = {
    "manifest.json", "allocations.csv", "payouts.json",
    "settle-receipt.json", "standings.json",
}
CSV_COLUMNS = [
    "did", "role", "entry", "amount_flop", "basis", "evidence",
    "record_room", "request_id", "intake_seq", "written_at",
]
MANIFEST_KEYS = {
    "contest_id", "winner", "finalists", "authorization", "pools_flop",
    "allocated_flop", "remainder_with_flop_labs", "recipients", "share_flop",
    "signed_records_in_d-sonnet-2-results", "sha256", "claims",
}
SOURCE_KEYS = {
    "schema", "official_commit", "official_tree_url", "announcement",
    "package_files", "unavailable_manifest_artifacts", "claim_boundary",
}


class VerificationError(ValueError):
    """A source pin, result invariant, hash, or exact-DID check failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def strict_int(value: Any, field: str) -> int:
    require(type(value) is int, f"{field} must be an integer")
    return cast(int, value)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot read valid JSON: {path.name}") from exc


def validate_source_record(data: Any, package_dir: Path) -> dict[str, Any]:
    require(type(data) is dict and set(data) == SOURCE_KEYS, "source record keys mismatch")
    source = cast(dict[str, Any], data)
    require(source["schema"] == SCHEMA, "unsupported source record schema")
    require(source["official_commit"] == OFFICIAL_COMMIT, "official commit pin mismatch")
    require(
        source["official_tree_url"] ==
        f"https://github.com/flop-labs/technocore-sonnet-challenge/tree/{OFFICIAL_COMMIT}/results/sonnet-2",
        "official tree URL must be commit-pinned",
    )
    raw_announcement = source["announcement"]
    require(type(raw_announcement) is dict and set(raw_announcement) == {"post_id", "timestamp", "url", "requirement"},
            "announcement keys mismatch")
    announcement = cast(dict[str, Any], raw_announcement)
    require(announcement["post_id"] == OFFICIAL_POST_ID, "announcement post ID mismatch")
    require(announcement["timestamp"] == OFFICIAL_POST_TIMESTAMP, "announcement timestamp mismatch")
    require(announcement["url"] == f"https://x.com/flop_labs/status/{OFFICIAL_POST_ID}",
            "announcement URL mismatch")
    require(type(announcement["requirement"]) is str and "claim process opens once mainnet is live" in announcement["requirement"],
            "announcement requirement is not preserved")

    raw_files = source["package_files"]
    require(type(raw_files) is dict and set(raw_files) == AVAILABLE_FILES, "source package file set mismatch")
    files = cast(dict[str, Any], raw_files)
    for name, expected in files.items():
        require(type(expected) is str and SHA256_RE.fullmatch(expected) is not None,
                f"invalid source hash: {name}")
        path = package_dir / name
        require(path.is_file(), f"missing package file: {name}")
        require(digest(path) == expected, f"source hash mismatch: {name}")
    unavailable = source["unavailable_manifest_artifacts"]
    require(unavailable == ["allocations.json", "referee.sqlite (closed ledger)"],
            "unavailable artifact disclosure mismatch")
    boundary = source["claim_boundary"]
    require(type(boundary) is str, "claim boundary must be text")
    boundary_lower = boundary.lower()
    require(all(term in boundary_lower for term in ("claimable", "claimed", "paid", "unverified")),
            "claim boundary must preserve lifecycle states")
    return source


def validate_manifest(data: Any) -> dict[str, Any]:
    require(type(data) is dict and set(data) == MANIFEST_KEYS, "manifest keys mismatch")
    manifest = cast(dict[str, Any], data)
    require(manifest["contest_id"] == "sonnet-2", "contest ID mismatch")
    require(manifest["winner"] == "maragung-flop", "winner mismatch")
    require(manifest["finalists"] == ["quire", "pom-team", "maragung-flop"], "finalists mismatch")
    require(str(OFFICIAL_POST_ID) in manifest["authorization"], "authorization post is not pinned")
    require(manifest["pools_flop"] == {"poem_prize": 50000, "voter_pool": 50000}, "pool totals mismatch")
    require(strict_int(manifest["allocated_flop"], "allocated_flop") == 97964, "allocated total mismatch")
    require(strict_int(manifest["remainder_with_flop_labs"], "remainder") == 2036, "remainder mismatch")
    require(manifest["recipients"] == {"contributors": 4, "voters": 6852, "total": 6856},
            "recipient counts mismatch")
    require(manifest["share_flop"] == {"contributor": 12500, "voter": 7}, "share amounts mismatch")
    require(manifest["signed_records_in_d-sonnet-2-results"]["settle-1"] == [45497, 45498],
            "settlement record sequence mismatch")
    require("open when mainnet is live" in manifest["claims"] and "sonnet.claim.v1" in manifest["claims"],
            "claim condition mismatch")
    hashes = manifest["sha256"]
    require(type(hashes) is dict, "manifest hashes must be an object")
    return manifest


def manifest_file_hashes(manifest: dict[str, Any]) -> dict[str, str]:
    hashes = manifest["sha256"]
    return {
        "payouts.json": hashes["payouts.json (= payments_sha256 in the settle receipt)"],
        "allocations.csv": hashes["allocations.csv"],
        "standings.json": hashes["standings.json"],
        "settle-receipt.json": hashes["settle-receipt.json"],
    }


def validate_payouts(data: Any) -> dict[str, int]:
    require(type(data) is dict and len(data) == 6856, "payout map must contain 6,856 DIDs")
    payouts = cast(dict[str, Any], data)
    for did, amount in payouts.items():
        require(DID_RE.fullmatch(did) is not None, "payout contains malformed DID")
        require(type(amount) is int and amount in {7, 12500}, "payout contains invalid amount")
    require(sum(cast(dict[str, int], payouts).values()) == 97964, "payout total mismatch")
    require(sum(value == 12500 for value in payouts.values()) == 4, "contributor payout count mismatch")
    return cast(dict[str, int], payouts)


def validate_allocations(path: Path, payouts: dict[str, int]) -> dict[str, dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            require(reader.fieldnames == CSV_COLUMNS, "allocation CSV columns mismatch")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise VerificationError("cannot read allocation CSV") from exc
    require(len(rows) == 6856, "allocation CSV row count mismatch")
    allocations: dict[str, dict[str, str]] = {}
    role_counts = {"contributor": 0, "voter": 0}
    for row in rows:
        did = row["did"]
        require(DID_RE.fullmatch(did) is not None and did not in allocations,
                "allocation CSV contains malformed or duplicate DID")
        role = row["role"]
        require(role in role_counts, "allocation CSV contains invalid role")
        role_counts[role] += 1
        require(row["amount_flop"].isdigit(), "allocation amount must be digits")
        amount = int(row["amount_flop"])
        expected = 12500 if role == "contributor" else 7
        require(amount == expected and payouts.get(did) == amount,
                "allocation CSV disagrees with payout map")
        require(row["entry"] == "maragung-flop", "allocation entry must be the winner")
        allocations[did] = row
    require(role_counts == {"contributor": 4, "voter": 6852}, "allocation role counts mismatch")
    require(set(allocations) == set(payouts), "allocation and payout DID sets mismatch")
    return allocations


def verify_package(package_dir: Path, source_record: Any, did: str) -> dict[str, Any]:
    require(type(did) is str and DID_RE.fullmatch(did) is not None, "lookup DID must be canonical Ed25519 did:key")
    validate_source_record(source_record, package_dir)
    manifest = validate_manifest(load_json(package_dir / "manifest.json"))
    for name, expected in manifest_file_hashes(manifest).items():
        require(type(expected) is str and SHA256_RE.fullmatch(expected) is not None,
                f"manifest hash invalid: {name}")
        require(digest(package_dir / name) == expected, f"manifest hash mismatch: {name}")

    payouts = validate_payouts(load_json(package_dir / "payouts.json"))
    allocations = validate_allocations(package_dir / "allocations.csv", payouts)
    settlement = load_json(package_dir / "settle-receipt.json")
    require(type(settlement) is dict and set(settlement) == {
        "contest_id", "intake_seq", "payments", "reason", "received_at",
        "request_id", "sender_did", "status", "total", "type",
    }, "settlement receipt keys mismatch")
    require(settlement["contest_id"] == "sonnet-2" and settlement["request_id"] == "settle-1",
            "settlement identity mismatch")
    require(settlement["sender_did"] == REFEREE_DID and settlement["status"] == "accepted",
            "settlement referee/status mismatch")
    require(settlement["payments"] == payouts and settlement["total"] == 97964,
            "settlement payments mismatch")
    standings = load_json(package_dir / "standings.json")
    require(type(standings) is dict and standings.get("finalists") == manifest["finalists"],
            "standings finalists mismatch")
    require(standings.get("totals", {}).get("maragung-flop") == 6852,
            "winning vote total mismatch")

    row = allocations.get(did)
    allocation = {"status": "NOT_LISTED"}
    if row is not None:
        allocation = {
            "status": "LISTED",
            "amount_flop": int(row["amount_flop"]),
            "role": row["role"],
            "entry": row["entry"],
        }
    return {
        "schema": SCHEMA,
        "package_verified": True,
        "official_commit": OFFICIAL_COMMIT,
        "announcement_post_id": OFFICIAL_POST_ID,
        "recipients_verified": len(payouts),
        "allocated_total_verified": sum(payouts.values()),
        "allocation": allocation,
        "claimable": {"status": "UNVERIFIED", "reason": "mainnet_and_claim_open_not_proven_by_package"},
        "claimed": {"status": "UNVERIFIED", "reason": "no_exact_did_claim_receipt"},
        "paid": {"status": "UNVERIFIED", "reason": "allocation_is_not_payment"},
        "coverage_gap": ["allocations.json", "referee.sqlite (closed ledger)"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="local official Sonnet-2 package directory")
    parser.add_argument("--source-record", required=True, type=Path, help="pinned source metadata JSON")
    parser.add_argument("--did", required=True, help="exact DID to look up (never printed)")
    args = parser.parse_args(argv)
    try:
        source = load_json(args.source_record)
        result = verify_package(args.package, source, args.did)
    except VerificationError as exc:
        print(f"sonnet_result_invalid:{exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
