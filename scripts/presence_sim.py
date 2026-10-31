#!/usr/bin/env python3
"""Replay synthetic radar/presence streams through the real CalmHome package logic.

The simulator loads ``homeassistant/packages/calmhome.yaml`` (and the mock
package), renders the package's own Jinja templates with a small emulation of
the Home Assistant template helpers, and applies ``delay_on``/``delay_off``,
``availability`` and the package automations on a simulated clock.

It is a test harness, not a Home Assistant replacement. Helper semantics were
checked against Home Assistant 2026.2 (see ``scripts/ha_runtime_check.py``):

- ``states()`` returns ``unknown`` for entities that do not exist.
- ``as_datetime()`` keeps naive strings naive; ``as_local()`` treats them as local time.
- ``as_timestamp()`` treats naive values as UTC.
- A template sensor with ``device_class: timestamp`` that renders a naive
  datetime becomes ``unknown``.
- ``input_datetime`` without a restored value starts at local midnight.

All sensor data is synthetic. Requires Jinja2 (``python -m pip install Jinja2``).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import jinja2

if __package__ in (None, ""):
    # Allow `python scripts/presence_sim.py` as well as `python -m scripts.presence_sim`.
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_configs import (
    CORE_PACKAGE_PATH,
    ENTITY_MAPPING_EXAMPLE_PATH,
    MOCK_MODE_PACKAGE_PATH,
    PROJECT_ROOT,
    load_yaml_file,
)

INVALID_STATES = ("unknown", "unavailable", "none", "")
DEFAULT_START = datetime(2026, 1, 15, 8, 0, 0)
DEFAULT_TIME_ZONE = "Asia/Seoul"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _seconds(value: Any) -> float:
    """Convert a Home Assistant duration mapping or number to seconds."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        return float(
            value.get("hours", 0) * 3600
            + value.get("minutes", 0) * 60
            + value.get("seconds", 0)
        )
    hours, minutes, seconds = (int(part) for part in str(value).split(":"))
    return float(hours * 3600 + minutes * 60 + seconds)


def _state_text(value: Any) -> str:
    """YAML 1.1 reads unquoted on/off as booleans; Home Assistant compares strings."""
    if value is True:
        return "on"
    if value is False:
        return "off"
    return str(value)


