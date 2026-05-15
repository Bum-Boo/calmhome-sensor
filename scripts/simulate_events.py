#!/usr/bin/env python3
"""Emit simulated calmhome-sensor Home Assistant event sequences as JSON."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

STATE_STABLE = "stable"
STATE_PRESENCE = "presence detected"
STATE_MOVEMENT = "movement detected"
STATE_FALL = "fall suspected"
STATE_LONG_INACTIVITY = "long inactivity"
STATE_DOOR_OPENED = "door opened"

DEFAULT_STATES: dict[str, bool] = {
    "presence_detected": False,
    "movement_detected": False,
    "still_presence_detected": False,
    "fall_detected": False,
    "long_inactivity": False,
    "door_opened": False,
}

SEQUENCES: dict[str, list[dict[str, Any]]] = {
    "normal_activity": [
        {"offset_s": 0, "states": {"presence_detected": True}},
        {"offset_s": 3, "states": {"presence_detected": True, "movement_detected": True}},
        {"offset_s": 8, "states": {"presence_detected": True, "movement_detected": True}},
    ],
    "room_empty": [
        {"offset_s": 0, "states": {"presence_detected": True}},
        {"offset_s": 10, "states": {}},
    ],
    "still_presence": [
        {"offset_s": 0, "states": {"presence_detected": True, "movement_detected": True}},
        {"offset_s": 15, "states": {"presence_detected": True, "still_presence_detected": True}},
    ],
    "fall_suspected": [
        {"offset_s": 0, "states": {"presence_detected": True, "movement_detected": True}},
        {"offset_s": 5, "states": {"presence_detected": True, "fall_detected": True}},
        {"offset_s": 35, "states": {"presence_detected": True, "fall_detected": True}},
    ],
    "long_inactivity": [
        {"offset_s": 0, "states": {"presence_detected": True, "still_presence_detected": True}},
        {
            "offset_s": 7200,
            "states": {
                "presence_detected": True,
                "still_presence_detected": True,
                "long_inactivity": True,
            },
        },
    ],
    "door_opened": [
        {"offset_s": 0, "states": {"presence_detected": True}},
        {"offset_s": 4, "states": {"presence_detected": True, "door_opened": True}},
    ],
}


def classify_event(states: dict[str, bool]) -> str:
    """Return the summary room state for a simulated event."""
    normalized = DEFAULT_STATES | states
    occupied = (
        normalized["presence_detected"]
        or normalized["still_presence_detected"]
        or normalized["movement_detected"]
    )

    if normalized["fall_detected"]:
        return STATE_FALL
    if normalized["long_inactivity"] and occupied:
        return STATE_LONG_INACTIVITY
    if normalized["door_opened"] and occupied:
        return STATE_DOOR_OPENED
    if normalized["movement_detected"]:
        return STATE_MOVEMENT
    if occupied:
        return STATE_PRESENCE
    return STATE_STABLE


def build_event(sequence_name: str, index: int, event: dict[str, Any]) -> dict[str, Any]:
    states = DEFAULT_STATES | event.get("states", {})
    return {
        "sequence": sequence_name,
        "index": index,
        "offset_s": event["offset_s"],
        "states": states,
        "room_state": classify_event(states),
    }


def simulate_sequence(sequence_name: str) -> dict[str, Any]:
    """Build a JSON-serializable simulation payload."""
    if sequence_name not in SEQUENCES:
        known = ", ".join(sorted(SEQUENCES))
        raise ValueError(f"Unknown sequence '{sequence_name}'. Known sequences: {known}")

    events = [
        build_event(sequence_name, index, deepcopy(event))
        for index, event in enumerate(SEQUENCES[sequence_name])
    ]

    return {
        "project": "calmhome-sensor",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sequence": sequence_name,
        "event_count": len(events),
        "final_classification": events[-1]["room_state"],
        "events": events,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit simulated Home Assistant event sequences for calmhome-sensor."
    )
    parser.add_argument(
        "sequence",
        nargs="?",
        choices=sorted(SEQUENCES),
        help="Simulated event sequence to emit.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available sequences and exit.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact JSON instead of pretty JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.list:
        print(json.dumps({"sequences": sorted(SEQUENCES)}, indent=2))
        return 0

    if not args.sequence:
        raise SystemExit("sequence is required unless --list is used")

    payload = simulate_sequence(args.sequence)
    indent = None if args.compact else 2
    print(json.dumps(payload, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
