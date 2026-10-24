#!/usr/bin/env python3
"""Offline validator for the curated FLOP contribution registry."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "evidence" / "contributions.json"
ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
ALLOWED_STATUS = {"UNVERIFIED", "VERIFIED"}
REPOSITORY_URL = "https://github.com/FebbyUtomo/flop-evidence-first"
RECEIPT_KEYS = {
    "snapshot_commit", "snapshot_url", "receipt_path", "receipt_sha256", "signature_path",
    "signature_sha256", "public_key_path", "public_key_sha256", "transcript_path",
    "transcript_sha256", "artifact_sha256", "source_commit", "contribution_id",
    "mapping_path", "mapping_sha256",
}
EXPECTED_EXTERNAL_RECEIPTS = {
    ("roadmap_integrity_validator", "ATTEST"): {
        "actor_did": "did:key:z6MkuzkFDAwgSXgSVhxruVD4DGzuxCieeXonpsgCApd9o6Ms",
        "evidence_url": (
            "https://github.com/FebbyUtomo/flop-evidence-first/issues/1"
            "#issuecomment-6387074008"
        ),
        "snapshot_commit": "6d931570047ba065a83702083efd08d615da9686",
        "snapshot_url": (
            "https://github.com/putrikeme/flop-evidence-first/tree/"
            "6d931570047ba065a83702083efd08d615da9686/reviews/f471436"
        ),
        "source_commit": "f47143668521ede1aee7dc3c37746fb00d9eee24",
        "reviewer_login": "putrikeme",
        "reviewer_id": 107520232,
        "comment_id": 6387074008,
    },
}


class ValidationError(ValueError):
    """The registry failed a structural or evidence-binding check."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def strict_object(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    require(type(value) is dict, f"{field} must be an object")
    require(set(value) == keys, f"{field} keys mismatch")
    return value


def artifact_path(root: Path, relative: Any) -> Path:
    require(type(relative) is str and bool(relative), "result.path must be a string")
    pure = PurePosixPath(relative)
    require(not pure.is_absolute() and relative == pure.as_posix(),
            f"result.path must be repository-relative: {relative}")
    require("." not in pure.parts and ".." not in pure.parts,
            f"result.path must be normalized: {relative}")
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValidationError(f"result.path escapes repository: {relative}") from exc
    require(path.is_file(), f"result artifact missing: {relative}")
    return path


