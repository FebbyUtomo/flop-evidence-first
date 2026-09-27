#!/usr/bin/env python3
"""Offline verifier for the official FLOP Close Call package and sample replay."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "evidence" / "close-call-source.json"
PACKAGE = ROOT / "evidence" / "fixtures" / "close-call-official"
COMMIT = "66c1da36538e4b1c685417d2f66922906b13fea0"
MANIFEST_SHA256 = "bae09812e25eb6f1369c611f24964f7ea0acafddfc45301a16f33f941296dafa"
PINNED = {
    "close_call_fold.py": (11754, "19e13cd15dd4e9078b608a94776947bb52bba86367446d0a405c0b05c85173d4"),
    "contest.json": (1282, "f2c08c1388fe7f29b13be01cf4655dcf2f2178aa2df92edac5841d5a021da831"),
    "examples/sample-season.jsonl": (3388, "54c830076d3ee6da71a0093f626be20d97be3fd3784c362b6d4d7e5070911b7b"),
}
UNVERIFIED = {"registration", "minted", "settled", "ranked", "prize_eligible",
              "claimable", "claimed", "paid"}


class VerificationError(ValueError):
    """Pinned evidence failed closed."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise VerificationError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    require(type(value) is dict and set(value) == keys, f"{label} keys mismatch")
    return value


def validate_source(source: Any) -> dict[str, Any]:
    top = exact(source, {"schema", "observed_at", "announcement", "repository",
                         "launch_seed", "lifecycle"}, "source")
    require(top["schema"] == "nanaz.close-call-source.v1", "source schema mismatch")
    announcement = exact(top["announcement"], {"actor", "post_id", "posted_at", "url"},
                         "announcement")
    require(announcement == {
        "actor": "Arthur Hayes (@CryptoHayes)",
        "post_id": "2103453504513937720",
        "posted_at": "2026-09-25T11:56:10Z",
        "url": "https://x.com/CryptoHayes/status/2103453504513937720",
    }, "announcement mismatch")
    repository = exact(top["repository"], {"owner", "name", "commit", "commit_url",
                                                "manifest_url", "manifest_sha256"}, "repository")
    require(repository["owner"] == "flop-labs" and
            repository["name"] == "technocore-close-call-challenge" and
            repository["commit"] == COMMIT and
            repository["manifest_sha256"] == MANIFEST_SHA256 and
            COMMIT in repository["commit_url"] and COMMIT in repository["manifest_url"],
            "repository pin mismatch")
    seed = exact(top["launch_seed"], {"room", "sequence", "season", "package_sha256",
                                             "price", "trade_time", "trade_id", "url"}, "seed")
    require(seed["room"] == "d-close1-price" and seed["sequence"] == 1 and
            seed["season"] == "close-1" and seed["package_sha256"] == MANIFEST_SHA256 and
            seed["trade_time"] == "2026-09-25T11:59:42.666000Z" and
            seed["trade_id"] == 626256716983248,
            "launch seed mismatch")
    lifecycle = top["lifecycle"]
    require(type(lifecycle) is dict and set(lifecycle) == UNVERIFIED | {"package_verified"},
            "lifecycle keys mismatch")
    require(lifecycle["package_verified"] is True and
            all(lifecycle[key] == "UNVERIFIED" for key in UNVERIFIED),
            "external lifecycle state was upgraded")
    return top


def load_fold(path: Path):
    spec = importlib.util.spec_from_file_location("pinned_close_call_fold", path)
    if spec is None or spec.loader is None:
        raise VerificationError("cannot load pinned fold")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify(package: Path = PACKAGE, source_path: Path = SOURCE) -> dict[str, Any]:
    source = validate_source(json.loads(source_path.read_text(encoding="utf-8")))
    manifest_path = package / "manifest.json"
    require(digest(manifest_path) == MANIFEST_SHA256, "manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["package"] == "technocore-close-call" and manifest["schema_version"] == 1,
            "manifest identity mismatch")
    for relative, (size, expected_hash) in PINNED.items():
        manifest_name = relative
        local_name = relative[len("examples/"):] if relative.startswith("examples/") else relative
        path = package / local_name
        item = manifest["files"].get(manifest_name)
        require(item == {"bytes": size, "sha256": expected_hash, "url": manifest_name},
                f"manifest entry mismatch: {relative}")
        require(path.is_file() and path.stat().st_size == size and digest(path) == expected_hash,
                f"artifact mismatch: {relative}")
    contest = json.loads((package / "contest.json").read_text(encoding="utf-8"))
    require(contest["contest_id"] == "close-1" and contest["limit_window"] == "0.05" and
            contest["fee_rate"] == "0.01" and contest["fee_rule"] == "clawback" and
            contest["lock"] == "2026-10-04T09:00:00Z" and
            contest["final_price_time"] == "2026-10-04T10:00:00Z",
            "contest rule mismatch")
    fold = load_fold(package / "close_call_fold.py")
    config = {key: contest[key] for key in fold.DEFAULTS if key in contest}
    actual = fold.replay((package / "sample-season.jsonl").read_text(encoding="utf-8").splitlines(),
                         config)
    expected = json.loads((package / "sample-season.expected.json").read_text(encoding="utf-8"))
    require(actual == expected, "official sample replay mismatch")
    return {
        "contest": "close-1",
        "commit": COMMIT,
        "manifest_sha256": MANIFEST_SHA256,
        "pinned_artifacts_verified": len(PINNED),
        "sample_sweeps": len(actual["sweeps"]),
        "sample_owners": actual["final"]["owners"],
        "sample_zero_sum": actual["final"]["zero_sum"],
        "registration": source["lifecycle"]["registration"],
        "eligibility": source["lifecycle"]["prize_eligible"],
        "allocation": "UNVERIFIED",
        "payment": source["lifecycle"]["paid"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, default=PACKAGE)
    parser.add_argument("--source", type=Path, default=SOURCE)
    args = parser.parse_args()
    try:
        result = verify(args.package, args.source)
    except (OSError, KeyError, json.JSONDecodeError, VerificationError, ValueError) as exc:
        print(f"close_call_invalid:{type(exc).__name__}:{exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
