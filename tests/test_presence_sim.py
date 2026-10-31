"""Replay synthetic radar streams through the real CalmHome package templates."""

from datetime import timedelta, timezone

import pytest

pytest.importorskip("jinja2")

from scripts.presence_sim import STREAMS, CalmHomeSimulator, load_mapping, replay  # noqa: E402

ROOM = "sensor.calmhome_room_state"
FALL = "binary_sensor.calmhome_fall_suspected"
MOVEMENT = "binary_sensor.calmhome_movement_confirmed"
PRESENCE = "binary_sensor.calmhome_presence_confirmed"
FALL_ALERT = "CalmHome Fall Suspected Notification"


def alerts(sim: CalmHomeSimulator, alias: str) -> list[float]:
    return [t for t, name, _ in sim.notifications if name == alias]


def test_simulator_loads_package_without_template_errors() -> None:
    sim = CalmHomeSimulator()

    assert sim.errors == []
    assert sim.states(ROOM) != "unknown"
    assert sim.states("input_text.calmhome_entity_presence_detected") == load_mapping()["presence_detected"]


def test_every_stream_replays_without_template_errors() -> None:
    for name, stream in STREAMS.items():
        sim = replay(stream, duration=max(offset for offset, _ in stream) + 600)
        assert sim.errors == [], name


def test_empty_room_is_stable_with_no_alerts() -> None:
    sim = replay(STREAMS["empty_room"], duration=3 * 3600)

    assert sim.states(ROOM) == "stable"
    assert sim.states(PRESENCE) == "off"
    assert sim.notifications == []


def test_one_person_still_shows_presence_without_movement() -> None:
    sim = replay(STREAMS["one_person_still"], duration=600)

    assert sim.states(PRESENCE) == "on"
    assert sim.states(MOVEMENT) == "off"
    assert sim.states(ROOM) == "presence detected"
    assert sim.notifications == []


def test_movement_is_debounced_before_it_is_shown() -> None:
    sim = replay(STREAMS["one_person_still"], duration=61)
    assert sim.states(MOVEMENT) == "off"

    sim.advance(2)
    assert sim.states(MOVEMENT) == "on"
    assert sim.states(ROOM) == "movement detected"


def test_noisy_sub_second_movement_never_confirms_movement() -> None:
    sim = replay(STREAMS["noisy_readings"], duration=120)

    assert not sim.seen(MOVEMENT, "on")
    assert not sim.seen(ROOM, "movement detected")
    assert sim.states(ROOM) == "stable"


def test_fall_like_pattern_alerts_once_after_recheck_delay() -> None:
    sim = replay(STREAMS["fall_like"], duration=59)
    assert sim.states(FALL) == "off"
    assert sim.states(ROOM) != "fall suspected"

    sim.advance(1)
    assert sim.states(FALL) == "on"
    assert sim.states(ROOM) == "fall suspected"

    sim = replay(STREAMS["fall_like"], duration=600)
    assert alerts(sim, FALL_ALERT) == [60.0]
    assert sim.states(FALL) == "off"


def test_short_fall_blip_is_not_reported() -> None:
    sim = replay(STREAMS["fall_blip"], duration=600)

    assert not sim.seen(FALL, "on")
    assert alerts(sim, FALL_ALERT) == []


def test_conflicting_fall_without_presence_still_reports_fall() -> None:
    sim = replay(STREAMS["conflicting_fall_without_presence"], duration=60)

    assert sim.states(PRESENCE) == "off"
    assert sim.states(ROOM) == "fall suspected"
    assert len(alerts(sim, FALL_ALERT)) == 1


def test_door_opened_while_occupied_writes_logbook_entry() -> None:
    sim = replay(STREAMS["door_while_occupied"], duration=60)

    assert sim.states(ROOM) == "door opened"
    assert [message for _, message in sim.logbook] == ["Door opened while the room was occupied."]


def test_mock_scenarios_drive_room_state() -> None:
    expected = {
        "room_empty": "stable",
        "presence_detected": "presence detected",
        "movement_detected": "movement detected",
        "still_presence": "presence detected",
        "fall_suspected": "fall suspected",
        "long_inactivity": "long inactivity",
        "door_opened": "door opened",
    }
    for scenario, room_state in expected.items():
        sim = CalmHomeSimulator()
        sim.set_input("input_boolean.calmhome_mock_mode", "on")
        sim.set_input("input_select.calmhome_mock_scenario", scenario)
        sim.advance(31)
        assert sim.states(ROOM) == room_state, scenario
        assert sim.errors == []


