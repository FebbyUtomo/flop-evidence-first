#!/usr/bin/env python3
"""Offline validator for attributable FLOP community-adoption evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_EVIDENCE = ROOT / "evidence" / "community-adoption.json"
SHA1_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def exact(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    require(type(value) is dict, f"{field} must be an object")
    require(set(value) == keys, f"{field} keys mismatch")
    return value


def validate(data: Any, root: Path = ROOT) -> dict[str, Any]:
    top = exact(data, {"schema", "observed_at", "source_repository", "adoption",
                       "independence_assessment", "official_status"}, "record")
    require(top["schema"] == "nanaz.flop-community-adoption.v1", "unsupported schema")
    require(top["source_repository"] == "FebbyUtomo/flop-evidence-first", "wrong source")
    require(type(top["observed_at"]) is str and TIMESTAMP_RE.fullmatch(top["observed_at"]) is not None,
            "invalid observation timestamp")

    adoption = exact(top["adoption"], {
        "kind", "actor", "actor_github_id", "actor_account_created_at",
        "actor_public_repositories", "fork_repository", "fork_repository_id",
        "fork_created_at", "fork_url", "github_api_url", "fork", "default_branch",
        "head_commit", "head_commit_date", "head_commit_title", "tutorial_path",
        "tutorial_blob_sha1", "tutorial_sha256", "tutorial_url",
    }, "adoption")
    require(adoption["kind"] == "github_fork" and adoption["fork"] is True,
            "adoption must be an explicit GitHub fork")
    require(adoption["actor"] == "putrikeme", "unexpected actor")
    require(type(adoption["actor_github_id"]) is int and adoption["actor_github_id"] > 0,
            "invalid actor id")
    require(type(adoption["fork_repository_id"]) is int and adoption["fork_repository_id"] > 0,
            "invalid repository id")
    require(type(adoption["actor_public_repositories"]) is int and
            adoption["actor_public_repositories"] > 0, "actor lacks public history")
    require(adoption["fork_repository"] == f"{adoption['actor']}/flop-evidence-first",
            "fork owner mismatch")
    require(adoption["fork_url"] == f"https://github.com/{adoption['fork_repository']}",
            "fork URL mismatch")
    require(adoption["github_api_url"] ==
            f"https://api.github.com/repos/{adoption['fork_repository']}", "API URL mismatch")
    require(adoption["default_branch"] == "main", "unexpected default branch")
    for field in ("actor_account_created_at", "fork_created_at", "head_commit_date"):
        require(type(adoption[field]) is str and TIMESTAMP_RE.fullmatch(adoption[field]) is not None,
                f"invalid {field}")
    require(adoption["actor_account_created_at"] < adoption["fork_created_at"],
            "actor account does not predate fork")
    require(type(adoption["head_commit"]) is str and SHA1_RE.fullmatch(adoption["head_commit"]) is not None,
            "invalid head commit")
    require(type(adoption["tutorial_blob_sha1"]) is str and
            SHA1_RE.fullmatch(adoption["tutorial_blob_sha1"]) is not None, "invalid blob sha1")
    require(type(adoption["tutorial_sha256"]) is str and
            SHA256_RE.fullmatch(adoption["tutorial_sha256"]) is not None, "invalid tutorial sha256")
    require(adoption["tutorial_path"] == "docs/tutorial-bilingual.md", "unexpected tutorial path")
    expected_url = (f"https://github.com/{adoption['fork_repository']}/blob/"
                    f"{adoption['head_commit']}/{adoption['tutorial_path']}")
    require(adoption["tutorial_url"] == expected_url, "tutorial URL is not commit-pinned")
    local = (root / adoption["tutorial_path"]).read_bytes()
    require(hashlib.sha256(local).hexdigest() == adoption["tutorial_sha256"],
            "forked tutorial does not match local artifact")

    independence = exact(top["independence_assessment"], {
        "source_owner", "actor_differs_from_source_owner", "account_predates_repository",
        "account_has_prior_public_repository_history", "classification", "boundary",
    }, "independence_assessment")
    require(independence["source_owner"] == "FebbyUtomo", "source owner mismatch")
    require(adoption["actor"].casefold() != independence["source_owner"].casefold(),
            "self-fork is not independent adoption")
    require(independence["actor_differs_from_source_owner"] is True and
            independence["account_predates_repository"] is True and
            independence["account_has_prior_public_repository_history"] is True,
            "independence indicators are incomplete")
    require(independence["classification"] == "INDEPENDENT_PUBLIC_ACTOR",
            "invalid independence classification")
    require(type(independence["boundary"]) is str and len(independence["boundary"]) >= 100,
            "claim boundary is missing")

    statuses = exact(top["official_status"], {
        "flop_labs_recognition", "arthur_hayes_recognition", "eligibility", "allocation",
        "claimable", "claimed", "paid",
    }, "official_status")
    require(set(statuses.values()) == {"UNVERIFIED"}, "official state cannot be upgraded")
    return {"adoption": "VERIFIED_FORK", "actor": adoption["actor"],
            "head_commit": adoption["head_commit"], "official_status": "UNVERIFIED"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.evidence.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"adoption_invalid:{type(exc).__name__}:{exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
