import itertools

import pytest

from scripts.simulate_events import (
    SEQUENCES,
    STATE_DOOR_OPENED,
    STATE_FALL,
    STATE_LONG_INACTIVITY,
    STATE_MOVEMENT,
    STATE_PRESENCE,
    STATE_SENSOR_OFFLINE,
    STATE_STABLE,
    classify_event,
    simulate_sequence,
)


def test_all_expected_sequences_exist() -> None:
    assert set(SEQUENCES) == {
        "normal_activity",
        "room_empty",
        "still_presence",
        "fall_suspected",
        "long_inactivity",
        "door_opened",
        "sensor_dropout",
    }


def test_sequence_final_classifications() -> None:
    expected = {
        "normal_activity": STATE_MOVEMENT,
        "room_empty": STATE_STABLE,
        "still_presence": STATE_PRESENCE,
        "fall_suspected": STATE_FALL,
        "long_inactivity": STATE_LONG_INACTIVITY,
        "door_opened": STATE_DOOR_OPENED,
        "sensor_dropout": STATE_SENSOR_OFFLINE,
    }

    for sequence, state in expected.items():
        payload = simulate_sequence(sequence)
        assert payload["final_classification"] == state
        assert payload["event_count"] == len(payload["events"])


def test_classification_priority() -> None:
    assert classify_event({"presence_detected": True, "fall_detected": True}) == STATE_FALL
    assert (
        classify_event(
            {
                "presence_detected": True,
                "movement_detected": True,
                "door_opened": True,
            }
        )
        == STATE_DOOR_OPENED
    )
    assert classify_event({"movement_detected": True}) == STATE_MOVEMENT


def test_sensor_offline_is_classified_after_fall() -> None:
    assert classify_event({"presence_detected": True, "sensor_offline": True}) == STATE_SENSOR_OFFLINE
    assert classify_event({"sensor_offline": True, "fall_detected": True}) == STATE_FALL
    assert simulate_sequence("sensor_dropout")["final_classification"] == STATE_SENSOR_OFFLINE


def test_classify_event_matches_package_room_state_template() -> None:
    pytest.importorskip("jinja2")
    from scripts.presence_sim import CalmHomeSimulator, EntityState

    sim = CalmHomeSimulator()
    room_state = next(t for t in sim.templates if t.entity_id == "sensor.calmhome_room_state")
    names = ["presence_detected", "movement_detected", "fall_detected", "long_inactivity", "door_opened", "sensor_offline"]

    for combo in itertools.product([False, True], repeat=len(names)):
        states = dict(zip(names, combo))
        if states["long_inactivity"] and not (states["presence_detected"] or states["movement_detected"]):
            continue  # The package only raises long inactivity while presence is confirmed.
        forced = {
            "binary_sensor.calmhome_fall_suspected": states["fall_detected"],
            "binary_sensor.calmhome_sensor_offline": states["sensor_offline"],
            "binary_sensor.calmhome_long_inactivity": states["long_inactivity"],
            "binary_sensor.calmhome_door_opened_signal": states["door_opened"],
            "binary_sensor.calmhome_movement_confirmed": states["movement_detected"],
            "binary_sensor.calmhome_presence_confirmed": states["presence_detected"] or states["movement_detected"],
        }
        for entity_id, value in forced.items():
            sim.entities[entity_id] = EntityState("on" if value else "off")

        assert sim.render(room_state.config["state"]) == classify_event(states), states
