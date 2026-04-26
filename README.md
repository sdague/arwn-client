# pyarwn

Python client library for parsing [ARWN](https://github.com/sdague/arwn) weather station MQTT messages.

## Installation

```bash
pip install pyarwn
```

## Usage

```python
from pyarwn import parse_message

readings = parse_message("arwn/temperature/BackYard", {"temp": 72.5, "units": "F"})
for r in readings:
    print(f"{r.sensor_name}: {r.value} {r.unit}")
# BackYard Temperature: 72.5 °F
```

## API

### `parse_message(topic, payload) -> list[ArwnReading]`

Parse an ARWN MQTT message. Returns an empty list for unknown topics.

### `ArwnReading`

| Field | Type | Description |
|---|---|---|
| `device_type` | `ArwnDeviceType` | `LOCATION` or `STATION` |
| `device_name` | `str` | e.g. `"BackYard"`, `"Weather Station"` |
| `sensor_key` | `str` | e.g. `"temp"`, `"speed"` |
| `sensor_name` | `str` | e.g. `"BackYard Temperature"` |
| `value` | `float \| int` | The reading value |
| `unit` | `str` | Unit string e.g. `"°F"`, `"mph"` |

### `ArwnDeviceType`

- `ArwnDeviceType.LOCATION` — sensor at a named location (temperature, moisture)
- `ArwnDeviceType.STATION` — weather station sensor (wind, rain, barometer)

## License

Apache 2.0
