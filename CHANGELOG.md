# Changelog

## [0.2.1] - 2026-05-26

Fix CI release workflow to use uv. No functional changes from 0.2.0.

## [0.2.0] - 2026-05-25

- Add HA sensor metadata fields (`device_class`, `state_class`, `icon`, `expose`, `unique_id_parts`) to `ArwnReading`
- Parser sets all metadata for every sensor type
- `expose=False` on `rain/total` (gauge can roll over, not suitable for HA long-term stats)

## [0.1.0] - 2026-04-26

Initial release.

- `parse_message(topic, payload)` parses ARWN MQTT messages into an `ArwnDevice` with a list of `ArwnReading` objects
- Supports temperature (with optional humidity), moisture, wind, rain, rain/today, barometer
- Device grouping logic lives in the library: location sensors (temperature, moisture) share a device keyed by location name; station sensors (wind, rain, barometer) share a `"station"` device
- `arwn-client listen` CLI subscribes to `arwn/#` and prints device readings as they arrive; supports `--host`, `--port`, `--count`, and `--json` flags