LONG = "binary_sensor.calmhome_long_inactivity"
LAST_ACTIVITY = "sensor.calmhome_last_activity_time"
LONG_ALERT = "CalmHome Long Inactivity Notification"


def test_last_activity_time_is_a_timezone_aware_timestamp() -> None:
    sim = replay(STREAMS["one_person_still"], duration=120)

    assert sim.states(LAST_ACTIVITY) not in ("unknown", "unavailable")
    assert sim.states(LAST_ACTIVITY).endswith("+00:00")


def test_still_person_past_threshold_raises_long_inactivity() -> None:
    sim = replay(STREAMS["one_person_still"], duration=90 + 120 * 60 - 60)
    assert sim.states(LONG) == "off"

    sim.advance(2 * 60)
    assert sim.states(LONG) == "on"
    assert sim.states(ROOM) == "long inactivity"

    sim.advance(6 * 60)
    assert len(alerts(sim, LONG_ALERT)) == 1


def test_mock_long_inactivity_shows_last_activity_time() -> None:
    sim = CalmHomeSimulator()
    sim.set_input("input_boolean.calmhome_mock_mode", "on")
    sim.set_input("input_select.calmhome_mock_scenario", "long_inactivity")

    assert sim.states(LAST_ACTIVITY) not in ("unknown", "unavailable")
    assert sim.states(ROOM) == "long inactivity"


def test_continuous_movement_is_never_long_inactivity() -> None:
    sim = replay(STREAMS["continuous_movement"], duration=3 * 3600)

    assert sim.states(ROOM) == "movement detected"
    assert not sim.seen(LONG, "on")
    assert alerts(sim, LONG_ALERT) == []


def test_inactivity_is_measured_from_when_movement_stopped() -> None:
    # Walks for an hour, then sits still: the timer starts when movement ends.
    stream = STREAMS["continuous_movement"] + [(3660, {"movement_detected": "off", "still_presence_detected": "on"})]
    sim = replay(stream, duration=3660 + 110 * 60)
    assert sim.states(LONG) == "off"

    sim.advance(15 * 60)
    assert sim.states(LONG) == "on"


def test_movement_ending_counts_as_activity_without_still_sensor() -> None:
    # Sensors without a still-target entity: only presence and movement are reported.
    stream = STREAMS["continuous_movement"] + [(3 * 3600, {"movement_detected": "off"})]
    sim = replay(stream, duration=3 * 3600 + 30 * 60)

    assert sim.states(PRESENCE) == "on"
    assert sim.states(LONG) == "off"
    assert sim.states(ROOM) == "presence detected"


OFFLINE = "binary_sensor.calmhome_sensor_offline"
OFFLINE_ALERT = "CalmHome Sensor Offline Notification"


def test_sensor_dropout_is_shown_as_offline_not_stable() -> None:
    sim = replay(STREAMS["sensor_dropout"], duration=899)

    assert sim.states(OFFLINE) == "on"
    assert sim.states(ROOM) == "sensor offline"
    assert not sim.seen(ROOM, "stable", since=600)
    assert alerts(sim, OFFLINE_ALERT) == [780.0]

    sim = replay(STREAMS["sensor_dropout"], duration=1200)
    assert sim.states(OFFLINE) == "off"
    assert sim.states(ROOM) == "presence detected"


def test_short_dropout_does_not_notify() -> None:
    stream = STREAMS["sensor_dropout"][:3] + [(700, STREAMS["sensor_dropout"][3][1])]
    sim = replay(stream, duration=1200)

    assert sim.seen(ROOM, "sensor offline")
    assert alerts(sim, OFFLINE_ALERT) == []


def test_reconnect_after_dropout_is_not_counted_as_activity() -> None:
    sim = replay(STREAMS["sensor_dropout"], duration=1200)

    # The reconnect at t=900 is not activity; inactivity is counted from the
    # start of the outage (t=600), because nothing is known about the outage.
    assert sim.states(LAST_ACTIVITY) == (sim.start + timedelta(seconds=600)).astimezone(timezone.utc).isoformat()
    sim.advance(600 + 120 * 60 - sim.elapsed + 60)
    assert sim.states(LONG) == "on"


def test_unavailable_fall_sensor_is_reported_offline() -> None:
    sim = replay(STREAMS["fall_sensor_offline"], duration=60)

    assert sim.states("binary_sensor.calmhome_fall_signal") == "unavailable"
    assert sim.states(OFFLINE) == "on"
    assert sim.states(ROOM) == "sensor offline"


