# Changelog

## [0.1.0] - 2026-04-26

Initial release.

- `parse_message(topic, payload)` parses ARWN MQTT messages into an `ArwnDevice` with a list of `ArwnReading` objects
- Supports temperature (with optional humidity), moisture, wind, rain, rain/today, barometer
- Device grouping logic lives in the library: location sensors (temperature, moisture) share a device keyed by location name; station sensors (wind, rain, barometer) share a `"station"` device
- `arwn-client listen` CLI subscribes to `arwn/#` and prints device readings as they arrive; supports `--host`, `--port`, `--count`, and `--json` flags
