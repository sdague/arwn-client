# arwn-client

Python client library for parsing [ARWN](https://github.com/sdague/arwn) weather station MQTT messages.

## Installation

```bash
pip install arwn-client
```

## Usage

```python
from arwn_client import parse_message

device = parse_message("arwn/temperature/BackYard", {"temp": 72.5, "units": "F"})
if device:
    print(f"{device.device_name}")
    for r in device.readings:
        print(f"  {r.sensor_name}: {r.value} {r.unit}")
# BackYard
#   BackYard Temperature: 72.5 °F
```

## CLI

```bash
arwn listen                          # connect to localhost:1883
arwn listen --host 192.168.1.10      # custom broker host
arwn listen --port 1884              # custom broker port
arwn listen --count 5                # stop after 5 messages
arwn listen --json                   # output as JSON
```

## API

### `parse_message(topic, payload) -> ArwnDevice | None`

Parse an ARWN MQTT message. Returns `None` for unknown topics.

### `ArwnDevice`

| Field | Type | Description |
|---|---|---|
| `device_key` | `str` | Unique key e.g. `"temperature_BackYard"` |
| `device_name` | `str` | e.g. `"BackYard"`, `"Weather Station"` |
| `readings` | `list[ArwnReading]` | Sensor readings for this device |

### `ArwnReading`

| Field | Type | Description |
|---|---|---|
| `sensor_key` | `str` | e.g. `"temp"`, `"speed"` |
| `sensor_name` | `str` | e.g. `"BackYard Temperature"` |
| `value` | `float \| int` | The reading value |
| `unit` | `str` | Unit string e.g. `"°F"`, `"mph"` |

## License

Apache 2.0
