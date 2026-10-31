# Install In Home Assistant

This guide assumes Home Assistant OS, Home Assistant Green, or another setup where you can edit files under the Home Assistant config directory.

## 1. Copy Package Files

Copy these files into your Home Assistant packages directory:

- `homeassistant/packages/calmhome.yaml` -> `/config/packages/calmhome.yaml`
- `homeassistant/packages/calmhome_mock.yaml` -> `/config/packages/calmhome_mock.yaml`

Create `/config/packages/` if it does not exist.

## 2. Enable Packages

In `/config/configuration.yaml`, add packages if you do not already have them enabled:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

If you already have a `homeassistant:` block, add only the `packages:` line inside that existing block.

## 3. Reload Or Restart

1. Go to Home Assistant Developer Tools > YAML.
2. Run Check Configuration.
3. If the check passes, reload YAML where available.
4. If package helpers or template entities do not appear, restart Home Assistant.

Home Assistant packages often require a restart when new helper domains are added.

## 4. Check Entities

Go to Developer Tools > States and search for `calmhome`.

Expected core entities include:

- `sensor.calmhome_room_state`
- `binary_sensor.calmhome_presence_confirmed`
- `binary_sensor.calmhome_movement_confirmed`
- `binary_sensor.calmhome_fall_suspected`
- `binary_sensor.calmhome_long_inactivity`
- `sensor.calmhome_last_activity_time`
- `binary_sensor.calmhome_sensor_offline`
- `input_boolean.calmhome_mock_mode`
- `input_select.calmhome_mock_scenario`

Until real sensors are mapped and online, `sensor.calmhome_room_state` shows `sensor offline`. This is expected and means CalmHome cannot see a working sensor yet.

## 5. Map Real Sensor Entities

Use Developer Tools > States to find the real entities created by ESPHome.

Then set the CalmHome mapping helpers to those entity IDs:

- `input_text.calmhome_entity_presence_detected`
- `input_text.calmhome_entity_movement_detected`
- `input_text.calmhome_entity_still_presence_detected`
- `input_text.calmhome_entity_target_distance`
- `input_text.calmhome_entity_fall_detected`
- `input_text.calmhome_entity_door_opened`
- `input_text.calmhome_entity_sensor_online`

Make the change persistent by editing the `initial:` value of each helper in `/config/packages/calmhome.yaml`, then restart Home Assistant. The helpers define `initial`, so Home Assistant resets them to the file values on every restart; a value typed only in the UI works until the next restart and is then lost. The same applies to `input_number.calmhome_long_inactivity_minutes`.

If a sensor does not provide an optional entity (still presence, distance, fall, door), leave the default in place. An entity that does not exist reads as off and does not mark the sensor offline. An entity that exists but is `unavailable` does.

Use `config/entities.example.yaml` as the logical checklist. Keep `config/entities.local.yaml` private if you use it for notes; Home Assistant does not read it, but `python scripts/validate_configs.py` checks its entity ID format.

## 6. Enable And Disable Mock Mode

Enable mock mode:

1. Turn on `input_boolean.calmhome_mock_mode`.
2. Select a scenario in `input_select.calmhome_mock_scenario`.
3. Watch `sensor.calmhome_room_state` and the dashboard.

Disable mock mode:

1. Turn off `input_boolean.calmhome_mock_mode`.
2. Confirm `sensor.calmhome_room_state` now follows your mapped real entities.

Mock scenarios:

- `room_empty`
- `presence_detected`
- `movement_detected`
- `still_presence`
- `fall_suspected`
- `long_inactivity`
- `door_opened`
- `sensor_offline`

## 7. Import Or Recreate The Dashboard

Option A: Raw dashboard YAML

1. Open a Home Assistant dashboard.
2. Use the dashboard menu and open the raw configuration editor.
3. Paste the contents of `dashboards/calmhome_dashboard.yaml`.
4. Save.

Option B: Manual recreation

Create Entities cards for:

- room state
- presence
- movement
- fall suspected
- long inactivity
- last activity
- privacy status
- mock mode controls
- diagnostics toggle

Keep diagnostics conditional or hidden by default.

## 8. Test Notifications

The package uses `notify.notify` as a generic example.

To test:

1. Confirm your Home Assistant has at least one notifier.
2. Go to Developer Tools > Actions.
3. Run `notify.notify` with a test title and message.
4. If you use mobile app notifications, replace `notify.notify` in the package with your target notify action.
5. Enable mock mode and select `fall_suspected`. Wait 30 seconds for the recheck delay.
6. Select `long_inactivity` and wait for the notification automation delay.
7. Select `sensor_offline` and wait 3 minutes for the offline notification.

## 9. Safe Rollback

To disable CalmHome:

1. Remove or rename `/config/packages/calmhome.yaml`.
2. Remove or rename `/config/packages/calmhome_mock.yaml`.
3. Restart Home Assistant.
