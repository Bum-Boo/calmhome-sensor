from scripts.simulate_events import (
    SEQUENCES,
    STATE_DOOR_OPENED,
    STATE_FALL,
    STATE_LONG_INACTIVITY,
    STATE_MOVEMENT,
    STATE_PRESENCE,
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
    }


def test_sequence_final_classifications() -> None:
    expected = {
        "normal_activity": STATE_MOVEMENT,
        "room_empty": STATE_STABLE,
        "still_presence": STATE_PRESENCE,
        "fall_suspected": STATE_FALL,
        "long_inactivity": STATE_LONG_INACTIVITY,
        "door_opened": STATE_DOOR_OPENED,
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
