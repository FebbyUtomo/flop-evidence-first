#!/usr/bin/env python3
"""Offline validator for the curated FLOP contribution registry."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "evidence" / "contributions.json"
ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
ALLOWED_STATUS = {"UNVERIFIED", "VERIFIED"}
REPOSITORY_URL = "https://github.com/FebbyUtomo/flop-evidence-first"


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


def validate_external_state(raw: Any, field: str, primary_did: str) -> str:
    state = strict_object(raw, {"status", "actor_did", "evidence_url"}, field)
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

        attest = validate_external_state(item["attest"], f"{field}.attest", primary_did)
        accept = validate_external_state(item["accept"], f"{field}.accept", primary_did)
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
