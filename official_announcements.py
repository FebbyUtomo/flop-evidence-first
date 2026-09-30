#!/usr/bin/env python3
"""Offline validator for pinned official FLOP announcement evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse


SCHEMA = "nanaz.flop-official-announcements.v1"
POST_ID_RE = re.compile(r"^[0-9]{19}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_LANES = {"GPU_WORK", "AGENT_WORK"}
DIRECTIONAL_STATE = "DIRECTIONAL_NOT_ELIGIBILITY_CRITERION"
PINNED_POST_ID = "2105090680314069401"
PINNED_ACCOUNT = "flop_labs"
PINNED_PUBLISHED_AT = "2026-09-30T00:21:43Z"
PINNED_QUOTE = "run GPUs or put your agent to work, and that's how you earn $ FLOP."
PINNED_CLAIM_BOUNDARY = (
    "This record preserves one official policy-direction announcement. It does not establish "
    "identity-specific eligibility, accepted contribution, allocation, claimability, or payment."
)
PINNED_AUTHORED_TEXT_RAW = (
    "@CryptoHayes on CryptoWendyO: most crypto projects use their token wrong, and that includes most of "
    "the ones he advises.\n\nBitcoin got it right. The only way in was to do the work, or buy from someone "
    "who did. Flop Network runs on the same rule: run GPUs or put your agent to work, and that's how you "
    "earn $ FLOP.\n\nFrom 19:31 https://t.co/mYx4G8My5A"
)
PINNED_AUTHORED_TEXT_EXPANDED = (
    "@CryptoHayes on CryptoWendyO: most crypto projects use their token wrong, and that includes most of "
    "the ones he advises.\n\nBitcoin got it right. The only way in was to do the work, or buy from someone "
    "who did. Flop Network runs on the same rule: run GPUs or put your agent to work, and that's how you "
    "earn $ FLOP.\n\nFrom 19:31 https://www.youtube.com/watch?v=dpmyx_rbSFY&t=1171s"
)
PINNED_ORIGINAL_LINK = "https://t.co/mYx4G8My5A"
PINNED_EXPANDED_LINK = "https://www.youtube.com/watch?v=dpmyx_rbSFY&t=1171s"
PINNED_DISPLAY_LINK = "youtube.com/watch?v=dpmyx_…"
PINNED_SNAPSHOT_SHA256 = "35269b582839a1ef78efb03401d51c499a924556ea3501c804ee765c6841ce55"


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def strict_object(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    require(type(value) is dict, f"{field} must be an object")
    require(set(value) == keys, f"{field} keys mismatch")
    return cast(dict[str, Any], value)


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict(text: str) -> Any:
    return json.loads(text, object_pairs_hook=reject_duplicate_keys)


def canonical_snapshot(snapshot: Any) -> bytes:
    return json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def validate(data: Any) -> dict[str, Any]:
    manifest = strict_object(
        data,
        {
            "schema",
            "captured_at",
            "eligibility_status",
            "allocation_status",
            "claim_boundary",
            "announcements",
        },
        "manifest",
    )
    require(manifest["schema"] == SCHEMA, "unsupported schema")
    require(manifest["captured_at"] == "2026-09-30", "unexpected capture date")
    require(manifest["eligibility_status"] == "UNVERIFIED", "eligibility must remain UNVERIFIED")
    require(manifest["allocation_status"] == "UNVERIFIED", "allocation must remain UNVERIFIED")
    require(manifest["claim_boundary"] == PINNED_CLAIM_BOUNDARY, "claim boundary mismatch")

    announcements = manifest["announcements"]
    require(type(announcements) is list and len(announcements) == 1, "exactly one pinned announcement required")
    item = strict_object(
        announcements[0],
        {
            "id",
            "source",
            "source_snapshot",
            "source_snapshot_sha256",
            "exact_quote",
            "work_lanes",
            "deadline",
            "linked_artifact",
            "exact_identity_receipt",
            "state",
        },
        "announcements[0]",
    )
    require(item["id"] == "gpu_agent_work_direction", "unexpected announcement id")

    source = strict_object(
        item["source"],
        {"platform", "account", "post_id", "published_at", "url"},
        "announcements[0].source",
    )
    require(source["platform"] == "x", "source platform must be x")
    require(source["account"] == PINNED_ACCOUNT, "source account mismatch")
    require(type(source["post_id"]) is str and POST_ID_RE.fullmatch(source["post_id"]) is not None,
            "post_id is malformed")
    require(source["post_id"] == PINNED_POST_ID, "post_id is not the pinned announcement")
    require(type(source["published_at"]) is str and TIMESTAMP_RE.fullmatch(source["published_at"]) is not None,
            "published_at is malformed")
    require(source["published_at"] == PINNED_PUBLISHED_AT, "published_at mismatch")
    expected_url = f"https://x.com/{PINNED_ACCOUNT}/status/{PINNED_POST_ID}"
    require(source["url"] == expected_url, "source URL mismatch")
    parsed = urlparse(source["url"])
    require(parsed.scheme == "https" and parsed.hostname == "x.com" and not parsed.username,
            "source URL must use the official HTTPS origin")

    snapshot = strict_object(
        item["source_snapshot"],
        {"authored_text_raw", "authored_text_expanded", "links"},
        "announcements[0].source_snapshot",
    )
    require(snapshot["authored_text_raw"] == PINNED_AUTHORED_TEXT_RAW, "raw authored text mismatch")
    require(snapshot["authored_text_expanded"] == PINNED_AUTHORED_TEXT_EXPANDED,
            "expanded authored text mismatch")
    links = snapshot["links"]
    require(type(links) is list and len(links) == 1, "exactly one source link required")
    link = strict_object(links[0], {"original", "expanded", "display"},
                         "announcements[0].source_snapshot.links[0]")
    require(link["original"] == PINNED_ORIGINAL_LINK, "original source link mismatch")
    require(link["expanded"] == PINNED_EXPANDED_LINK, "expanded source link mismatch")
    require(link["display"] == PINNED_DISPLAY_LINK, "display source link mismatch")
    digest = item["source_snapshot_sha256"]
    require(type(digest) is str and SHA256_RE.fullmatch(digest) is not None,
            "source_snapshot_sha256 is malformed")
    calculated_digest = hashlib.sha256(canonical_snapshot(snapshot)).hexdigest()
    require(digest == calculated_digest, "source snapshot hash does not match content")
    require(digest == PINNED_SNAPSHOT_SHA256, "source snapshot hash mismatch")
    require(item["exact_quote"] == PINNED_QUOTE, "exact quote mismatch")
    require(PINNED_QUOTE in snapshot["authored_text_raw"], "exact quote is not in raw authored text")
    require(PINNED_QUOTE in snapshot["authored_text_expanded"],
            "exact quote is not in expanded authored text")

    lanes = item["work_lanes"]
    require(type(lanes) is list and len(lanes) == 2, "exactly two work lanes required")
    require(all(type(lane) is str for lane in lanes), "work lane must be a string")
    require(set(lanes) == ALLOWED_LANES, "work lanes must be exact GPU_WORK and AGENT_WORK lanes")
    require(item["deadline"] is None, "announcement does not publish a deadline")
    require(item["linked_artifact"] is None, "announcement does not link an executable artifact")
    require(item["exact_identity_receipt"] is None, "announcement has no exact-identity receipt")
    require(item["state"] == DIRECTIONAL_STATE,
            "directional announcement cannot be promoted to eligibility")

    return {
        "schema": SCHEMA,
        "announcements": 1,
        "work_lanes": sorted(ALLOWED_LANES),
        "state": DIRECTIONAL_STATE,
        "eligibility_status": "UNVERIFIED",
        "allocation_status": "UNVERIFIED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path,
                        default=Path(__file__).resolve().parent / "evidence" / "official-announcements.json")
    args = parser.parse_args(argv)
    try:
        data = loads_strict(args.manifest.read_text(encoding="utf-8"))
        result = validate(data)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"official_announcements_invalid:{type(exc).__name__}:{exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
