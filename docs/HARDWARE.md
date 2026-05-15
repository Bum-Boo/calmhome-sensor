# Hardware Guide

## Recommended Paths

### A. Easiest Path: Prebuilt Presence Sensor + MR60FDA2

Use a prebuilt ESPHome presence sensor such as Apollo MSR-2 or Everything Presence Lite for room occupancy and movement states. Add a Seeed Studio MR60FDA2 with XIAO ESP32C6 for fall status.

Pros:

- Lowest wiring effort.
- Usually ships with ESPHome or Home Assistant-friendly firmware.
- Good fit for a first single-room MVP.

Setup notes:

- Adopt the device in ESPHome or Home Assistant.
- Keep entity names aligned with the package, or edit `homeassistant/packages/calmhome.yaml`.
- Mount sensors where residents expect them and can consent to them.

### B. DIY Path: ESP32 + LD2410C/LD2450 + Optional PIR/Door Sensor

Use an ESP32 with an HLK-LD2410C or LD2450 module for presence. Add a PIR sensor if you want a simple independent motion check. Add a door contact sensor if door-open events matter for the room.

High-level wiring notes:

- Power the ESP32 and sensor from a stable supply that matches the module requirements.
- Connect UART TX/RX between the ESP32 and the radar module according to the module pinout.
- Use a shared ground between the ESP32 and attached sensor module.
- For a PIR or door contact sensor, use a GPIO suitable for digital input and configure pull-up or pull-down behavior as needed.
- Keep wiring short and strain-relieved in an enclosure.

The example `esphome/ld2410_presence_example.yaml` exposes these Home Assistant entities:

- `binary_sensor.calmhome_presence_detected`
- `binary_sensor.calmhome_movement_detected`
- `binary_sensor.calmhome_still_presence_detected`
- `sensor.calmhome_target_distance`
- `binary_sensor.calmhome_sensor_online`

For LD2450, use the matching ESPHome component and keep the same entity naming pattern so the Home Assistant package can stay unchanged.

### C. Research Path: TI IWR6843-Class Radar

TI IWR6843-class radar modules can support advanced research and custom firmware work, but they are out of scope for this MVP.

Reasons:

- More complex firmware and data handling.
- More validation work before it is appropriate for a simple home safety/status monitor.
- Easier to drift into detailed sensing outputs that are intentionally excluded from this project.

Use this path only for separate research work with clear consent, documented data handling, and a separate design review.

## Placement Guidance

- Place sensors in the room being monitored, not in hidden or unexpected locations.
- Prefer visible mounting and label the device purpose.
- Avoid pointing sensors at areas outside the intended room.
- Test normal daily activity, still presence, room empty, and fall-suspected scenarios before relying on alerts.

## Home Assistant Host

Supported assumptions:

- Raspberry Pi.
- Mini PC.
- Home Assistant Green.

Remote access should be via VPN/Tailscale or Home Assistant Cloud. Public port forwarding is not recommended.
