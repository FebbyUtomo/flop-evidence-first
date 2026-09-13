#!/usr/bin/env python3
"""Offline, fail-closed quality gate for Technocore task drafts.

This module intentionally contains no network client and no signing-key loader.
It produces review decisions only; it cannot claim or publish work.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SUPPORTED_TYPES = {"analysis", "audit", "build", "check", "coordinate", "data", "explain", "research", "review", "security", "security_audit", "verify"}
GENERIC_PHRASES = (
    "based on available information",
    "multiple interconnected factors",
    "the core idea centers on",
    "areas needing attention: edge cases",
    "implementation approach: use standard library tools",
)
SENSITIVE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:seed|private[_ -]?key|passphrase)\s*[:=]\s*\S+", re.I),
    re.compile(r"-----BEGIN (?:ENCRYPTED )?PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_ -]?key|bearer)\s*[:= ]\s*[A-Za-z0-9._-]{20,}", re.I),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"(?:^|\s)/" + r"root/\S+"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)


def _valid_https_sources(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    valid: list[str] = []
    domains: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            continue
        domain = parsed.hostname.lower().rstrip(".")
        if domain == "localhost" or domain.endswith((".local", ".internal")):
            continue
        try:
            if ipaddress.ip_address(domain).is_private or ipaddress.ip_address(domain).is_loopback:
                continue
        except ValueError:
            if "." not in domain:
                continue
        if domain in domains:
            continue
        domains.add(domain)
        valid.append(value)
    return valid


def _contains_sensitive(text: str) -> bool:
    return any(pattern.search(text) for pattern in SENSITIVE_PATTERNS)


def evaluate(job: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    job_id = str(job.get("id") or "").strip()
    task_type = str(job.get("type") or "").strip().lower()
    description = str(job.get("description") or job.get("desc") or "").strip()
    body = str(draft.get("body") or "").strip()
    sources = _valid_https_sources(draft.get("sources"))

    if not re.fullmatch(r"k[a-zA-Z0-9_-]{1,64}", job_id):
        reasons.append("invalid_job_id")
    if task_type not in SUPPORTED_TYPES:
        reasons.append("unsupported_type")
    if len(description) < 12:
        reasons.append("insufficient_job_context")
    if len(body) < 180:
        reasons.append("draft_too_short")

    lowered = body.lower()
    if any(phrase in lowered for phrase in GENERIC_PHRASES):
        reasons.append("generic_boilerplate")
    if _contains_sensitive(body) or _contains_sensitive(json.dumps(draft)):
        reasons.append("sensitive_content")

    if task_type in {"research", "analysis", "check", "verify", "audit", "security", "security_audit", "review"}:
        if len(sources) < 2:
            reasons.append("insufficient_public_sources")

    if task_type == "build":
        # Never trust caller-supplied test receipts. Running arbitrary draft
        # commands here would be unsafe, so builds always require an
        # independent execution review outside this structural gate.
        reasons.append("build_requires_manual_execution_review")
        artifact = draft.get("artifact")
        tests = draft.get("tests")
        if not artifact:
            reasons.append("missing_artifact")
        elif not isinstance(artifact, dict):
            reasons.append("artifact_not_verified")
        else:
            artifact_path = Path(str(artifact.get("path") or ""))
            expected_hash = str(artifact.get("sha256") or "")
            if (not artifact_path.is_file() or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
                    or hashlib.sha256(artifact_path.read_bytes()).hexdigest() != expected_hash):
                reasons.append("artifact_not_verified")
        if not isinstance(tests, dict) or not tests.get("command"):
            reasons.append("missing_test_evidence")
        elif (tests.get("exit_code") != 0
              or not re.fullmatch(r"[0-9a-f]{64}", str(tests.get("output_sha256") or ""))):
            reasons.append("test_evidence_not_verified")

    reasons = sorted(set(reasons))
    return {
        "schema": "nanaz.kibble.quality-decision.v1",
        "job_id": job_id,
        "task_type": task_type,
        "gate_passed": not reasons,
        "approved": False,
        "reasons": reasons,
        "valid_source_count": len(sources),
        "mode": "offline_only",
        "can_publish": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Kibble draft quality gate")
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = evaluate(json.loads(args.job.read_text()), json.loads(args.draft.read_text()))
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end="")
    return 0 if result["gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
