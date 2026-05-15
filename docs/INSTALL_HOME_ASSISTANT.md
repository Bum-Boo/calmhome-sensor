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
- `input_boolean.calmhome_mock_mode`
- `input_select.calmhome_mock_scenario`

## 5. Map Real Sensor Entities

Use Developer Tools > States to find the real entities created by ESPHome.

Then update the CalmHome mapping helpers:

- `input_text.calmhome_entity_presence_detected`
- `input_text.calmhome_entity_movement_detected`
- `input_text.calmhome_entity_still_presence_detected`
- `input_text.calmhome_entity_target_distance`
- `input_text.calmhome_entity_fall_detected`
- `input_text.calmhome_entity_door_opened`
- `input_text.calmhome_entity_sensor_online`

Use `config/entities.example.yaml` as the logical checklist. Keep `config/entities.local.yaml` private if you use it for notes.

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

## 9. Safe Rollback

To disable CalmHome:

1. Remove or rename `/config/packages/calmhome.yaml`.
2. Remove or rename `/config/packages/calmhome_mock.yaml`.
3. Restart Home Assistant.
