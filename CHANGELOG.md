# Changelog

## [0.1.0] - 2026-04-26

Initial release.

- `parse_message(topic, payload)` parses ARWN MQTT messages into `ArwnReading` objects
- Supports temperature (with optional humidity), moisture, wind, rain, rain/today, barometer
- `ArwnDeviceType` distinguishes location-based sensors from weather station sensors