def result_as_boolean(value: Any) -> bool:
    """Mirror homeassistant.helpers.template.result_as_boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    if text in ("true", "yes", "on", "enable"):
        return True
    try:
        return float(text) != 0
    except ValueError:
        return False


@dataclass
class EntityState:
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)
    last_changed: datetime | None = None


@dataclass
class TemplateEntity:
    entity_id: str
    config: dict[str, Any]
    is_binary: bool

    @property
    def delay_on(self) -> float:
        return _seconds(self.config.get("delay_on"))

    @property
    def delay_off(self) -> float:
        return _seconds(self.config.get("delay_off"))


@dataclass
class Automation:
    config: dict[str, Any]

    @property
    def alias(self) -> str:
        return self.config.get("alias", self.config.get("id", "?"))

    @property
    def triggers(self) -> list[dict[str, Any]]:
        return self.config.get("triggers", self.config.get("trigger", []))

    @property
    def conditions(self) -> list[dict[str, Any]]:
        return self.config.get("conditions", self.config.get("condition", []))

    @property
    def actions(self) -> list[dict[str, Any]]:
        return self.config.get("actions", self.config.get("action", []))


class CalmHomeSimulator:
    """Simulated Home Assistant instance with the CalmHome packages loaded."""

    def __init__(
        self,
        root: Path = PROJECT_ROOT,
        *,
        include_mock: bool = True,
        start: datetime = DEFAULT_START,
        time_zone: str = DEFAULT_TIME_ZONE,
        package_overrides: dict[str, Any] | None = None,
    ) -> None:
        self.tz = ZoneInfo(time_zone)
        self.clock = start.replace(tzinfo=self.tz) if start.tzinfo is None else start.astimezone(self.tz)
        self.start = self.clock
        self.entities: dict[str, EntityState] = {}
        self.templates: list[TemplateEntity] = []
        self.automations: list[Automation] = []
        self.pending: dict[str, tuple[datetime, str]] = {}
        self.pending_for: list[tuple[datetime, Automation, dict[str, Any], str, str]] = []
        self.history: list[tuple[float, str, str]] = []
        self.notifications: list[tuple[float, str, str]] = []
        self.logbook: list[tuple[float, str]] = []
        self.errors: list[str] = []
        self._compiled: dict[str, jinja2.Template] = {}
        self.env = self._build_env()

        packages = [load_yaml_file(root / CORE_PACKAGE_PATH)]
        if include_mock:
            packages.append(load_yaml_file(root / MOCK_MODE_PACKAGE_PATH))
        if package_overrides:
            packages.append(package_overrides)
        for package in packages:
            self._load_package(package)
        self._settle()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _load_package(self, package: dict[str, Any]) -> None:
        for object_id, conf in (package.get("input_boolean") or {}).items():
            conf = conf or {}
            self._write(f"input_boolean.{object_id}", "on" if conf.get("initial") else "off")
        for object_id, conf in (package.get("input_select") or {}).items():
            options = conf.get("options", [])
            self._write(f"input_select.{object_id}", str(conf.get("initial", options[0] if options else "")))
        for object_id, conf in (package.get("input_text") or {}).items():
            self._write(f"input_text.{object_id}", str(conf.get("initial", "")))
        for object_id, conf in (package.get("input_number") or {}).items():
            value = conf.get("initial", conf.get("min", 0))
            self._write(f"input_number.{object_id}", str(float(value)))
        for object_id in (package.get("input_datetime") or {}):
            midnight = datetime.combine(self.clock.date(), time(0, 0), tzinfo=self.tz)
            self._set_input_datetime(f"input_datetime.{object_id}", midnight)
        for block in package.get("template") or []:
            for kind in ("binary_sensor", "sensor"):
                for conf in block.get(kind, []) or []:
                    entity_id = f"{kind}.{slugify(conf['name'])}"
                    self.templates.append(TemplateEntity(entity_id, conf, kind == "binary_sensor"))
                    self._write(entity_id, "unknown")
        for conf in package.get("automation") or []:
            self.automations.append(Automation(conf))

    def _build_env(self) -> jinja2.Environment:
        env = jinja2.Environment(undefined=jinja2.ChainableUndefined)
        env.globals.update(
            states=self.states,
            is_state=self.is_state,
            state_attr=self.state_attr,
            now=self.now,
            as_timestamp=self._as_timestamp,
            as_datetime=self._as_datetime,
            as_local=self._as_local,
        )
        env.filters.update(
            int=self._int_filter,
            float=self._float_filter,
            timestamp_custom=self._timestamp_custom,
            as_datetime=self._as_datetime,
            as_local=self._as_local,
            as_timestamp=self._as_timestamp,
        )
        return env

    # ------------------------------------------------------------------
    # Home Assistant template helper emulation
    # ------------------------------------------------------------------
    def now(self) -> datetime:
        return self.clock

    def states(self, entity_id: str) -> str:
        entity = self.entities.get(str(entity_id))
        return entity.state if entity else "unknown"

    def is_state(self, entity_id: str, value: Any) -> bool:
        current = self.states(entity_id)
        if isinstance(value, (list, tuple)):
            return current in value
        return current == value

    def state_attr(self, entity_id: str, name: str) -> Any:
        entity = self.entities.get(str(entity_id))
        return entity.attributes.get(name) if entity else None

    def _parse(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc)
        try:
            return datetime.fromisoformat(str(value).strip())
        except ValueError:
            return None

    def _as_datetime(self, value: Any) -> datetime | None:
        return self._parse(value)

    def _as_local(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=self.tz)
        return value.astimezone(self.tz)

    def _as_timestamp(self, value: Any, default: Any = None) -> float:
        parsed = self._parse(value)
        if parsed is None:
            if default is not None:
                return default
            raise ValueError(f"as_timestamp got invalid input '{value}'")
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()

    @staticmethod
    def _int_filter(value: Any, default: int = 0) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _float_filter(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _timestamp_custom(self, value: float, fmt: str = "%Y-%m-%d %H:%M:%S", local: bool = True) -> str:
        moment = datetime.fromtimestamp(float(value), self.tz if local else timezone.utc)
        return moment.strftime(fmt)

    def render(self, source: Any) -> str:
        source = str(source)
        compiled = self._compiled.get(source)
        if compiled is None:
            compiled = self._compiled[source] = self.env.from_string(source)
        return compiled.render().strip()

    # ------------------------------------------------------------------
    # State handling
    # ------------------------------------------------------------------
    @property
    def elapsed(self) -> float:
        return (self.clock - self.start).total_seconds()

    def _write(self, entity_id: str, state: str, attributes: dict[str, Any] | None = None) -> bool:
        current = self.entities.get(entity_id)
        if current and current.state == state:
            if attributes is not None:
                current.attributes = attributes
            return False
        old = current.state if current else None
        self.entities[entity_id] = EntityState(state, attributes or {}, self.clock)
        self.history.append((self.elapsed, entity_id, state))
        if old is not None:
            self._run_state_triggers(entity_id, old, state)
        return True

    def _set_input_datetime(self, entity_id: str, moment: datetime) -> None:
        local = self._as_local(moment)
        self._write(
            entity_id,
            local.strftime("%Y-%m-%d %H:%M:%S"),
            {"timestamp": local.timestamp(), "has_date": True, "has_time": True},
        )

    def set_state(self, entity_id: str, state: Any) -> None:
        """Set a raw device entity (what ESPHome would report) and settle templates."""
        self._write(entity_id, _state_text(state))
        self._settle()

    def set_states(self, states: dict[str, Any]) -> None:
        for entity_id, state in states.items():
            self._write(entity_id, _state_text(state))
        self._settle()

    def set_input(self, entity_id: str, value: Any) -> None:
        if entity_id.startswith("input_datetime."):
            self._set_input_datetime(entity_id, value)
        elif entity_id.startswith("input_number."):
            self._write(entity_id, str(float(value)))
        else:
            self._write(entity_id, _state_text(value))
        self._settle()

    def _evaluate(self, entity: TemplateEntity) -> str:
        conf = entity.config
        try:
            if "availability" in conf and not result_as_boolean(self.render(conf["availability"])):
                return "unavailable"
            rendered = self.render(conf["state"])
        except Exception as exc:  # noqa: BLE001 - Home Assistant marks the entity unavailable.
            self.errors.append(f"{entity.entity_id}: {exc}")
            return "unavailable"
        if entity.is_binary:
            return "on" if result_as_boolean(rendered) else "off"
        if conf.get("device_class") == "timestamp":
            parsed = self._parse(rendered)
            if parsed is None or parsed.tzinfo is None:
                return "unknown"
            return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
        return rendered

    def _settle(self) -> None:
        for _ in range(50):
            changed = False
            for entity in self.templates:
                target = self._evaluate(entity)
                current = self.states(entity.entity_id)
                delay = 0.0
                if entity.is_binary and target in ("on", "off"):
                    delay = entity.delay_on if target == "on" else entity.delay_off
                pending = self.pending.get(entity.entity_id)
                if target == current:
                    self.pending.pop(entity.entity_id, None)
                    continue
                if delay:
                    if pending is None or pending[1] != target:
                        self.pending[entity.entity_id] = (self.clock + timedelta(seconds=delay), target)
                    continue
                self.pending.pop(entity.entity_id, None)
                changed |= self._write(entity.entity_id, target)
            if not changed:
                return
        self.errors.append("templates did not settle after 50 passes")

    # ------------------------------------------------------------------
    # Automations
    # ------------------------------------------------------------------
    def _trigger_matches(self, trigger: dict[str, Any], entity_id: str, old: str, new: str) -> bool:
        if trigger.get("platform", trigger.get("trigger")) != "state":
            return False
        entity_ids = trigger.get("entity_id", [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        if entity_id not in entity_ids:
            return False
        if "to" in trigger and _state_text(trigger["to"]) != new:
            return False
        if "from" in trigger and _state_text(trigger["from"]) != old:
            return False
        return True

    def _run_state_triggers(self, entity_id: str, old: str, new: str) -> None:
        self.pending_for = [item for item in self.pending_for if not (item[3] == entity_id and item[4] != new)]
        for automation in self.automations:
            for trigger in automation.triggers:
                if not self._trigger_matches(trigger, entity_id, old, new):
                    continue
                hold = _seconds(trigger.get("for"))
                if hold:
                    self.pending_for.append(
                        (self.clock + timedelta(seconds=hold), automation, trigger, entity_id, new)
                    )
                else:
                    self._run_automation(automation)

    def _conditions_pass(self, automation: Automation) -> bool:
        for condition in automation.conditions:
            if condition.get("condition") == "state":
                if self.states(condition["entity_id"]) != _state_text(condition["state"]):
                    return False
            elif condition.get("condition") == "template":
                if not result_as_boolean(self.render(condition["value_template"])):
                    return False
        return True

    def _run_automation(self, automation: Automation) -> None:
        if not self._conditions_pass(automation):
            return
        for action in automation.actions:
            service = action.get("action", action.get("service"))
            data = action.get("data", {}) or {}
            if service == "input_datetime.set_datetime":
                target = action.get("target", {}).get("entity_id")
                if "timestamp" in data:
                    moment = datetime.fromtimestamp(float(self.render(data["timestamp"])), self.tz)
                else:
                    moment = datetime.fromisoformat(self.render(data["datetime"]))
                self._set_input_datetime(target, moment)
            elif service and service.startswith("notify."):
                self.notifications.append((self.elapsed, automation.alias, self.render(data.get("message", ""))))
            elif service == "logbook.log":
                self.logbook.append((self.elapsed, self.render(data.get("message", ""))))
            else:
                self.errors.append(f"{automation.alias}: unsupported action {service}")

    def _run_time_triggers(self, previous: datetime) -> None:
        for automation in self.automations:
            for trigger in automation.triggers:
                if trigger.get("platform", trigger.get("trigger")) != "time":
                    continue
                at = time.fromisoformat(str(trigger["at"]))
                moment = datetime.combine(self.clock.date(), at, tzinfo=self.tz)
                if previous < moment <= self.clock:
                    self._run_automation(automation)

    # ------------------------------------------------------------------
    # Clock
    # ------------------------------------------------------------------
    def advance(self, seconds: float) -> None:
        """Move the simulated clock forward, firing delays, `for:` holds and minute ticks."""
        end = self.clock + timedelta(seconds=seconds)
        while True:
            due = [moment for moment, _ in self.pending.values()]
            due += [item[0] for item in self.pending_for]
            next_minute = (self.clock + timedelta(minutes=1)).replace(second=0, microsecond=0)
            due.append(next_minute)
            moment = min(min(due), end)
            previous = self.clock
            self.clock = moment
            for entity_id, (when, target) in list(self.pending.items()):
                if when <= self.clock:
                    del self.pending[entity_id]
                    self._write(entity_id, target)
            ready = [item for item in self.pending_for if item[0] <= self.clock]
            self.pending_for = [item for item in self.pending_for if item[0] > self.clock]
            for _, automation, _, entity_id, state in ready:
                if self.states(entity_id) == state:
                    self._run_automation(automation)
            self._run_time_triggers(previous)
            self._settle()
            if self.clock >= end:
                return

    def seen(self, entity_id: str, state: str, since: float = 0.0) -> bool:
        return any(t >= since and e == entity_id and s == state for t, e, s in self.history)


# ----------------------------------------------------------------------
# Synthetic streams
# ----------------------------------------------------------------------
LOGICAL_RAW_STATES = ("presence_detected", "movement_detected", "still_presence_detected", "fall_detected", "door_opened", "sensor_online")


def load_mapping(root: Path = PROJECT_ROOT) -> dict[str, str]:
    return dict(load_yaml_file(root / ENTITY_MAPPING_EXAMPLE_PATH)["logical_entities"])


def raw(**logical: Any) -> dict[str, Any]:
    """Build a frame of logical sensor readings; unspecified radar readings default to off."""
    frame: dict[str, Any] = {name: "off" for name in LOGICAL_RAW_STATES if name != "sensor_online"}
    frame["sensor_online"] = "on"
    frame.update(logical)
    return frame


def offline() -> dict[str, Any]:
    """Every ESPHome entity becomes unavailable when the device drops off the network."""
    return {name: "unavailable" for name in LOGICAL_RAW_STATES if name != "door_opened"}


def flicker(start: float, end: float, period: float, on: dict[str, Any], off: dict[str, Any]) -> list[tuple[float, dict[str, Any]]]:
    frames = []
    moment, high = start, True
    while moment < end:
        frames.append((moment, on if high else off))
        moment += period
        high = not high
    return frames


# Each stream is a list of (offset_seconds, logical readings). Offsets are absolute.
STREAMS: dict[str, list[tuple[float, dict[str, Any]]]] = {
    "empty_room": [
        (0, raw()),
    ],
    "one_person_still": [
        (0, raw()),
        (60, raw(presence_detected="on", movement_detected="on")),
        (90, raw(presence_detected="on", still_presence_detected="on")),
    ],
    "continuous_movement": [
        (0, raw()),
        (60, raw(presence_detected="on", movement_detected="on")),
    ],
    "fall_like": [
        (0, raw(presence_detected="on", movement_detected="on")),
        (30, raw(presence_detected="on", fall_detected="on")),
        (150, raw(presence_detected="on", movement_detected="on")),
    ],
    "fall_blip": [
        (0, raw(presence_detected="on", still_presence_detected="on")),
        (30, raw(presence_detected="on", still_presence_detected="on", fall_detected="on")),
        (40, raw(presence_detected="on", still_presence_detected="on")),
    ],
    "sensor_dropout": [
        (0, raw(presence_detected="on", movement_detected="on")),
        (30, raw(presence_detected="on", still_presence_detected="on")),
        (600, offline()),
        (900, raw(presence_detected="on", still_presence_detected="on")),
    ],
    "noisy_readings": [
        (0, raw()),
        *flicker(
            10,
            40,
            1,
            raw(presence_detected="on", movement_detected="on"),
            raw(),
        ),
        (40, raw()),
    ],
    "conflicting_fall_without_presence": [
        (0, raw()),
        (10, raw(fall_detected="on")),
    ],
    "fall_sensor_offline": [
        (0, raw(presence_detected="on", movement_detected="on")),
        (30, raw(presence_detected="on", movement_detected="on", fall_detected="unavailable")),
    ],
    "door_while_occupied": [
        (0, raw(presence_detected="on", still_presence_detected="on")),
        (20, raw(presence_detected="on", still_presence_detected="on", door_opened="on")),
    ],
}


def replay(
    stream: list[tuple[float, dict[str, Any]]],
    *,
    duration: float | None = None,
    sim: CalmHomeSimulator | None = None,
    on_frame: Callable[[CalmHomeSimulator, float], None] | None = None,
) -> CalmHomeSimulator:
    """Replay a synthetic stream into a simulator (real mode, example entity mapping).

    Frames later than ``duration`` are not applied, so a stream can be stopped part-way.
    """
    sim = sim or CalmHomeSimulator()
    mapping = load_mapping()
    base = sim.elapsed
    for offset, frame in sorted(stream, key=lambda item: item[0]):
        if duration is not None and offset > duration:
            break
        target = base + offset
        if target > sim.elapsed:
            sim.advance(target - sim.elapsed)
        sim.set_states({mapping[name]: value for name, value in frame.items()})
        if on_frame:
            on_frame(sim, offset)
    if duration is not None and base + duration > sim.elapsed:
        sim.advance(base + duration - sim.elapsed)
    return sim


SUMMARY_ENTITIES = (
    "sensor.calmhome_room_state",
    "binary_sensor.calmhome_presence_confirmed",
    "binary_sensor.calmhome_movement_confirmed",
    "binary_sensor.calmhome_fall_suspected",
    "binary_sensor.calmhome_long_inactivity",
    "binary_sensor.calmhome_sensor_offline",
    "sensor.calmhome_last_activity_time",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay a synthetic CalmHome sensor stream through the package templates.")
    parser.add_argument("stream", nargs="?", choices=sorted(STREAMS), help="Synthetic stream to replay.")
    parser.add_argument("--duration", type=float, default=None, help="Seconds to simulate (default: last frame + 5 min).")
    parser.add_argument("--list", action="store_true", help="List available streams and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list or not args.stream:
        print(json.dumps({"streams": sorted(STREAMS)}, indent=2))
        return 0
    stream = STREAMS[args.stream]
    duration = args.duration if args.duration is not None else max(offset for offset, _ in stream) + 300
    sim = replay(stream, duration=duration)
    payload = {
        "stream": args.stream,
        "simulated_seconds": sim.elapsed,
        "final_states": {entity_id: sim.states(entity_id) for entity_id in SUMMARY_ENTITIES},
        "room_state_timeline": [
            {"t": t, "state": s} for t, e, s in sim.history if e == "sensor.calmhome_room_state"
        ],
        "notifications": [{"t": t, "automation": a, "message": m} for t, a, m in sim.notifications],
        "logbook": [{"t": t, "message": m} for t, m in sim.logbook],
        "template_errors": sim.errors,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
