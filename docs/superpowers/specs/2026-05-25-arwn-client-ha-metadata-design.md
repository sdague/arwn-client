# arwn-client HA Metadata Design

**Date:** 2026-05-25
**Status:** Approved

## Goal

Move all ARWN sensor parsing and Home Assistant metadata into `arwn-client` so that
changes to the MQTT topic structure only require updating the client library. The HA
component becomes a thin integration layer with no parsing logic.

## Motivation

Currently `homeassistant-core/homeassistant/components/arwn/sensor.py` duplicates the
MQTT parsing logic that already exists in `arwn_client/_parser.py`. Adding or renaming
a sensor type requires changes in both repos. With this design, only `arwn-client`
needs to change; the HA component picks it up by bumping the dependency version.

## Data Model (`arwn-client`)

`ArwnReading` gains five new fields:

```python
@dataclass
class ArwnReading:
    sensor_key: str
    sensor_name: str
    value: float | int
    unit: str
    device_class: str | None      # HA SensorDeviceClass value, e.g. "temperature"
    state_class: str              # HA SensorStateClass value, e.g. "measurement"
    icon: str | None              # MDI icon string, e.g. "mdi:compass", or None
    expose: bool = True           # False = skip in HA, still available to other consumers
```

All fields are required except `expose` (defaults to `True`). Making `device_class`,
`state_class`, and `icon` required ensures the parser cannot add a new sensor type
without explicitly setting them.

`ArwnDevice` is unchanged.

### Rationale for plain strings

`arwn-client` must not import from `homeassistant` — that would be a circular
dependency and would prevent the library from being installed outside HA. The string
values (`"temperature"`, `"measurement"`, etc.) match the `.value` of the corresponding
HA enum types, so the HA component can do `SensorDeviceClass(reading.device_class)`
safely.

## Sensor Metadata Table

| sensor_key | device_class | state_class | icon | expose |
|---|---|---|---|---|
| `temp` | `"temperature"` | `"measurement"` | None | True |
| `humid` | `"humidity"` | `"measurement"` | None | True |
| `moisture` | None | `"measurement"` | `"mdi:water-percent"` | True |
| `pressure` | None | `"measurement"` | `"mdi:thermometer-lines"` | True |
| `speed` | `"wind_speed"` | `"measurement"` | None | True |
| `gust` | `"wind_speed"` | `"measurement"` | None | True |
| `direction` | `"wind_direction"` | `"measurement_angle"` | `"mdi:compass"` | True |
| `total` | `"precipitation"` | `"measurement"` | None | **False** |
| `rate` | `"precipitation"` | `"measurement"` | None | True |
| `since_midnight` | `"precipitation"` | `"measurement"` | None | True |

### Notes on `expose`

- `total` is the raw cumulative gauge total published on `arwn/rain`. It uses
  `"measurement"` because the physical gauge can roll over (reset to zero). It is
  available to `arwn listen` and other library consumers but should not appear as an
  HA entity. `since_midnight` (computed daily reset) and `rate` are the meaningful
  values for HA.
- `expose=False` is the mechanism for future sensors that should be on MQTT but not
  in HA, with no HA component changes required.

### Notes on `since_midnight`

`since_midnight` resets to 0 each midnight (computed by `arwn`'s `RainAccumulator`).
It uses `"measurement"` not `"total_increasing"` because HA's `TOTAL_INCREASING`
state class cannot handle values that decrease.

## Parser Changes (`arwn-client`)

`parse_message()` in `_parser.py` is the only place `ArwnReading` objects are
constructed. All five new fields are set inline at each construction site. No new
public API is introduced.

The existing unit constants in `_units.py` are unchanged.

## HA Component Changes (`homeassistant-core`)

### `manifest.json`

Add `"arwn-client"` to `requirements`. Note: the PyPI package name is `arwn-client`
(not `arwn`, which is the server-side RF collector package).

### `sensor.py`

`discover_sensors()` is deleted entirely (~100 lines). The MQTT callback calls
`arwn_client.parse_message()` directly:

```python
from arwn_client import parse_message

device = parse_message(msg.topic, event)
if device is None:
    return

for reading in device.readings:
    if not reading.expose:
        continue
    unique_id = _unique_id(entry.entry_id, reading.sensor_key, device.device_key)
    if unique_id not in store:
        device_info = DeviceInfo(
            identifiers={(DOMAIN, _unique_id(entry.entry_id, device.device_key))},
            name=device.device_name,
        )
        sensor = ArwnSensor(reading, unique_id, device_info)
        sensor.set_initial_event(event_clean)
        store[unique_id] = sensor
        async_add_entities((sensor,), False)
    else:
        store[unique_id].set_event(event_clean)
```

`ArwnSensor.__init__` takes an `ArwnReading` and maps string metadata to HA types:

```python
class ArwnSensor(SensorEntity):
    def __init__(self, reading: ArwnReading, unique_id: str, device_info: DeviceInfo):
        self._attr_name = reading.sensor_name
        self._attr_unique_id = unique_id
        self._state_key = reading.sensor_key
        self._attr_native_unit_of_measurement = reading.unit
        self._attr_device_info = device_info
        self._attr_icon = reading.icon
        self._attr_device_class = SensorDeviceClass(reading.device_class) if reading.device_class else None
        self._attr_state_class = SensorStateClass(reading.state_class)
```

### Unique ID compatibility

The current HA component builds unique IDs as
`_unique_id(entry_id, "temperature", name, "temp")` — including the domain segment.
The new approach must produce identical strings to avoid breaking existing HA
installations (entities would be duplicated or lose history otherwise). The
implementation plan must audit and preserve the exact unique ID format, or include
a migration step.

### HA Tests

The existing tests in `tests/components/arwn/test_sensor.py` require no structural
changes — they test behavior via MQTT messages and entity/device registry assertions,
which is unchanged. The `total` sensor is no longer exposed, so any test asserting
its presence should be updated to assert its absence.

## `arwn-client` Test Changes

The 29 existing tests must be updated to pass the five new required fields on every
`ArwnReading` construction. New tests should assert correct metadata values for each
sensor type, and assert `expose=False` for `total`.

## Versioning

Bump `arwn-client` to `0.2.0` (minor bump — additive, but breaks the
`ArwnReading` constructor signature for any existing callers).
