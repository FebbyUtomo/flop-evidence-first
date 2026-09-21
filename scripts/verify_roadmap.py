#!/usr/bin/env python3
"""Fail-closed validator for the public FLOP roadmap score."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROGRESS = ROOT / "evidence" / "progress.json"
DEFAULT_ROADMAP = ROOT / "ROADMAP.md"
ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
LEDGER_HEADING_RE = re.compile(
    r"^### ([a-z][a-z0-9_]{1,63}) — (.+) \((\d+) points\)$", re.MULTILINE
)
HASHED_ARTIFACT_RE = re.compile(
    r"^- Artifact: `([^`]+)` — sha256 `([a-f0-9]{64})`$", re.MULTILINE
)
COMPLETED_SECTION_RE = re.compile(
    r"^## Completed evidence ledger — (\d+) points$", re.MULTILINE
)
PENDING_SECTION_RE = re.compile(
    r"^## Pending evidence ledger — (\d+) unscored points$", re.MULTILINE
)


class ValidationError(ValueError):
    """Roadmap data failed an integrity check."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def strict_int(value: Any, field: str) -> int:
    require(type(value) is int, f"{field} must be an integer")
    return value


def strict_keys(value: Any, expected: set[str], field: str) -> dict[str, Any]:
    require(type(value) is dict, f"{field} must be an object")
    actual = set(value)
    require(actual == expected, f"{field} keys mismatch: {sorted(actual ^ expected)}")
    return value


def normalized_artifact(root: Path, relative: Any) -> Path:
    require(type(relative) is str and relative != "", "artifact path must be a string")
    pure = PurePosixPath(relative)
    require(not pure.is_absolute(), f"artifact path must be repository-relative: {relative}")
    require(relative == pure.as_posix() and "." not in pure.parts and ".." not in pure.parts,
            f"artifact path must be normalized: {relative}")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValidationError(f"artifact escapes repository: {relative}") from exc
    require(candidate.is_file(), f"missing artifact: {relative}")
    return candidate


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_markdown_workstreams(text: str) -> tuple[dict[str, tuple[int, int]], tuple[int, int]]:
    rows: dict[str, tuple[int, int]] = {}
    total: tuple[int, int] | None = None
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            continue
        if cells[0] == "**Total**":
            require(total is None, "duplicate ROADMAP.md total row")
            try:
                total = (int(cells[2].strip("*")), int(cells[3].strip("*")))
            except ValueError as exc:
                raise ValidationError("invalid ROADMAP.md total row") from exc
            continue
        ident = cells[0]
        if ID_RE.fullmatch(ident):
            require(ident not in rows, f"duplicate ROADMAP.md workstream row: {ident}")
            try:
                rows[ident] = (int(cells[2]), int(cells[3]))
            except ValueError as exc:
                raise ValidationError(f"invalid ROADMAP.md workstream row: {ident}") from exc
    if total is None:
        raise ValidationError("ROADMAP.md total row missing")
    return rows, total


