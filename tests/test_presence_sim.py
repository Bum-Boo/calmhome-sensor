"""Replay synthetic radar streams through the real CalmHome package templates."""

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