def base58btc(raw: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = int.from_bytes(raw, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = alphabet[remainder] + encoded
    leading = len(raw) - len(raw.lstrip(b"\0"))
    return alphabet[0] * leading + encoded


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_verified_receipt(
    receipt_raw: Any,
    *,
    state: dict[str, Any],
    field: str,
    root: Path,
    contribution_id: str,
    result_path: str,
    result_sha256: str,
    verdict: str,
) -> None:
    receipt = strict_object(receipt_raw, RECEIPT_KEYS, f"{field}.receipt")
    expected = EXPECTED_EXTERNAL_RECEIPTS.get((contribution_id, verdict))
    if expected is None:
        raise ValidationError(f"{field}.receipt is not an approved external receipt")
    require(state["actor_did"] == expected["actor_did"],
            f"{field}.receipt unexpected actor DID")
    require(state["evidence_url"] == expected["evidence_url"],
            f"{field}.receipt unexpected evidence URL")
    require(receipt["contribution_id"] == contribution_id,
            f"{field}.receipt contribution mismatch")
    require(receipt["snapshot_commit"] == expected["snapshot_commit"],
            f"{field}.receipt snapshot commit mismatch")
    require(receipt["snapshot_url"] == expected["snapshot_url"],
            f"{field}.receipt snapshot URL mismatch")
    require(receipt["source_commit"] == expected["source_commit"],
            f"{field}.receipt unexpected source commit")
    for key in ("snapshot_commit", "source_commit"):
        require(type(receipt[key]) is str and COMMIT_RE.fullmatch(receipt[key]) is not None,
                f"{field}.receipt.{key} is invalid")
    for key in (
        "receipt_sha256", "signature_sha256", "public_key_sha256",
        "transcript_sha256", "artifact_sha256", "mapping_sha256",
    ):
        require(type(receipt[key]) is str and SHA256_RE.fullmatch(receipt[key]) is not None,
                f"{field}.receipt.{key} is invalid")

    receipt_path = artifact_path(root, receipt["receipt_path"])
    signature_path = artifact_path(root, receipt["signature_path"])
    public_key_path = artifact_path(root, receipt["public_key_path"])
    transcript_path = artifact_path(root, receipt["transcript_path"])
    mapping_path = artifact_path(root, receipt["mapping_path"])
    require(digest(receipt_path) == receipt["receipt_sha256"],
            f"{field}.receipt receipt hash mismatch")
    require(digest(signature_path) == receipt["signature_sha256"],
            f"{field}.receipt signature hash mismatch")
    require(digest(public_key_path) == receipt["public_key_sha256"],
            f"{field}.receipt public key hash mismatch")
    require(digest(transcript_path) == receipt["transcript_sha256"],
            f"{field}.receipt transcript hash mismatch")
    require(digest(mapping_path) == receipt["mapping_sha256"],
            f"{field}.receipt mapping hash mismatch")

    try:
        signed = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{field}.receipt signed receipt is invalid") from exc
    require(type(signed) is dict, f"{field}.receipt signed receipt must be an object")
    require(signed.get("verdict") == verdict, f"{field}.receipt verdict mismatch")
    require(signed.get("reviewer", {}).get("actor_did") == state["actor_did"],
            f"{field}.receipt actor DID mismatch")
    require(signed.get("source", {}).get("repository") == REPOSITORY_URL,
            f"{field}.receipt repository mismatch")
    require(signed.get("source", {}).get("commit") == receipt["source_commit"],
            f"{field}.receipt source commit mismatch")
    require(signed.get("artifact", {}).get("sha256") == receipt["artifact_sha256"],
            f"{field}.receipt artifact hash mismatch")
    require(signed.get("result", {}).get("transcript_sha256") == receipt["transcript_sha256"],
            f"{field}.receipt transcript binding mismatch")
    require(signed.get("result", {}).get("core_exit_code") == 0 and
            signed.get("result", {}).get("core_verdict") == "PASS",
            f"{field}.receipt core result is not PASS")
    require(signed.get("reviewer", {}).get("name") == expected["reviewer_login"],
            f"{field}.receipt reviewer login mismatch")

    try:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{field}.receipt mapping snapshot is invalid") from exc
    require(type(mapping) is dict, f"{field}.receipt mapping must be an object")
    require(mapping.get("id") == expected["comment_id"],
            f"{field}.receipt mapping comment ID mismatch")
    require(mapping.get("html_url") == state["evidence_url"],
            f"{field}.receipt mapping URL mismatch")
    require(mapping.get("user", {}).get("login") == expected["reviewer_login"] and
            mapping.get("user", {}).get("id") == expected["reviewer_id"],
            f"{field}.receipt mapping reviewer mismatch")
    require(mapping.get("created_at") == mapping.get("updated_at"),
            f"{field}.receipt mapping snapshot was edited")
    require(mapping.get("performed_via_github_app", {}).get("slug") == "hark",
            f"{field}.receipt mapping app mismatch")
    mapping_body = mapping.get("body")
    require(type(mapping_body) is str and
            f"Attested contribution_id: {contribution_id}" in mapping_body and
            receipt["snapshot_commit"] in mapping_body and
            "I personally control the reviewer DID/signing key" in mapping_body and
            "The repository owner does not control this account" in mapping_body,
            f"{field}.receipt mapping statement mismatch")

    try:
        loaded_key = serialization.load_pem_public_key(public_key_path.read_bytes())
        if not isinstance(loaded_key, Ed25519PublicKey):
            raise ValidationError(f"{field}.receipt public key is not Ed25519")
        public_key = loaded_key
        public_key.verify(signature_path.read_bytes(), receipt_path.read_bytes())
    except (OSError, ValueError, TypeError, InvalidSignature) as exc:
        raise ValidationError(f"{field}.receipt signature verification failed") from exc
    raw_public = public_key.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    derived_did = "did:key:z" + base58btc(bytes.fromhex("ed01") + raw_public)
    require(derived_did == state["actor_did"], f"{field}.receipt DID derivation mismatch")

    try:
        reviewed_bytes = subprocess.run(
            ["git", "-C", str(root), "show", f"{receipt['source_commit']}:{result_path}"],
            check=True, capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValidationError(f"{field}.receipt reviewed artifact is unavailable") from exc
    require(hashlib.sha256(reviewed_bytes).hexdigest() == result_sha256,
            f"{field}.receipt reviewed artifact hash mismatch")


def validate_external_state(
    raw: Any,
    field: str,
    primary_did: str,
    root: Path,
    contribution_id: str,
    result_path: str,
    result_sha256: str,
    verdict: str,
) -> str:
    require(type(raw) is dict, f"{field} must be an object")
    status = raw.get("status")
    expected_keys = {"status", "actor_did", "evidence_url"}
    if status == "VERIFIED":
        expected_keys.add("receipt")
    state = strict_object(raw, expected_keys, field)
    status = state["status"]
    require(status in ALLOWED_STATUS, f"{field}.status is invalid")
    if status == "UNVERIFIED":
        require(state["actor_did"] is None and state["evidence_url"] is None,
                f"{field} UNVERIFIED cannot carry pretend evidence")
    else:
        actor = state["actor_did"]
        evidence_url = state["evidence_url"]
        require(type(actor) is str and actor.startswith("did:key:") and actor != primary_did,
                f"{field} VERIFIED requires an independent DID")
        require(type(evidence_url) is str and evidence_url.startswith("https://"),
                f"{field} VERIFIED requires HTTPS evidence")
        validate_verified_receipt(
            state["receipt"], state=state, field=field, root=root,
            contribution_id=contribution_id, result_path=result_path,
            result_sha256=result_sha256, verdict=verdict,
        )
    return status


def validate(data: Any, root: Path) -> dict[str, Any]:
    manifest = strict_object(
        data,
        {"schema", "repository", "primary_did", "allocation_status", "contributions"},
        "manifest",
    )
    require(manifest["schema"] == "nanaz.flop-contributions.v1", "unsupported schema")
    require(manifest["repository"] == REPOSITORY_URL, "unexpected repository")
    primary_did = manifest["primary_did"]
    require(type(primary_did) is str and primary_did.startswith("did:key:"), "invalid primary_did")
    require(manifest["allocation_status"] == "UNVERIFIED",
            "allocation_status must remain UNVERIFIED")

    contributions = manifest["contributions"]
    require(type(contributions) is list and 10 <= len(contributions) <= 20,
            "registry must curate 10-20 contributions")
    ids: set[str] = set()
    paths: set[str] = set()
    hashes: set[str] = set()
    commits: set[str] = set()
    attest_counts = {status: 0 for status in sorted(ALLOWED_STATUS)}
    accept_counts = {status: 0 for status in sorted(ALLOWED_STATUS)}

    for index, raw in enumerate(contributions):
        field = f"contributions[{index}]"
        item = strict_object(
            raw, {"id", "title", "category", "result", "attest", "accept"}, field
        )
        ident = item["id"]
        require(type(ident) is str and ID_RE.fullmatch(ident) is not None,
                f"{field}.id is invalid")
        require(ident not in ids, f"duplicate contribution id: {ident}")
        ids.add(ident)
        require(type(item["title"]) is str and 5 <= len(item["title"]) <= 120,
                f"{field}.title is invalid")
        require(item["category"] in {"evidence", "tooling", "testnet", "readiness", "education"},
                f"{field}.category is invalid")

        result = strict_object(item["result"], {"path", "sha256", "commit", "url"},
                               f"{field}.result")
        path = artifact_path(root, result["path"])
        require(result["path"] not in paths, f"duplicate result path: {result['path']}")
        paths.add(result["path"])
        digest = result["sha256"]
        require(type(digest) is str and SHA256_RE.fullmatch(digest) is not None,
                f"{field}.result.sha256 is invalid")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                f"result hash mismatch: {result['path']}")
        require(digest not in hashes, f"duplicate result content: {result['path']}")
        hashes.add(digest)
        commit = result["commit"]
        require(type(commit) is str and COMMIT_RE.fullmatch(commit) is not None,
                f"{field}.result.commit is invalid")
        commits.add(commit)
        expected_url = f"{REPOSITORY_URL}/blob/{commit}/{result['path']}"
        require(result["url"] == expected_url, f"result URL is not commit-pinned: {ident}")

        attest = validate_external_state(
            item["attest"], f"{field}.attest", primary_did, root, ident,
            result["path"], digest, "ATTEST",
        )
        accept = validate_external_state(
            item["accept"], f"{field}.accept", primary_did, root, ident,
            result["path"], digest, "ACCEPT",
        )
        attest_counts[attest] += 1
        accept_counts[accept] += 1

    return {
        "schema": manifest["schema"],
        "contributions": len(contributions),
        "result_hashes_verified": len(hashes),
        "unique_commits": len(commits),
        "attest": attest_counts,
        "accept": accept_counts,
        "allocation_status": manifest["allocation_status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = validate(data, args.root.resolve())
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"registry_invalid:{type(exc).__name__}:{exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
