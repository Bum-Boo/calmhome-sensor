# calmhome-sensor

## Goal / 목표

**English:** calmhome-sensor is a privacy-preserving, camera-free Home Assistant MVP for single-room presence and safety status. It uses ESPHome-compatible sensors and local Home Assistant logic to show only state-level summaries such as stable, presence detected, movement detected, fall suspected, long inactivity, and door opened.

**한국어:** calmhome-sensor는 한 방의 재실 및 안전 상태를 확인하기 위한 프라이버시 중심의 카메라 없는 Home Assistant MVP입니다. ESPHome 호환 센서와 로컬 Home Assistant 로직을 사용해 안정 상태, 재실 감지, 움직임 감지, 낙상 의심, 장시간 비활동, 문 열림 같은 상태 요약만 표시합니다.

This is a home safety and status monitor, not a surveillance system. It does not identify people, render bodies, record media, intercept network traffic, or use the Wi-Fi router as a sensing device. The router is only network transport for Home Assistant and ESPHome.

## Privacy Model

- Local-first: ESPHome devices publish simple entity states to Home Assistant on the local network.
- Minimal states: the dashboard defaults to summaries, not diagnostic measurements.
- No identity layer: the MVP does not infer who a person is.
- Short retention: keep only Home Assistant state history needed for safety/status review; suggested default is 7 days or less.
- Consent required: all residents should know which sensors are installed, what states they expose, and how notifications work.
- Remote access: use Tailscale, another VPN, or Home Assistant Cloud. Do not expose Home Assistant with public port forwarding.

## Hardware Assumptions

Host:

- Raspberry Pi, mini PC, or Home Assistant Green running Home Assistant.

Presence options:

- Easiest: Apollo MSR-2 or Everything Presence Lite, adopted into ESPHome/Home Assistant.
- DIY: ESP32 plus HLK-LD2410C or LD2450 with ESPHome.

Fall option:

- Seeed Studio MR60FDA2 with XIAO ESP32C6, exposed through ESPHome.

Optional:

- PIR motion sensor.
- Door contact sensor.

The project also works without physical hardware by using `scripts/simulate_events.py`.

## Repository Layout

- `esphome/`: example ESPHome device YAML.
- `homeassistant/packages/calmhome.yaml`: package with template entities and automations.
- `dashboards/calmhome_dashboard.yaml`: dashboard view that shows only status summaries by default.
- `scripts/simulate_events.py`: local simulated event generator.
- `scripts/validate_configs.py`: YAML and privacy guardrail validator.
- `tests/`: simulated event, YAML loading, and privacy guardrail tests.

## Setup

1. Install Python 3.11 or newer.
2. Install Python dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Review and copy the ESPHome example you need from `esphome/`.
4. Add ESPHome secrets in your ESPHome `secrets.yaml`:

   ```yaml
   wifi_ssid: "your-wifi"
   wifi_password: "your-password"
   calmhome_ld2410_api_key: "replace-with-esphome-api-key"
   calmhome_ld2410_ota_password: "replace-with-ota-password"
   calmhome_mr60fda2_api_key: "replace-with-esphome-api-key"
   calmhome_mr60fda2_ota_password: "replace-with-ota-password"
   calmhome_fallback_ap_password: "replace-with-setup-password"
   ```

5. In Home Assistant, enable packages if not already enabled:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

6. Place `homeassistant/packages/calmhome.yaml` into your Home Assistant `packages/` directory.
7. If your ESPHome entity IDs differ, replace the entity IDs in the package comments section and templates.
8. Import or paste `dashboards/calmhome_dashboard.yaml` into a Home Assistant dashboard.

## Validation And Simulation

```powershell
make validate
make test
make simulate-normal
make simulate-fall
```

If `make` is not available on your system, run the underlying commands:

```powershell
python scripts/validate_configs.py
python -m pytest tests
python scripts/simulate_events.py normal_activity
python scripts/simulate_events.py fall_suspected
```

If you prefer package scripts:

```powershell
npm run validate
npm test
npm run simulate-normal
npm run simulate-fall
```

## Notes

- Physical sensor tuning is room-specific. Start with conservative sensitivity and test with consented residents.
- Do not use this project for hidden monitoring or outside a home safety/status context.
- The optional diagnostics section is disabled by default and should only be enabled for setup and troubleshooting.
