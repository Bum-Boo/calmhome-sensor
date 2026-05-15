# Runtime Test Plan

Run these tests in Home Assistant after installing `calmhome.yaml` and `calmhome_mock.yaml`.

Use this result format for each test:

```text
Pass/Fail:
Notes:
Date:
Tester:
```

## 1. Normal Entry

Setup:

- Disable mock mode.
- Start with the room empty.
- Walk into the room normally.

Expected Home Assistant state:

- `binary_sensor.calmhome_presence_confirmed` turns on.
- `sensor.calmhome_room_state` becomes `presence detected` or `movement detected`.

Expected dashboard result:

- Presence shows on.
- Room state updates within a few seconds.

Expected notification behavior:

- No urgent notification.

Pass/Fail:

## 2. Room Empty

Setup:

- Disable mock mode.
- Leave the room and wait for the sensor timeout.

Expected Home Assistant state:

- `binary_sensor.calmhome_presence_confirmed` turns off.
- `binary_sensor.calmhome_movement_confirmed` turns off.
- `sensor.calmhome_room_state` becomes `stable`.

Expected dashboard result:

- Presence and movement show off.
- Room state shows stable.

Expected notification behavior:

- No notification.

Pass/Fail:

## 3. Seated Still Presence

Setup:

- Disable mock mode.
- Sit still in the monitored area.

Expected Home Assistant state:

- `binary_sensor.calmhome_presence_confirmed` remains on.
- `binary_sensor.calmhome_still_presence_signal` turns on if the sensor supports it.
- `sensor.calmhome_room_state` becomes `presence detected`.

Expected dashboard result:

- Presence shows on.
- Movement may be off.

Expected notification behavior:

- No notification unless long inactivity threshold is intentionally exceeded.

Pass/Fail:

## 4. Walking Movement

Setup:

- Disable mock mode.
- Walk through the normal activity area for at least 5 seconds.

Expected Home Assistant state:

- `binary_sensor.calmhome_movement_signal` turns on.
- `binary_sensor.calmhome_movement_confirmed` turns on after the 2 second debounce.
- `sensor.calmhome_room_state` becomes `movement detected`.

Expected dashboard result:

- Movement shows on after debounce.

Expected notification behavior:

- No notification.

Pass/Fail:

## 5. Simulated Fall Event

Setup:

- Enable mock mode.
- Select `fall_suspected`.
- Wait at least 30 seconds.

Expected Home Assistant state:

- `binary_sensor.calmhome_fall_signal` turns on immediately.
- `binary_sensor.calmhome_fall_suspected` turns on after the 30 second recheck delay.
- `sensor.calmhome_room_state` becomes `fall suspected`.

Expected dashboard result:

- Fall suspected shows on after the delay.

Expected notification behavior:

- Fall suspected notification is sent after the delay.

Pass/Fail:

## 6. Long Inactivity

Setup:

- Enable mock mode.
- Select `long_inactivity`.

Expected Home Assistant state:

- `binary_sensor.calmhome_presence_confirmed` is on.
- `binary_sensor.calmhome_long_inactivity` is on.
- `sensor.calmhome_room_state` becomes `long inactivity`.

Expected dashboard result:

- Presence and long inactivity show on.

Expected notification behavior:

- Long inactivity notification is sent after the automation delay.

Pass/Fail:

## 7. Door Opened While Occupied

Setup:

- Enable mock mode.
- Select `door_opened`.

Expected Home Assistant state:

- `binary_sensor.calmhome_presence_confirmed` is on.
- `binary_sensor.calmhome_door_opened_signal` is on.
- `sensor.calmhome_room_state` becomes `door opened`.

Expected dashboard result:

- Door signal appears in diagnostics when diagnostics are enabled.
- Room state shows door opened.

Expected notification behavior:

- The package writes a logbook event by default.

Pass/Fail:

## 8. Sensor Offline

Setup:

- Disable mock mode.
- Turn off or unplug the ESPHome sensor.
- Wait at least 3 minutes.

Expected Home Assistant state:

- `binary_sensor.calmhome_sensor_online_signal` turns off.
- `binary_sensor.calmhome_sensor_offline` turns on.

Expected dashboard result:

- Sensor offline shows on in Setup Controls.

Expected notification behavior:

- Sensor offline notification is sent after the automation delay.

Pass/Fail:
