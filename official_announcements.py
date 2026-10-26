#!/usr/bin/env python3
"""Offline validator for pinned official FLOP announcement evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse


SCHEMA = "nanaz.flop-official-announcements.v3"
POST_ID_RE = re.compile(r"^[0-9]{19}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_LANES = {"GPU_WORK", "AGENT_WORK"}
MEDIA_DIR = Path(__file__).resolve().parent / "evidence" / "media"
DIRECTIONAL_STATE = "DIRECTIONAL_NOT_ELIGIBILITY_CRITERION"
PREVIEW_STATE = "PREVIEW_PROVISIONAL_INACTIVE"
DEVNET_STATE = "DEVNET_UPCOMING_NOT_LIVE"
OPERATIONAL_MARKERS = ["devnet_upcoming_not_live", "devnet_zero_allocation"]
PINNED_CLAIM_BOUNDARY = (
    "This record preserves official directional and preview announcements. It does not establish "
    "identity-specific eligibility, accepted contribution, allocation, claimability, or payment."
)
ITEM_KEYS = {
    "id", "source", "source_snapshot", "source_snapshot_sha256", "exact_quote",
    "work_lanes", "required_markers", "quoted_post_ids", "media", "deadline",
    "linked_artifact", "exact_identity_receipt", "state",
}
SOURCE_KEYS = {"platform", "account", "post_id", "published_at", "url"}
SNAPSHOT_KEYS = {"authored_text_raw", "authored_text_expanded", "links"}
MEDIA_KEYS = {"url", "sha256", "bytes", "content_type"}

PINNED = {
    "gpu_agent_work_direction": {
        "account": "flop_labs",
        "post_id": "2105090680314069401",
        "published_at": "2026-09-30T00:21:43Z",
        "snapshot_sha256": "35269b582839a1ef78efb03401d51c499a924556ea3501c804ee765c6841ce55",
        "state": DIRECTIONAL_STATE,
        "markers": [],
        "quoted_post_ids": [],
        "media": [],
    },
    "kol_leaderboard_preview": {
        "account": "CryptoHayes",
        "post_id": "2110624608890282056",
        "published_at": "2026-10-15T06:51:34Z",
        "snapshot_sha256": "50428da86308fd92f80a0246bfda9defe75842d0d99019ba30d68cc3aa805855",
        "state": PREVIEW_STATE,
        "markers": [
            "PROVISIONAL · SAMPLE DATA",
            "Weekly payout pool: To be announced",
            "shared among the top public KOLs in proportion to certified work",
            "Interactive demo with fictional identities and balances",
        ],
        "quoted_post_ids": [],
        "media": [{
            "url": "https://pbs.twimg.com/media/HUpwzmRakAAas2L.jpg",
            "sha256": "3f8c3276b76706e9ef09ae88bf05203fcbc1226e3098bef4b3e78e534560f987",
            "bytes": 98525,
            "content_type": "image/jpeg",
        }],
    },
    "kol_join_preview": {
        "account": "CryptoHayes",
        "post_id": "2110624611604037995",
        "published_at": "2026-10-15T06:51:35Z",
        "snapshot_sha256": "cb5cd712a208551a649aaa81f032e61f51eb388c2f5f27dd2f718f573a371b56",
        "state": PREVIEW_STATE,
        "markers": [
            "PROVISIONAL · SAMPLE DATA",
            "Verify at least one handle",
            "connect your socials (optional)",
            "Email, wallet signing, social verification and funding are simulated",
        ],
        "quoted_post_ids": [],
        "media": [{
            "url": "https://pbs.twimg.com/media/HUpxM84bQAAjoYx.jpg",
            "sha256": "3886d6278f84bbcb3dacaf4a03dda280ef2eabfe323a2ca0bae9196b3e22c9cf",
            "bytes": 85335,
            "content_type": "image/jpeg",
        }],
    },
    "kol_referral_preview": {
        "account": "CryptoHayes",
        "post_id": "2110624614233845768",
        "published_at": "2026-10-15T06:51:36Z",
        "snapshot_sha256": "865db5f3898144a0a40a549bf766190395117bcea437f4495cfe5fcc67601568",
        "state": PREVIEW_STATE,
        "markers": [
            "PROVISIONAL · SAMPLE DATA",
            "Signup is simulated",
            "Payouts and the work-weighted lottery are inactive",
            "period boundaries, eligibility and reward caps still need agreement",
            "No real identity has been verified",
        ],
        "quoted_post_ids": [],
        "media": [{
            "url": "https://pbs.twimg.com/media/HUpxns1aoAEULkY.jpg",
            "sha256": "8d6ce76b4b4d1b10703e572e43f7a53e2af6066bb9aff8b064b0e2ae37427f16",
            "bytes": 97642,
            "content_type": "image/jpeg",
        }],
    },
    "kol_official_quote_preview": {
        "account": "flop_labs",
        "post_id": "2110628169476981128",
        "published_at": "2026-10-15T07:05:43Z",
        "snapshot_sha256": "cb39b221f81324c227261ab03d476b6628efb1942af3dc80c05758905064b309",
        "state": PREVIEW_STATE,
        "markers": ["Preview of the upcoming KOL leaderboard", "PROVISIONAL · SAMPLE DATA"],
        "quoted_post_ids": ["2110624608890282056"],
        "media": [],
    },
    "devnet_public_upcoming": {
        "account": "CryptoHayes",
        "post_id": "2114617436398100654",
        "published_at": "2026-10-26T07:17:39Z",
        "snapshot_sha256": "7effba624e1ba8e429cba815b28dc8a5d3449bffaae85ee5c249b3ddafb07288",
        "state": DEVNET_STATE,
        "markers": ["Participation does not count toward any token allocation."],
        "quoted_post_ids": [],
        "media": [],
    },
    "devnet_official_quote": {
        "account": "flop_labs",
        "post_id": "2114628648615772410",
        "published_at": "2026-10-26T08:02:12Z",
        "snapshot_sha256": "f3d71ac66c9024ca3fc7ee91208fc7d153b1b8f95f1f7a0f90c7c8b2317acd5f",
        "state": DEVNET_STATE,
        "markers": ["Devnet coming very soon"],
        "quoted_post_ids": ["2114617436398100654"],
        "media": [],
    },
}


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


def validate_source(source: Any, expected: dict[str, Any], field: str) -> None:
    value = strict_object(source, SOURCE_KEYS, field)
    require(value["platform"] == "x", f"{field}.platform must be x")
    require(value["account"] == expected["account"], f"{field}.account mismatch")
    post_id = value["post_id"]
    require(type(post_id) is str and POST_ID_RE.fullmatch(post_id) is not None,
            f"{field}.post_id malformed")
    require(post_id == expected["post_id"], f"{field}.post_id mismatch")
    published_at = value["published_at"]
    require(type(published_at) is str and TIMESTAMP_RE.fullmatch(published_at) is not None,
            f"{field}.published_at malformed")
    require(published_at == expected["published_at"], f"{field}.published_at mismatch")
    expected_url = f"https://x.com/{expected['account']}/status/{expected['post_id']}"
    require(value["url"] == expected_url, f"{field}.url mismatch")
    parsed = urlparse(value["url"])
    require(parsed.scheme == "https" and parsed.hostname == "x.com" and not parsed.username,
            f"{field}.url must use x.com HTTPS")


def validate_snapshot(item: dict[str, Any], expected: dict[str, Any], field: str) -> None:
    snapshot = strict_object(item["source_snapshot"], SNAPSHOT_KEYS, f"{field}.source_snapshot")
    require(type(snapshot["authored_text_raw"]) is str and bool(snapshot["authored_text_raw"]),
            f"{field}.source_snapshot.authored_text_raw invalid")
    require(type(snapshot["authored_text_expanded"]) is str and bool(snapshot["authored_text_expanded"]),
            f"{field}.source_snapshot.authored_text_expanded invalid")
    links = snapshot["links"]
    require(type(links) is list, f"{field}.source_snapshot.links invalid")
    for index, raw in enumerate(links):
        link = strict_object(raw, {"original", "expanded", "display"},
                             f"{field}.source_snapshot.links[{index}]")
        require(all(type(link[key]) is str and link[key] for key in link),
                f"{field}.source_snapshot.links[{index}] invalid")
    digest = item["source_snapshot_sha256"]
    require(type(digest) is str and SHA256_RE.fullmatch(digest) is not None,
            f"{field}.source_snapshot_sha256 malformed")
    calculated = hashlib.sha256(canonical_snapshot(snapshot)).hexdigest()
    require(digest == calculated, f"{field}.source snapshot hash does not match content")
    require(digest == expected["snapshot_sha256"], f"{field}.source snapshot hash mismatch")


def validate_media(media: Any, expected: list[dict[str, Any]], field: str) -> None:
    require(type(media) is list, f"{field}.media must be an array")
    require(media == expected, f"{field}.media does not match pinned media facets")
    for index, raw in enumerate(media):
        item = strict_object(raw, MEDIA_KEYS, f"{field}.media[{index}]")
        parsed = urlparse(item["url"])
        require(parsed.scheme == "https" and parsed.hostname == "pbs.twimg.com" and not parsed.username,
                f"{field}.media[{index}].url must use pbs.twimg.com HTTPS")
        require(type(item["sha256"]) is str and SHA256_RE.fullmatch(item["sha256"]) is not None,
                f"{field}.media[{index}].sha256 malformed")
        require(type(item["bytes"]) is int and item["bytes"] > 0,
                f"{field}.media[{index}].bytes invalid")
        require(item["content_type"] == "image/jpeg", f"{field}.media[{index}].content_type invalid")
        local_path = MEDIA_DIR / Path(parsed.path).name
        require(local_path.is_file(), f"{field}.media[{index}] local evidence missing")
        payload = local_path.read_bytes()
        require(len(payload) == item["bytes"], f"{field}.media[{index}] local byte size mismatch")
        require(hashlib.sha256(payload).hexdigest() == item["sha256"],
                f"{field}.media[{index}] local hash mismatch")


def validate(data: Any) -> dict[str, Any]:
    manifest = strict_object(
        data,
        {"schema", "captured_at", "eligibility_status", "allocation_status", "claim_boundary",
         "operational_markers", "announcements"},
        "manifest",
    )
    require(manifest["schema"] == SCHEMA, "unsupported schema")
    require(manifest["captured_at"] == "2026-10-26", "unexpected capture date")
    require(manifest["eligibility_status"] == "UNVERIFIED", "eligibility must remain UNVERIFIED")
    require(manifest["allocation_status"] == "UNVERIFIED", "allocation must remain UNVERIFIED")
    require(manifest["claim_boundary"] == PINNED_CLAIM_BOUNDARY, "claim boundary mismatch")
    require(manifest["operational_markers"] == OPERATIONAL_MARKERS,
            "operational markers must keep devnet upcoming and zero-allocation")

    announcements = manifest["announcements"]
    require(type(announcements) is list and len(announcements) == len(PINNED),
            "exact pinned announcement set required")
    observed_ids: set[str] = set()
    states: Counter[str] = Counter()

    for index, raw in enumerate(announcements):
        field = f"announcements[{index}]"
        item = strict_object(raw, ITEM_KEYS, field)
        ident = item["id"]
        require(type(ident) is str and ident in PINNED, f"{field}.id unknown")
        require(ident not in observed_ids, f"duplicate announcement id: {ident}")
        observed_ids.add(ident)
        expected = PINNED[ident]

        validate_source(item["source"], expected, f"{field}.source")
        validate_snapshot(item, expected, field)
        require(item["required_markers"] == expected["markers"], f"{field}.required_markers mismatch")
        require(item["quoted_post_ids"] == expected["quoted_post_ids"], f"{field}.quoted_post_ids mismatch")
        validate_media(item["media"], expected["media"], field)
        require(item["deadline"] is None, f"{field} cannot treat sample dates as deadlines")
        require(item["linked_artifact"] is None, f"{field} has no executable artifact")
        require(item["exact_identity_receipt"] is None, f"{field} has no exact-identity receipt")
        require(item["state"] == expected["state"], f"{field}.state mismatch")
        states[item["state"]] += 1

        lanes = item["work_lanes"]
        require(type(lanes) is list and all(type(lane) is str for lane in lanes),
                f"{field}.work_lanes invalid")
        if ident == "gpu_agent_work_direction":
            require(set(lanes) == ALLOWED_LANES and len(lanes) == 2,
                    "directional announcement requires exact work lanes")
            quote = "run GPUs or put your agent to work, and that's how you earn $ FLOP."
            require(item["exact_quote"] == quote, "directional exact quote mismatch")
            require(quote in item["source_snapshot"]["authored_text_raw"],
                    "directional quote absent from source snapshot")
        else:
            require(lanes == [], f"{field} must not invent work lanes")
            require(item["exact_quote"] is None, f"{field} exact_quote must be null")

        if ident == "devnet_public_upcoming":
            zero_allocation = "Participation does not count toward any token allocation."
            require(zero_allocation in item["source_snapshot"]["authored_text_raw"],
                    "devnet zero-allocation boundary absent from authored source")
        elif ident == "devnet_official_quote":
            require(item["source_snapshot"]["authored_text_raw"] == "Devnet coming very soon",
                    "official devnet authored text must remain separate from quoted text")
            require(item["quoted_post_ids"] == [PINNED["devnet_public_upcoming"]["post_id"]],
                    "official devnet quote relationship mismatch")

    require(observed_ids == set(PINNED), "announcement set mismatch")
    return {
        "schema": SCHEMA,
        "announcements": len(announcements),
        "work_lanes": sorted(ALLOWED_LANES),
        "states": dict(sorted(states.items())),
        "operational_markers": OPERATIONAL_MARKERS,
        "eligibility_status": "UNVERIFIED",
        "allocation_status": "UNVERIFIED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent / "evidence" / "official-announcements.json",
    )
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