def test_unmapped_or_never_connected_sensor_is_not_shown_as_stable() -> None:
    sim = CalmHomeSimulator()

    assert sim.states(OFFLINE) == "on"
    assert sim.states(ROOM) == "sensor offline"


def test_missing_optional_door_sensor_does_not_mark_sensor_offline() -> None:
    # No door contact installed: its entity simply does not exist.
    stream = [(0, {k: v for k, v in STREAMS["one_person_still"][2][1].items() if k != "door_opened"})]
    sim = replay(stream, duration=60)

    assert sim.states("binary_sensor.calmhome_door_opened") == "unknown"
    assert sim.states(OFFLINE) == "off"
    assert sim.states(ROOM) == "presence detected"


def test_fall_reported_before_dropout_is_kept_on_screen() -> None:
    stream = STREAMS["fall_like"][:2] + [(70, {"sensor_online": "off", "presence_detected": "unavailable", "fall_detected": "unavailable"})]
    sim = replay(stream, duration=80)

    assert alerts(sim, FALL_ALERT) == [60.0]
    assert sim.states(ROOM) == "fall suspected"
    sim.advance(60)
    assert sim.states(ROOM) == "sensor offline"


def test_mock_sensor_offline_scenario() -> None:
    sim = CalmHomeSimulator()
    sim.set_input("input_boolean.calmhome_mock_mode", "on")
    sim.set_input("input_select.calmhome_mock_scenario", "sensor_offline")
    sim.advance(4 * 60)

    assert sim.states(OFFLINE) == "on"
    assert sim.states(ROOM) == "sensor offline"
    assert len(alerts(sim, OFFLINE_ALERT)) == 1


def test_noisy_presence_flicker_counts_as_activity() -> None:
    # Documented limitation: presence flicker (fans, curtains) refreshes the activity time.
    storage = "input_datetime.calmhome_last_activity_time_storage"
    before = replay(STREAMS["noisy_readings"], duration=9).states(storage)
    after = replay(STREAMS["noisy_readings"], duration=60).states(storage)

    assert after != before


def test_cli_replays_a_stream_as_json() -> None:
    import json
    import subprocess
    import sys

    from scripts.validate_configs import PROJECT_ROOT

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "presence_sim.py"), "sensor_dropout"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)

    assert payload["template_errors"] == []
    assert "sensor offline" in [item["state"] for item in payload["room_state_timeline"]]


def boot_with(frame: dict, **kwargs) -> CalmHomeSimulator:
    """Start Home Assistant while the device already reports these readings (unknown -> on)."""
    mapping = load_mapping()
    return CalmHomeSimulator(initial_states={mapping[k]: v for k, v in frame.items()}, **kwargs)


def test_boot_with_person_already_still_does_not_alert_immediately() -> None:
    # Fresh install in the afternoon: the activity helper starts at local midnight.
    from datetime import datetime

    still = STREAMS["one_person_still"][2][1]
    sim = boot_with(still, start=datetime(2026, 1, 15, 14, 0, 0))
    assert sim.states(PRESENCE) == "on"
    assert sim.states(LONG) == "off"

    sim.advance(60 * 60)
    assert sim.states(LONG) == "off"
    assert alerts(sim, LONG_ALERT) == []
    # Still nobody moved: after the threshold counted from start-up it is reported.
    sim.advance(65 * 60)
    assert sim.states(LONG) == "on"


def test_entry_during_dropout_is_not_judged_by_stale_activity_time() -> None:
    # Room empty for hours, sensor offline, someone enters and sits down meanwhile.
    stream = [
        (0, STREAMS["empty_room"][0][1]),
        (5 * 3600, {name: "unavailable" for name in ("presence_detected", "movement_detected", "still_presence_detected", "fall_detected", "sensor_online")}),
        (5 * 3600 + 300, STREAMS["one_person_still"][2][1]),
    ]
    sim = replay(stream, duration=5 * 3600 + 400)

    assert sim.states(PRESENCE) == "on"
    assert sim.states(LONG) == "off"
    assert sim.states(ROOM) == "presence detected"

    # The outage counts toward inactivity: alert 120 min after the dropout started.
    sim.advance(5 * 3600 + 121 * 60 - sim.elapsed)
    assert sim.states(LONG) == "on"


def test_long_inactivity_is_not_hidden_by_offline_fall_sensor() -> None:
    sim = replay(STREAMS["one_person_still"], duration=90 + 125 * 60)
    assert sim.states(LONG) == "on"

    sim.set_state(load_mapping()["fall_detected"], "unavailable")
    assert sim.states(OFFLINE) == "on"
    assert sim.states(ROOM) == "long inactivity"
