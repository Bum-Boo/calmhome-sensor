# calmhome-sensor

Privacy-first Home Assistant + ESPHome beta for single-room presence and safety status monitoring.

calmhome-sensor helps a household understand room status without cameras, microphones, identity recognition, body visualization, network interception, or router-based sensing. It is designed for consent-based in-home use with ESPHome-compatible mmWave presence sensors, an optional fall-status sensor, optional door/PIR sensors, Home Assistant automations, mock mode, validation scripts, and deployment documentation.

## Current Status

- MVP skeleton complete.
- Hardware-ready beta configuration is included.
- Mock mode is included for safe testing without physical sensors.
- Real hardware validation is still required in the target room before relying on notifications.
- Default UI shows state-level summaries only.

## What It Shows

The default dashboard and automations work with simple room states:

- `stable`
- `presence detected`
- `movement detected`
- `fall suspected`
- `long inactivity`
- `door opened`

Raw diagnostics are hidden by default and should only be enabled for setup or troubleshooting.

## Privacy And Safety Boundaries

This project is a home safety and status monitor, not a surveillance system.

It does not implement:

- camera capture
- microphone capture
- face recognition
- identity recognition
- silhouette rendering
- through-wall sensing
- router hacking
- Wi-Fi packet sniffing
- raw radar point-cloud export
- credential capture

The Wi-Fi router is only network transport for Home Assistant and ESPHome. It is not treated as a sensing device.

All monitoring should be local-first, consent-based, and clearly disclosed to every resident. For remote access, use Tailscale, another VPN, or Home Assistant Cloud. Do not expose Home Assistant with public port forwarding.

## Quickstart

1. Install Python dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. Simulate events before installing hardware:

   ```powershell
   python scripts/simulate_events.py normal_activity
   python scripts/simulate_events.py fall_suspected
   ```

3. Install the Home Assistant packages:

   - `homeassistant/packages/calmhome.yaml`
   - `homeassistant/packages/calmhome_mock.yaml`

4. Enable mock mode in Home Assistant and test each scenario:

   - `room_empty`
   - `presence_detected`
   - `movement_detected`
   - `still_presence`
   - `fall_suspected`
   - `long_inactivity`
   - `door_opened`

5. Install an ESPHome sensor using one of the examples in `esphome/`.
6. Map your real Home Assistant entity IDs using the CalmHome mapping helpers.
7. Import or recreate the dashboard from `dashboards/calmhome_dashboard.yaml`.
8. Test notifications with mock mode, then test again with physical sensors.

## Hardware Assumptions

Home Assistant host:

- Raspberry Pi
- mini PC
- Home Assistant Green

Presence sensor options:

- Apollo MSR-2 or Everything Presence Lite
- ESP32 + HLK-LD2410C
- ESP32 + LD2450

Fall-status option:

- Seeed Studio MR60FDA2 with XIAO ESP32C6

Optional sensors:

- PIR motion sensor
- door contact sensor

## Entity Mapping

Use `config/entities.example.yaml` as the logical entity checklist:

- `presence_detected`
- `movement_detected`
- `still_presence_detected`
- `target_distance`
- `fall_detected`
- `door_opened`
- `sensor_online`

For private local notes, copy:

```powershell
Copy-Item config/entities.local.example.yaml config/entities.local.yaml
```

Then replace the placeholders with entity IDs from Home Assistant Developer Tools > States.

`config/entities.local.yaml` is ignored by Git. Do not commit personal entity IDs, Wi-Fi names, passwords, API keys, or room-specific private notes.

## Documentation

- [Home Assistant installation](docs/INSTALL_HOME_ASSISTANT.md)
- [ESPHome installation](docs/INSTALL_ESPHOME.md)
- [Hardware guide](docs/HARDWARE.md)
- [Sensor placement guide](docs/SENSOR_PLACEMENT.md)
- [Runtime test plan](docs/RUNTIME_TEST_PLAN.md)
- [Privacy model](docs/PRIVACY.md)

## Repository Layout

```text
config/                 Entity mapping examples
dashboards/             Home Assistant dashboard YAML
docs/                   Installation, privacy, hardware, placement, and test docs
esphome/                ESPHome example device YAML
homeassistant/packages/ Home Assistant core and mock packages
scripts/                Simulation and validation utilities
tests/                  Pytest test suite
```

## Validation

Run the full local validation suite:

```powershell
python scripts/validate_configs.py
python -m pytest tests
```

Or use npm scripts:

```powershell
npm run validate
npm test
npm run simulate-normal
npm run simulate-fall
```

If `make` is available:

```powershell
make validate
make test
make simulate-normal
make simulate-fall
```

## Notes For Deployment

- Start in mock mode before connecting physical sensors.
- Use conservative sensor sensitivity until the room has been tested.
- Keep optional diagnostics disabled during normal use.
- Confirm long-inactivity and fall-suspected notification behavior with residents.
- Re-run the runtime test plan after moving furniture, changing curtains, adding fans, or changing sensor angle.
