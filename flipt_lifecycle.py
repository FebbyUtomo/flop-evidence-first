#!/usr/bin/env python3
"""Offline, read-only validator for a public-safe Flipt lifecycle fixture."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast


SCHEMA = "nanaz.flipt-lifecycle.v1"
CHAIN_ID = 5042002
EXPECTED_ACTIONS = (
    "graduated",
    "unbond_requested",
    "release_claimed",
    "liquidity_added",
    "auto_sell_created",
    "auto_sell_executed",
)
TX_RE = re.compile(r"^0x[0-9a-f]{64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SELECTOR_RE = re.compile(r"^0x[0-9a-f]{8}$")
ADDRESS_RE = re.compile(r"(?<![0-9a-fA-F])0x[0-9a-fA-F]{40}(?![0-9a-fA-F])")
SENSITIVE_KEY_RE = re.compile(
    r"(?:address|api[_-]?key|balance|credential|mnemonic|pass(?:word|wd)?|private[_-]?key|rpc|secret|seed|wallet)",
    re.IGNORECASE,
)
EVIDENCE_ANCHORS = {
    "graduated": {
        "tx_hash": "0x382e36151a6803eed28af47c904e4b998719c7a8cf1e88e306c46cdb117246a7",
        "block_number": 62165818,
        "timestamp": "2026-09-15T02:55:32Z",
        "method_selector": "0xff6d8d05",
        "input_sha256": "8196827295e102a9d8df498eaf2dba430817660e41b1a35692a64f422cdc7218",
        "decoded_method": "graduate",
    },
    "unbond_requested": {
        "tx_hash": "0x5d36fae98c3986c2d314c75ad831779021129173d839f2197b52166089c31738",
        "block_number": 62211650,
        "timestamp": "2026-09-15T09:39:31Z",
        "method_selector": "0xede94c22",
        "input_sha256": "bd72f6a777bd7d72e9324decd84217b9c1f61b877ea5ab74f5ff302712c64973",
        "amount": {"symbol": "NAKF", "value": "100000"},
        "maturity_seconds": 90,
        "unlocks_at": "2026-09-15T09:41:01Z",
    },
    "release_claimed": {
        "tx_hash": "0x195124558bd5fe75a316c638869600d600f4d8f133b987333d1b133f17e6e249",
        "block_number": 62211796,
        "timestamp": "2026-09-15T09:41:17Z",
        "method_selector": "0x5dd68e16",
        "input_sha256": "dfdc9c5c4987a972098008e96cb59eb35a0e8902090a75528f50af0749b6e7a2",
        "amount": {"symbol": "NAKF", "value": "100000"},
        "swap_observed": False,
    },
    "liquidity_added": {
        "tx_hash": "0xb8ec86b05769dc9f7e3b0a27d1662a977965bc6800078d34ee8dfa0e1052839e",
        "block_number": 62212435,
        "timestamp": "2026-09-15T09:47:45Z",
        "method_selector": "0x2aaeb990",
        "input_sha256": "a1530185616625c85fa6565d297a361ac731996ddcdffaf68259b095a58f6619",
        "lp_receipt": {"symbol": "fLP-NAKF", "value": "0.389179046468619699"},
    },
    "auto_sell_created": {
        "tx_hash": "0xd9644130255ceb395a7d4932eb1666e238143d882e86d8d33cde3d594ed9bc9a",
        "block_number": 62214167,
        "timestamp": "2026-09-15T10:02:20Z",
        "method_selector": "0xede94c22",
        "input_sha256": "25ad25ae3d6badd2de8830deb0569fee3aad65cc0ca6f137885004845bc69f28",
        "mode": "auto_sell",
        "tranche_id": 5170,
        "amount": {"symbol": "NAKF", "value": "100000"},
        "maturity_seconds": 90,
        "matures_at": "2026-09-15T10:03:50Z",
        "keeper_funding": {"symbol": "test-USDC", "value": "0.02"},
    },
    "auto_sell_executed": {
        "tx_hash": "0x76124ead65b3e3c01449ee01764d54e9e73f243ea6ec4cf3580d088a1ee6c7e1",
        "block_number": 62214390,
        "timestamp": "2026-09-15T10:04:14Z",
        "method_selector": "0x64ec4d23",
        "input_sha256": "019c47005e6eac9572ab9cb44f8d6c2dd598eee8e3a84a1635b9c1be92cb2501",
        "mode": "auto_sell",
        "tranche_id": 5170,
        "external_executor": True,
        "settlement": {"symbol": "test-USDC", "value": "1.405283"},
        "final_state": "filled",
    },
}
COMMON_EVENT_KEYS = {
    "action", "tx_hash", "source_url", "block_number", "timestamp",
    "status", "finalized", "method_selector", "input_sha256",
}
EVENT_KEYS = {
    "graduated": COMMON_EVENT_KEYS | {"decoded_method"},
    "unbond_requested": COMMON_EVENT_KEYS | {"amount", "maturity_seconds", "unlocks_at"},
    "release_claimed": COMMON_EVENT_KEYS | {"amount", "swap_observed"},
    "liquidity_added": COMMON_EVENT_KEYS | {"lp_receipt"},
    "auto_sell_created": COMMON_EVENT_KEYS | {
        "mode", "tranche_id", "amount", "maturity_seconds", "matures_at", "keeper_funding",
    },
    "auto_sell_executed": COMMON_EVENT_KEYS | {
        "mode", "tranche_id", "external_executor", "settlement", "final_state",
    },
}


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def parse_time(value: Any, field: str) -> datetime:
    require(type(value) is str and value.endswith("Z"), f"{field} must be UTC ISO-8601")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValidationError(f"{field} is invalid") from exc
    require(parsed.tzinfo == timezone.utc, f"{field} must use UTC")
    return parsed


def positive_decimal(value: Any, field: str) -> Decimal:
    require(type(value) is str, f"{field} must be a decimal string")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationError(f"{field} is invalid") from exc
    require(number.is_finite() and number > 0, f"{field} must be positive")
    return number


def scan_public_shape(value: Any, path: str = "root") -> None:
    if type(value) is dict:
        for key, child in value.items():
            require(type(key) is str, f"{path} contains a non-string key")
            require(SENSITIVE_KEY_RE.search(key) is None, f"{path}.{key} is private material")
            scan_public_shape(child, f"{path}.{key}")
    elif type(value) is list:
        for index, child in enumerate(value):
            scan_public_shape(child, f"{path}[{index}]")
    elif type(value) is str:
        require(ADDRESS_RE.search(value) is None, f"{path} contains an EVM address")


def validate_amount(value: Any, field: str) -> None:
    require(type(value) is dict and set(value) == {"symbol", "value"}, f"{field} shape is invalid")
    require(type(value["symbol"]) is str and bool(value["symbol"]), f"{field}.symbol is invalid")
    positive_decimal(value["value"], f"{field}.value")


def validate(data: Any) -> dict[str, Any]:
    require(type(data) is dict, "fixture must be an object")
    scan_public_shape(data)
    require(set(data) == {"schema", "chain_id", "network", "claim_boundary", "events"},
            "fixture keys mismatch")
    require(data.get("schema") == SCHEMA, "wrong schema")
    require(type(data.get("chain_id")) is int and data["chain_id"] == CHAIN_ID, "wrong chain_id")
    require(data.get("network") == "Arc Testnet", "wrong network")
    boundary = data.get("claim_boundary")
    require(type(boundary) is str and "do not prove FLOP" in boundary, "claim boundary is incomplete")
    raw_events = data.get("events")
    require(type(raw_events) is list and len(raw_events) == len(EXPECTED_ACTIONS),
            "six lifecycle events required")
    require(all(type(event) is dict for event in raw_events), "each lifecycle event must be an object")
    events = cast(list[dict[str, Any]], raw_events)
    require(tuple(event.get("action") for event in events) == EXPECTED_ACTIONS,
            "lifecycle event order is invalid")

    hashes: set[str] = set()
    previous_block = -1
    previous_time: datetime | None = None
    for index, event in enumerate(events):
        require(type(event) is dict, f"events[{index}] must be an object")
        action = event["action"]
        require(set(event) == EVENT_KEYS[action], f"events[{index}] keys mismatch")
        anchor = EVIDENCE_ANCHORS[action]
        raw_tx_hash = event.get("tx_hash")
        require(type(raw_tx_hash) is str and TX_RE.fullmatch(raw_tx_hash) is not None,
                f"events[{index}].tx_hash is invalid")
        tx_hash = cast(str, raw_tx_hash)
        require(tx_hash not in hashes, "duplicate transaction hash")
        hashes.add(tx_hash)
        expected_url = f"https://api-testnet.arc-scan.org/v1/txs/{tx_hash}"
        require(event.get("source_url") == expected_url, f"events[{index}].source_url does not match tx_hash")
        raw_block = event.get("block_number")
        require(type(raw_block) is int, f"events[{index}].block_number is invalid")
        block = cast(int, raw_block)
        require(block > previous_block, "block numbers must increase")
        previous_block = block
        timestamp = parse_time(event.get("timestamp"), f"events[{index}].timestamp")
        require(previous_time is None or timestamp >= previous_time, "timestamps must not go backwards")
        previous_time = timestamp
        require(event.get("status") == "success", f"events[{index}] is not successful")
        require(event.get("finalized") is True, f"events[{index}] is not finalized")
        selector = event.get("method_selector")
        require(type(selector) is str and SELECTOR_RE.fullmatch(selector) is not None,
                f"events[{index}].method_selector is invalid")
        input_sha256 = event.get("input_sha256")
        require(type(input_sha256) is str and SHA256_RE.fullmatch(input_sha256) is not None,
                f"events[{index}].input_sha256 is invalid")
        for field, expected in anchor.items():
            require(event.get(field) == expected, f"events[{index}].{field} does not match pinned evidence")

    unbond = events[1]
    release = events[2]
    require(type(unbond.get("maturity_seconds")) is int and unbond["maturity_seconds"] >= 90,
            "unbond maturity must be at least 90 seconds")
    unbond_time = parse_time(unbond["timestamp"], "unbond.timestamp")
    unlock_time = parse_time(unbond.get("unlocks_at"), "unbond.unlocks_at")
    require(unlock_time - unbond_time == timedelta(seconds=unbond["maturity_seconds"]),
            "unbond unlock interval mismatch")
    require(parse_time(release["timestamp"], "release.timestamp") >= unlock_time,
            "release happened before unlock")
    validate_amount(unbond.get("amount"), "unbond.amount")
    validate_amount(release.get("amount"), "release.amount")
    require(unbond["amount"] == release["amount"], "release amount does not match unbond")
    require(release.get("swap_observed") is False, "release must not claim a swap")

    liquidity = events[3]
    validate_amount(liquidity.get("lp_receipt"), "liquidity.lp_receipt")

    created = events[4]
    executed = events[5]
    require(created.get("mode") == executed.get("mode") == "auto_sell", "exit mode must be auto_sell")
    require(type(created.get("tranche_id")) is int and created["tranche_id"] > 0,
            "tranche_id is invalid")
    require(executed.get("tranche_id") == created["tranche_id"], "tranche_id mismatch")
    require(type(created.get("maturity_seconds")) is int and created["maturity_seconds"] >= 90,
            "auto-sell maturity must be at least 90 seconds")
    created_time = parse_time(created["timestamp"], "auto_sell.created")
    matures_at = parse_time(created.get("matures_at"), "auto_sell.matures_at")
    require(matures_at - created_time == timedelta(seconds=created["maturity_seconds"]),
            "auto-sell maturity interval mismatch")
    require(parse_time(executed["timestamp"], "auto_sell.executed") >= matures_at,
            "auto-sell executed before maturity")
    validate_amount(created.get("amount"), "auto_sell.amount")
    validate_amount(created.get("keeper_funding"), "auto_sell.keeper_funding")
    validate_amount(executed.get("settlement"), "auto_sell.settlement")
    require(executed.get("external_executor") is True, "external execution evidence missing")
    require(executed.get("final_state") == "filled", "auto-sell final state must be filled")

    return {
        "schema": SCHEMA,
        "chain_id": CHAIN_ID,
        "events": len(events),
        "transactions": len(hashes),
        "minimum_maturity_seconds": min(unbond["maturity_seconds"], created["maturity_seconds"]),
        "final_state": "auto_sell_filled",
        "allocation_status": "UNVERIFIED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.fixture.read_text(encoding="utf-8"))
        print(json.dumps(validate(data), sort_keys=True))
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"flipt_lifecycle_invalid: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
