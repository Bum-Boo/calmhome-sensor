#!/usr/bin/env python3
"""Boot a real Home Assistant core in-process with the CalmHome packages and check key states.

This cross-checks the pure-Python simulator (``scripts/presence_sim.py``)
against Home Assistant itself. It needs the ``homeassistant`` package, which is
large, so install it in a separate virtual environment:

    python -m venv .venv-ha
    .venv-ha/bin/python -m pip install homeassistant
    .venv-ha/bin/python scripts/ha_runtime_check.py

It uses a temporary config directory, synthetic entity states only, no network
integrations and no notifier (notify.notify calls are captured by a stub
service). It takes about 10 seconds because it waits for real debounce delays.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIGURATION = """\
homeassistant:
  name: CalmHome synthetic check
  latitude: 0
  longitude: 0
  elevation: 0
  unit_system: metric
  time_zone: Asia/Seoul
  packages: !include_dir_named packages
"""

ROOM = "sensor.calmhome_room_state"
LONG = "binary_sensor.calmhome_long_inactivity"
OFFLINE = "binary_sensor.calmhome_sensor_offline"
LAST = "sensor.calmhome_last_activity_time"
STORAGE = "input_datetime.calmhome_last_activity_time_storage"
DEVICE = {
    "presence": "binary_sensor.calmhome_presence_detected",
    "movement": "binary_sensor.calmhome_movement_detected",
    "still": "binary_sensor.calmhome_still_presence_detected",
    "fall": "binary_sensor.calmhome_fall_detected",
    "online": "binary_sensor.calmhome_sensor_online",
}


async def run(config_dir: Path) -> list[tuple[str, bool, str]]:
    from homeassistant import bootstrap, runner
    from homeassistant.exceptions import HomeAssistantError

    hass = await bootstrap.async_setup_hass(
        runner.RuntimeConfig(config_dir=str(config_dir), skip_pip=True, recovery_mode=False, safe_mode=False)
    )
    notifications: list[str] = []

    async def fake_notify(call) -> None:  # call: Home Assistant ServiceCall
        notifications.append(call.data.get("message", ""))

    hass.services.async_register("notify", "notify", fake_notify)
    await hass.async_start()
    await hass.async_block_till_done()

    results: list[tuple[str, bool, str]] = []
    room_history: list[str] = []

    def on_change(event) -> None:  # event: Home Assistant Event
        if event.data["entity_id"] == ROOM and event.data["new_state"] is not None:
            room_history.append(event.data["new_state"].state)

    hass.bus.async_listen("state_changed", on_change)

    def state(entity_id: str) -> str | None:
        current = hass.states.get(entity_id)
        return current.state if current else None

    def check(name: str, ok: bool) -> None:
        results.append((name, ok, f"room={state(ROOM)} offline={state(OFFLINE)} long={state(LONG)} last={state(LAST)}"))

    async def device(**values: str) -> None:
        for key, value in values.items():
            hass.states.async_set(DEVICE[key], value)
        await hass.async_block_till_done()
        await asyncio.sleep(0.2)
        await hass.async_block_till_done()

    async def last_activity(seconds_ago: float) -> None:
        await hass.services.async_call(
            "input_datetime", "set_datetime", {"entity_id": STORAGE, "timestamp": time.time() - seconds_ago}, blocking=True
        )
        await hass.services.async_call("homeassistant", "update_entity", {"entity_id": [LAST, LONG]}, blocking=True)
        await hass.async_block_till_done()

    check("room state sensor exists", state(ROOM) is not None)
    check("never-connected sensor is reported offline", state(ROOM) == "sensor offline")

    await device(online="on", presence="off", movement="off", still="off", fall="off")
    check("empty room is stable", state(ROOM) == "stable")

    await device(presence="on", still="on")
    check("still person shows presence", state(ROOM) == "presence detected")
    check("last activity is a valid timestamp", state(LAST) not in (None, "unknown", "unavailable"))

    await last_activity(3 * 3600)
    check("still person past threshold is long inactivity", state(LONG) == "on" and state(ROOM) == "long inactivity")

    await device(movement="on")
    await hass.services.async_call("homeassistant", "update_entity", {"entity_id": [LONG]}, blocking=True)
    await hass.async_block_till_done()
    check("movement clears long inactivity", state(LONG) == "off")
    await asyncio.sleep(2.5)
    await hass.async_block_till_done()
    check("movement is shown after the 2 s debounce", state(ROOM) == "movement detected")

    await device(movement="off")
    await asyncio.sleep(2.5)
    await last_activity(3 * 3600)
    stored = state(STORAGE)
    await device(online="off", presence="unavailable", movement="unavailable", still="unavailable", fall="unavailable")
    check("dropout is sensor offline, not stable", state(ROOM) == "sensor offline")
    await device(online="on", presence="on", movement="off", still="on", fall="off")
    check("reconnect is not recorded as activity", state(STORAGE) == stored)
    check("long inactivity survives a dropout", state(LONG) == "on")

    await device(fall="unavailable")
    check("unavailable fall sensor is sensor offline", state(OFFLINE) == "on" and state(ROOM) == "sensor offline")
    await device(fall="off")

    await device(presence="off", movement="off", still="off")
    await asyncio.sleep(2.5)
    await last_activity(5 * 3600)
    room_history.clear()
    await device(presence="on", movement="on")
    check("entering after a long absence never flashes long inactivity", "long inactivity" not in room_history)

    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": "input_boolean.calmhome_mock_mode"}, blocking=True
    )
    async def scenario(option: str) -> bool:
        try:
            await hass.services.async_call(
                "input_select",
                "select_option",
                {"entity_id": "input_select.calmhome_mock_scenario", "option": option},
                blocking=True,
            )
        except HomeAssistantError:
            return False
        await hass.async_block_till_done()
        return True

    check("mock sensor_offline scenario", await scenario("sensor_offline") and state(ROOM) == "sensor offline")
    check(
        "mock long_inactivity scenario",
        await scenario("long_inactivity") and state(ROOM) == "long inactivity" and state(LAST) != "unknown",
    )

    await hass.async_stop()
    return results


def main() -> int:
    try:
        import homeassistant  # noqa: F401
    except ImportError:
        print("homeassistant is not installed; see the module docstring.", file=sys.stderr)
        return 2

    config_dir = Path(tempfile.mkdtemp(prefix="calmhome-ha-"))
    (config_dir / "packages").mkdir()
    (config_dir / "configuration.yaml").write_text(CONFIGURATION, encoding="utf-8")
    for name in ("calmhome.yaml", "calmhome_mock.yaml"):
        shutil.copy(PROJECT_ROOT / "homeassistant" / "packages" / name, config_dir / "packages" / name)
    try:
        results = asyncio.run(run(config_dir))
    finally:
        shutil.rmtree(config_dir, ignore_errors=True)

    failed = 0
    for name, ok, detail in results:
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  ({detail})"))
    print(f"{len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