def validate(data: Any, root: Path, roadmap_text: str) -> dict[str, Any]:
    top = strict_keys(
        data,
        {
            "schema", "updated_at", "score", "target", "daily_target_points",
            "allocation_status", "workstreams", "completed_tranches", "pending_tranches",
        },
        "progress",
    )
    require(top["schema"] == "nanaz.flop-roadmap.v1", "unsupported schema")
    require(type(top["updated_at"]) is str and DATE_RE.fullmatch(top["updated_at"]) is not None,
            "updated_at must be YYYY-MM-DD")
    target = strict_int(top["target"], "target")
    score = strict_int(top["score"], "score")
    daily = strict_int(top["daily_target_points"], "daily_target_points")
    require(target == 100, "target must equal 100")
    require(daily == 5, "daily target must equal 5")
    require(top["allocation_status"] == "UNVERIFIED", "allocation status must remain UNVERIFIED")

    workstreams = top["workstreams"]
    require(type(workstreams) is list and bool(workstreams), "workstreams must be a non-empty array")
    ids: set[str] = set()
    weights: dict[str, int] = {}
    scores: dict[str, int] = {}
    for index, raw in enumerate(workstreams):
        item = strict_keys(raw, {"id", "weight", "score"}, f"workstreams[{index}]")
        ident = item["id"]
        require(type(ident) is str and ID_RE.fullmatch(ident) is not None,
                f"invalid workstream id at index {index}")
        require(ident not in ids, f"duplicate workstream id: {ident}")
        ids.add(ident)
        weight = strict_int(item["weight"], f"workstreams[{index}].weight")
        points = strict_int(item["score"], f"workstreams[{index}].score")
        require(weight > 0 and 0 <= points <= weight, f"invalid score bounds for {ident}")
        weights[ident] = weight
        scores[ident] = points
    require(sum(weights.values()) == target, "workstream weights must sum to target")
    require(sum(scores.values()) == score, "workstream scores must sum to score")
    require(0 <= score <= target, "score outside target range")

    completed = top["completed_tranches"]
    pending = top["pending_tranches"]
    require(type(completed) is list, "completed_tranches must be an array")
    require(type(pending) is list, "pending_tranches must be an array")
    tranche_ids: set[str] = set()
    artifact_paths: set[str] = set()
    artifact_hashes: set[str] = set()
    resolved_artifacts: set[Path] = set()
    attributed = {ident: 0 for ident in ids}
    completed_ledger_entries: set[tuple[str, str, int]] = set()
    completed_artifact_entries: set[tuple[str, str]] = set()
    completed_points = 0
    artifact_count = 0

    for index, raw in enumerate(completed):
        tranche = strict_keys(
            raw,
            {"id", "title", "workstream", "date", "points", "artifacts", "status", "evidence"},
            f"completed_tranches[{index}]",
        )
        tranche_id = tranche["id"]
        title = tranche["title"]
        workstream = tranche["workstream"]
        require(type(tranche_id) is str and ID_RE.fullmatch(tranche_id) is not None,
                f"invalid completed tranche id at index {index}")
        require(tranche_id not in tranche_ids, f"duplicate tranche id: {tranche_id}")
        tranche_ids.add(tranche_id)
        require(type(title) is str and title.strip() == title and 3 <= len(title) <= 120,
                f"invalid completed tranche title: {tranche_id}")
        require(workstream in ids, f"unknown completed tranche workstream: {workstream}")
        require(type(tranche["date"]) is str and DATE_RE.fullmatch(tranche["date"]) is not None,
                f"invalid completed tranche date at index {index}")
        points = strict_int(tranche["points"], f"completed_tranches[{index}].points")
        require(points == daily, "every completed tranche must equal the daily 5-point unit")
        require(tranche["status"] == "verified", "completed tranche status must be verified")
        require(type(tranche["evidence"]) is str and len(tranche["evidence"].strip()) >= 20,
                "completed tranche requires a concrete evidence statement")
        artifacts = tranche["artifacts"]
        require(type(artifacts) is list and bool(artifacts), "completed tranche requires artifacts")
        for artifact_index, raw_artifact in enumerate(artifacts):
            artifact = strict_keys(raw_artifact, {"path", "sha256"},
                                   f"completed_tranches[{index}].artifacts[{artifact_index}]")
            relative = artifact["path"]
            require(type(relative) is str and relative not in artifact_paths,
                    f"duplicate artifact path: {relative}")
            path = normalized_artifact(root, relative)
            expected_hash = artifact["sha256"]
            require(type(expected_hash) is str and SHA256_RE.fullmatch(expected_hash) is not None,
                    f"invalid artifact hash: {relative}")
            require(path not in resolved_artifacts, f"duplicate resolved artifact: {relative}")
            require(expected_hash not in artifact_hashes,
                    f"duplicate artifact content hash: {relative}")
            require(digest(path) == expected_hash, f"artifact hash mismatch: {relative}")
            artifact_paths.add(relative)
            artifact_hashes.add(expected_hash)
            resolved_artifacts.add(path)
            completed_artifact_entries.add((relative, expected_hash))
            artifact_count += 1
        attributed[workstream] += points
        completed_points += points
        completed_ledger_entries.add((tranche_id, title, points))

    require(completed_points == score, "completed tranche points must equal score")
    require(attributed == scores, "completed tranche attribution must equal workstream scores")

    pending_ledger_entries: set[tuple[str, str, int]] = set()
    for index, raw in enumerate(pending):
        tranche = strict_keys(
            raw,
            {"id", "title", "workstream", "date", "points", "artifact", "status", "blocker"},
            f"pending_tranches[{index}]",
        )
        tranche_id = tranche["id"]
        title = tranche["title"]
        workstream = tranche["workstream"]
        require(type(tranche_id) is str and ID_RE.fullmatch(tranche_id) is not None,
                f"invalid pending tranche id at index {index}")
        require(tranche_id not in tranche_ids, f"duplicate tranche id: {tranche_id}")
        tranche_ids.add(tranche_id)
        require(type(title) is str and title.strip() == title and 3 <= len(title) <= 120,
                f"invalid pending tranche title: {tranche_id}")
        require(workstream in ids, f"unknown pending tranche workstream: {workstream}")
        require(type(tranche["date"]) is str and DATE_RE.fullmatch(tranche["date"]) is not None,
                f"invalid pending tranche date at index {index}")
        points = strict_int(tranche["points"], f"pending_tranches[{index}].points")
        require(points == daily, "pending tranche must use the 5-point unit")
        require(tranche["status"] == "pending", "pending tranche status must be pending")
        relative = tranche["artifact"]
        require(type(relative) is str and relative not in artifact_paths,
                f"duplicate artifact path: {relative}")
        pending_path = normalized_artifact(root, relative)
        require(pending_path not in resolved_artifacts, f"duplicate resolved artifact: {relative}")
        artifact_paths.add(relative)
        resolved_artifacts.add(pending_path)
        require(type(tranche["blocker"]) is str and bool(tranche["blocker"].strip()),
                "pending tranche requires a blocker")
        pending_ledger_entries.add((tranche_id, title, points))

    markdown_rows, markdown_total = parse_markdown_workstreams(roadmap_text)
    require(markdown_rows == {ident: (weights[ident], scores[ident]) for ident in ids},
            "ROADMAP.md workstream rows do not match progress.json")
    require(markdown_total == (target, score), "ROADMAP.md total does not match progress.json")

    completed_sections = COMPLETED_SECTION_RE.findall(roadmap_text)
    require(completed_sections == [str(score)],
            "ROADMAP.md completed ledger total mismatch or duplicate")
    pending_points = sum(strict_int(item["points"], "pending points") for item in pending)
    pending_sections = PENDING_SECTION_RE.findall(roadmap_text)
    require(pending_sections == [str(pending_points)],
            "ROADMAP.md pending ledger total mismatch or duplicate")

    actual_headings = {
        (ident, title, int(points))
        for ident, title, points in LEDGER_HEADING_RE.findall(roadmap_text)
    }
    expected_headings = completed_ledger_entries | pending_ledger_entries
    require(actual_headings == expected_headings and
            len(LEDGER_HEADING_RE.findall(roadmap_text)) == len(expected_headings),
            "ROADMAP.md visible tranche headings do not match progress.json")
    actual_hashed_artifacts = set(HASHED_ARTIFACT_RE.findall(roadmap_text))
    require(actual_hashed_artifacts == completed_artifact_entries and
            len(HASHED_ARTIFACT_RE.findall(roadmap_text)) == len(completed_artifact_entries),
            "ROADMAP.md visible artifact hashes do not match progress.json")

    for tranche in completed:
        artifact_lines = "\n".join(
            f"- Artifact: `{item['path']}` — sha256 `{item['sha256']}`"
            for item in tranche["artifacts"]
        )
        block = (
            f"### {tranche['id']} — {tranche['title']} ({tranche['points']} points)\n\n"
            f"- Workstream: `{tranche['workstream']}`\n"
            f"- Status: `verified`\n{artifact_lines}"
        )
        require(roadmap_text.count(block) == 1,
                f"ROADMAP.md visible completed block mismatch: {tranche['id']}")
    for tranche in pending:
        block = (
            f"### {tranche['id']} — {tranche['title']} ({tranche['points']} points)\n\n"
            f"- Workstream: `{tranche['workstream']}`\n"
            f"- Status: `pending`\n- Artifact: `{tranche['artifact']}`"
        )
        require(roadmap_text.count(block) == 1,
                f"ROADMAP.md visible pending block mismatch: {tranche['id']}")

    return {
        "schema": top["schema"],
        "score": score,
        "target": target,
        "workstreams": len(workstreams),
        "completed_tranches": len(completed),
        "pending_tranches": len(pending),
        "artifacts": artifact_count,
        "allocation_status": top["allocation_status"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--roadmap", type=Path, default=DEFAULT_ROADMAP)
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.progress.read_text(encoding="utf-8"))
        roadmap_text = args.roadmap.read_text(encoding="utf-8")
        result = validate(data, args.root.resolve(), roadmap_text)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"roadmap_invalid:{type(exc).__name__}:{exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
