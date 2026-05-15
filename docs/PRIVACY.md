# Privacy Policy For The MVP

calmhome-sensor is designed as a consented home safety/status monitor.

## Explicit Exclusions

- No camera.
- No mic.
- No microphone.
- No biometric ID.
- No face recognition.
- No silhouettes.
- No raw point cloud export.
- No identity recognition.
- No credential capture.
- No network packet interception.

## Data Minimization

The system should expose only state-level summaries by default:

- stable
- presence detected
- movement detected
- fall suspected
- long inactivity
- door opened

Diagnostic measurements, such as target distance, are disabled or hidden by default and should be used only during setup or troubleshooting.

## Local-First Processing

ESPHome devices publish simple states to Home Assistant over the local network. Home Assistant performs the summary logic locally. The Wi-Fi router is only network transport, not a sensing input.

Remote access should use VPN/Tailscale or Home Assistant Cloud. Do not rely on public port forwarding.

## Retention Defaults

Recommended defaults:

- Keep Home Assistant recorder history for this package to 7 days or less unless residents agree otherwise.
- Do not export diagnostic event logs unless needed for troubleshooting.
- Delete troubleshooting exports after the issue is resolved.

## Consent Requirements

All residents should consent before installation. At minimum, residents should know:

- which room is monitored,
- where sensors are placed,
- which summary states can be shown,
- who receives notifications,
- how to pause or remove the system.

Do not use this project for hidden monitoring, landlord/tenant monitoring, workplace monitoring, or any context where residents cannot freely consent.
