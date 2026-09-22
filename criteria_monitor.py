#!/usr/bin/env python3
"""Read-only drift monitor for official draft FLOP criteria sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, cast
from urllib.parse import urlparse
from urllib.request import Request, urlopen


SCHEMA = "nanaz.flop-official-criteria.v1"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_HOSTS = {"flop.finance", "ask.flop.finance"}
USER_AGENT = "flop-criteria-monitor/1.0"


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)


def normalize_text(value: str) -> str:
    return " ".join(unescape(value).split())


def visible_html_text(value: str) -> str:
    parser = VisibleTextParser()
    parser.feed(value)
    return normalize_text(" ".join(parser.parts))


def text_digest(value: str) -> str:
    return hashlib.sha256(normalize_text(value).encode("utf-8")).hexdigest()


def fetch_visible_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        raw = response.read().decode(charset, "replace")
    return visible_html_text(raw)


def validate_manifest(data: Any) -> dict[str, Any]:
    require(type(data) is dict, "manifest must be an object")
    expected_top = {
        "schema", "captured_at", "allocation_status", "claim_boundary",
        "sources", "known_conflicts",
    }
    require(set(data) == expected_top, "manifest keys mismatch")
    require(data["schema"] == SCHEMA, "unsupported schema")
    require(type(data["captured_at"]) is str and DATE_RE.fullmatch(data["captured_at"]) is not None,
            "captured_at must be YYYY-MM-DD")
    require(data["allocation_status"] == "UNVERIFIED", "allocation status must remain UNVERIFIED")
    boundary = data["claim_boundary"]
    require(type(boundary) is str and "does not establish" in boundary and "allocation" in boundary,
            "claim boundary is incomplete")

    raw_sources = data["sources"]
    require(type(raw_sources) is list and len(raw_sources) >= 3, "at least three official sources required")
    sources = cast(list[Any], raw_sources)
    source_ids: set[str] = set()
    urls: set[str] = set()
    source_by_id: dict[str, dict[str, Any]] = {}
    source_keys = {"id", "url", "authority", "baseline_sha256", "required_markers"}
    for index, raw in enumerate(sources):
        require(type(raw) is dict and set(raw) == source_keys, f"sources[{index}] keys mismatch")
        source = cast(dict[str, Any], raw)
        ident = source["id"]
        require(type(ident) is str and ID_RE.fullmatch(ident) is not None, f"sources[{index}].id invalid")
        require(ident not in source_ids, f"duplicate source id: {ident}")
        source_ids.add(ident)
        url = source["url"]
        require(type(url) is str, f"sources[{index}].url invalid")
        parsed = urlparse(url)
        require(parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS and not parsed.username,
                f"source URL is not an allowlisted HTTPS origin: {url}")
        require(url not in urls, f"duplicate source URL: {url}")
        urls.add(url)
        authority = source["authority"]
        require(type(authority) is str and authority.startswith("official_"),
                f"sources[{index}].authority invalid")
        baseline = source["baseline_sha256"]
        require(type(baseline) is str and SHA256_RE.fullmatch(baseline) is not None,
                f"sources[{index}].baseline_sha256 invalid")
        markers = source["required_markers"]
        require(type(markers) is list and bool(markers), f"sources[{index}] requires markers")
        require(all(type(marker) is str and len(marker.strip()) >= 8 for marker in markers),
                f"sources[{index}] marker invalid")
        require(len(markers) == len(set(markers)), f"sources[{index}] duplicate marker")
        source_by_id[ident] = source

    raw_conflicts = data["known_conflicts"]
    require(type(raw_conflicts) is list, "known_conflicts must be an array")
    conflict_ids: set[str] = set()
    conflict_keys = {"id", "source_ids", "markers", "status", "explanation"}
    for index, raw in enumerate(raw_conflicts):
        require(type(raw) is dict and set(raw) == conflict_keys,
                f"known_conflicts[{index}] keys mismatch")
        conflict = cast(dict[str, Any], raw)
        ident = conflict["id"]
        require(type(ident) is str and ID_RE.fullmatch(ident) is not None,
                f"known_conflicts[{index}].id invalid")
        require(ident not in conflict_ids, f"duplicate conflict id: {ident}")
        conflict_ids.add(ident)
        ids = conflict["source_ids"]
        markers = conflict["markers"]
        require(type(ids) is list and len(ids) == 2 and len(set(ids)) == 2,
                f"known_conflicts[{index}].source_ids invalid")
        require(type(markers) is list and len(markers) == 2,
                f"known_conflicts[{index}].markers invalid")
        for source_id, marker in zip(ids, markers):
            require(source_id in source_by_id, f"unknown conflict source: {source_id}")
            require(marker in source_by_id[source_id]["required_markers"],
                    f"conflict marker is not pinned by source: {marker}")
        require(conflict["status"] == "UNRESOLVED_DRAFT_CONFLICT",
                f"known_conflicts[{index}].status invalid")
        require(type(conflict["explanation"]) is str and len(conflict["explanation"].strip()) >= 40,
                f"known_conflicts[{index}].explanation invalid")
    return cast(dict[str, Any], data)


def evaluate(data: Any, fetcher: Callable[[str], str] = fetch_visible_text) -> dict[str, Any]:
    manifest = validate_manifest(data)
    changed_sources: list[str] = []
    material_changes: list[dict[str, str]] = []
    observed: dict[str, str] = {}

    for source in manifest["sources"]:
        text = normalize_text(fetcher(source["url"]))
        observed[source["id"]] = text
        digest = text_digest(text)
        if digest != source["baseline_sha256"]:
            changed_sources.append(source["id"])
        for marker in source["required_markers"]:
            if marker not in text:
                material_changes.append({"source": source["id"], "missing_marker": marker})

    status = "unchanged"
    if material_changes:
        status = "material_change"
    elif changed_sources:
        status = "content_changed"

    return {
        "schema": SCHEMA,
        "status": status,
        "sources_checked": len(manifest["sources"]),
        "changed_sources": changed_sources,
        "material_changes": material_changes,
        "known_draft_conflicts": [item["id"] for item in manifest["known_conflicts"]],
        "allocation_status": "UNVERIFIED",
    }


def result_exit_code(result: dict[str, Any]) -> int:
    return {"unchanged": 0, "content_changed": 2, "material_change": 3}[result["status"]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.manifest_only:
            manifest = validate_manifest(data)
            result = {
                "schema": SCHEMA,
                "status": "manifest_valid",
                "sources": len(manifest["sources"]),
                "known_draft_conflicts": len(manifest["known_conflicts"]),
                "allocation_status": "UNVERIFIED",
            }
            print(json.dumps(result, sort_keys=True))
            return 0
        result = evaluate(data)
        print(json.dumps(result, sort_keys=True))
        return result_exit_code(result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"criteria_monitor_error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
