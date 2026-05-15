# Install ESPHome Sensors

This guide uses the ESPHome Device Builder add-on inside Home Assistant.

## 1. Install ESPHome Device Builder

1. In Home Assistant, go to Settings > Add-ons > Add-on Store.
2. Search for ESPHome Device Builder.
3. Install it.
4. Start the add-on.
5. Open the ESPHome web UI.

If your Home Assistant installation does not support add-ons, use ESPHome from Docker or the command line instead.

## 2. Choose A YAML Example

Presence sensor:

- `esphome/ld2410_presence_example.yaml`

Fall status sensor:

- `esphome/mr60fda2_fall_example.yaml`

Copy the file into the ESPHome config directory. In the Home Assistant add-on this is usually:

```text
/config/esphome/
```

You can also create a new ESPHome device in the UI, open Edit, and paste the example YAML.

## 3. Set ESPHome Secrets

In ESPHome `secrets.yaml`, add:

```yaml
wifi_ssid: "your-wifi"
wifi_password: "your-password"
calmhome_ld2410_api_key: "replace-with-esphome-api-key"
calmhome_ld2410_ota_password: "replace-with-ota-password"
calmhome_mr60fda2_api_key: "replace-with-esphome-api-key"
calmhome_mr60fda2_ota_password: "replace-with-ota-password"
calmhome_fallback_ap_password: "replace-with-setup-password"
```

Use unique API keys and OTA passwords per device.

## 4. Check Pins And Board Type

Before flashing:

- Confirm the ESP32 board type matches your actual board.
- Confirm UART TX/RX pins match your wiring.
- Confirm the sensor and ESP32 share ground.
- Confirm the sensor power matches its required voltage.

The examples are starting points. Board variants may need different pins.

## 5. Flash The Device

Initial flash:

1. Connect the ESP32 or XIAO ESP32C6 with a USB data cable.
2. In ESPHome Device Builder, open the device.
3. Choose Install.
4. Select the USB or browser-based install method available to your setup.
5. Wait for logs to show the device connected to Wi-Fi.

Later updates can usually be installed wirelessly after the device is online.

## 6. Add Device To Home Assistant

After the ESPHome device is online:

1. Go to Settings > Devices & services.
2. Look for a discovered ESPHome device.
3. Add it.
4. Confirm the API encryption key if prompted.

## 7. Confirm Entities

In Developer Tools > States, search for the sensor names.

LD2410 example entities should include:

- `binary_sensor.calmhome_presence_detected`
- `binary_sensor.calmhome_movement_detected`
- `binary_sensor.calmhome_still_presence_detected`
- `sensor.calmhome_target_distance`
- `binary_sensor.calmhome_sensor_online`

MR60FDA2 example entities should include:

- `binary_sensor.calmhome_fall_detected`
- `binary_sensor.calmhome_fall_sensor_online`
- a presence entity from the fall status sensor

If your entity IDs differ, update the CalmHome mapping helpers in Home Assistant.

## 8. LD2450 Or Prebuilt Sensors

For LD2450, Apollo MSR-2, Everything Presence Lite, or another ESPHome-compatible device:

1. Install or adopt the device using its vendor instructions.
2. Identify its Home Assistant entities in Developer Tools > States.
3. Map the closest logical entities in CalmHome:
   - presence
   - movement
   - still presence if available
   - optional distance
   - online status

If a device does not expose still presence or target distance, leave the helper mapped to a placeholder and rely on the available presence/movement entities.
