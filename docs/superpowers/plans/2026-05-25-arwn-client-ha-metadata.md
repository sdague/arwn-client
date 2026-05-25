# arwn-client HA Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add HA sensor metadata (`device_class`, `state_class`, `icon`, `expose`, `unique_id_parts`) to `ArwnReading` in `arwn-client`, then rewrite the HA `arwn` component's `sensor.py` to use `arwn-client` instead of its duplicated parsing logic.

**Architecture:** `ArwnReading` gains five new fields carrying HA metadata as plain strings (no HA import). The parser sets them at construction time. The HA component drops `discover_sensors()` entirely and maps `ArwnReading` fields to HA enum types at entity creation. Unique IDs are preserved exactly via a `unique_id_parts` tuple on each reading.

**Tech Stack:** Python 3.10+, `arwn-client` (this repo), `homeassistant-core` (`homeassistant/components/arwn/`), `uv`, `pytest`, `ruff`

---

## File Map

### `arwn-client` repo (`/home/sdague/code/arwn-client/`)

| File | Change |
|---|---|
| `arwn_client/_models.py` | Add 5 fields to `ArwnReading` |
| `arwn_client/_parser.py` | Set new fields on every `ArwnReading` construction |
| `tests/test_parser.py` | Update existing tests + add metadata assertion tests |
| `pyproject.toml` | Bump version to `0.2.0` |

### `homeassistant-core` repo (`/home/sdague/code/homeassistant-core/`)

| File | Change |
|---|---|
| `homeassistant/components/arwn/sensor.py` | Delete `discover_sensors()`, rewrite callback, rewrite `ArwnSensor.__init__` |
| `homeassistant/components/arwn/manifest.json` | Add `arwn-client` to `requirements` |
| `tests/components/arwn/test_sensor.py` | Update `rain_total` test; add `expose=False` test |

---

## Task 1: Extend `ArwnReading` with metadata fields

**Files:**
- Modify: `arwn_client/_models.py`

- [ ] **Step 1: Update the `ArwnReading` dataclass**

Replace the entire contents of `arwn_client/_models.py` with:

```python
"""Data models for ARWN sensor readings."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ArwnReading:
    """A single sensor reading parsed from an ARWN MQTT message."""

    sensor_key: str
    sensor_name: str
    value: float | int
    unit: str
    device_class: str | None
    state_class: str
    icon: str | None
    unique_id_parts: tuple[str, ...]
    expose: bool = True


@dataclass
class ArwnDevice:
    """A physical device that owns one or more sensor readings."""

    device_key: str
    device_name: str
    readings: list[ArwnReading] = field(default_factory=list)
```

- [ ] **Step 2: Run existing tests to see the breakage**

```bash
cd /home/sdague/code/arwn-client && uv run pytest tests/test_parser.py -v 2>&1 | head -40
```

Expected: many failures — `ArwnReading` constructor calls are missing the new required fields. This confirms the tests are sensitive to the model change.

- [ ] **Step 3: Commit the model change**

```bash
git add arwn_client/_models.py
git commit -m "feat: add HA metadata fields to ArwnReading"
```

---

## Task 2: Update the parser to set all new fields

**Files:**
- Modify: `arwn_client/_parser.py`

- [ ] **Step 1: Replace `_parser.py` with the updated version**

```python
"""ARWN MQTT topic and payload parser."""

from __future__ import annotations

from typing import Any

from ._models import ArwnDevice, ArwnReading
from ._units import CELSIUS, DEGREE, FAHRENHEIT, INCHES, PERCENTAGE

_STATION_KEY = "station"
_STATION_NAME = "Weather Station"


def _location_device(name: str) -> ArwnDevice:
    return ArwnDevice(device_key=name.lower(), device_name=name)


def _station_device() -> ArwnDevice:
    return ArwnDevice(device_key=_STATION_KEY, device_name=_STATION_NAME)


def parse_message(topic: str, payload: dict[str, Any]) -> ArwnDevice | None:
    """Parse an ARWN MQTT message into a device with readings.

    Returns None for unknown or malformed topics.
    """
    parts = topic.split("/")
    if len(parts) < 2:
        return None

    unit = payload.get("units", "")
    domain = parts[1]

    if domain == "temperature":
        if len(parts) < 3:
            return None
        name = parts[2]
        temp_unit = FAHRENHEIT if unit == "F" else CELSIUS
        device = _location_device(name)
        device.readings.append(
            ArwnReading(
                sensor_key="temp",
                sensor_name=f"{name} Temperature",
                value=payload["temp"],
                unit=temp_unit,
                device_class="temperature",
                state_class="measurement",
                icon=None,
                unique_id_parts=("temperature", name, "temp"),
            )
        )
        if "humid" in payload:
            device.readings.append(
                ArwnReading(
                    sensor_key="humid",
                    sensor_name=f"{name} Humidity",
                    value=payload["humid"],
                    unit=PERCENTAGE,
                    device_class="humidity",
                    state_class="measurement",
                    icon=None,
                    unique_id_parts=("temperature", name, "humid"),
                )
            )
        return device

    if domain == "moisture":
        if len(parts) < 3:
            return None
        name = parts[2]
        device = _location_device(name)
        device.readings.append(
            ArwnReading(
                sensor_key="moisture",
                sensor_name=f"{name} Moisture",
                value=payload["moisture"],
                unit=unit,
                device_class=None,
                state_class="measurement",
                icon="mdi:water-percent",
                unique_id_parts=("moisture", name, "moisture"),
            )
        )
        return device

    if domain == "rain":
        device = _station_device()
        if len(parts) >= 3 and parts[2] == "today":
            device.readings.append(
                ArwnReading(
                    sensor_key="since_midnight",
                    sensor_name="Rain Since Midnight",
                    value=payload["since_midnight"],
                    unit=INCHES,
                    device_class="precipitation",
                    state_class="measurement",
                    icon=None,
                    unique_id_parts=("rain", "since_midnight"),
                )
            )
        else:
            device.readings.extend(
                [
                    ArwnReading(
                        sensor_key="total",
                        sensor_name="Total Rainfall",
                        value=payload["total"],
                        unit=unit,
                        device_class="precipitation",
                        state_class="measurement",
                        icon=None,
                        unique_id_parts=("rain", "total"),
                        expose=False,
                    ),
                    ArwnReading(
                        sensor_key="rate",
                        sensor_name="Rainfall Rate",
                        value=payload["rate"],
                        unit=unit,
                        device_class="precipitation",
                        state_class="measurement",
                        icon=None,
                        unique_id_parts=("rain", "rate"),
                    ),
                ]
            )
        return device

    if domain == "barometer":
        device = _station_device()
        device.readings.append(
            ArwnReading(
                sensor_key="pressure",
                sensor_name="Barometer",
                value=payload["pressure"],
                unit=unit,
                device_class=None,
                state_class="measurement",
                icon="mdi:thermometer-lines",
                unique_id_parts=("barometer", "pressure"),
            )
        )
        return device

    if domain == "wind":
        device = _station_device()
        device.readings.extend(
            [
                ArwnReading(
                    sensor_key="speed",
                    sensor_name="Wind Speed",
                    value=payload["speed"],
                    unit=unit,
                    device_class="wind_speed",
                    state_class="measurement",
                    icon=None,
                    unique_id_parts=("wind", "speed"),
                ),
                ArwnReading(
                    sensor_key="gust",
                    sensor_name="Wind Gust",
                    value=payload["gust"],
                    unit=unit,
                    device_class="wind_speed",
                    state_class="measurement",
                    icon=None,
                    unique_id_parts=("wind", "gust"),
                ),
                ArwnReading(
                    sensor_key="direction",
                    sensor_name="Wind Direction",
                    value=payload["direction"],
                    unit=DEGREE,
                    device_class="wind_direction",
                    state_class="measurement_angle",
                    icon="mdi:compass",
                    unique_id_parts=("wind", "direction"),
                ),
            ]
        )
        return device

    return None
```

- [ ] **Step 2: Run tests — still failing (tests haven't been updated yet)**

```bash
uv run pytest tests/test_parser.py -v 2>&1 | head -40
```

Expected: tests that construct `ArwnReading` directly still fail; tests that only call `parse_message()` and check `.value`/`.unit`/`.sensor_name` should now pass.

- [ ] **Step 3: Commit the parser update**

```bash
git add arwn_client/_parser.py
git commit -m "feat: set HA metadata fields in parser for all sensor types"
```

---

## Task 3: Update existing tests and add metadata tests

**Files:**
- Modify: `tests/test_parser.py`

- [ ] **Step 1: Replace `tests/test_parser.py` with updated version**

```python
"""Tests for the ARWN MQTT message parser."""

from __future__ import annotations

import pytest

from arwn_client import ArwnDevice, ArwnReading, parse_message
from arwn_client._units import CELSIUS, DEGREE, FAHRENHEIT, INCHES, PERCENTAGE

# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------


def test_temperature_fahrenheit() -> None:
    device = parse_message("arwn/temperature/BackYard", {"temp": 72.5, "units": "F"})
    assert device is not None
    assert device.device_key == "backyard"
    assert device.device_name == "BackYard"
    assert len(device.readings) == 1
    r = device.readings[0]
    assert r.sensor_key == "temp"
    assert r.value == 72.5
    assert r.unit == FAHRENHEIT
    assert r.sensor_name == "BackYard Temperature"


def test_temperature_celsius() -> None:
    device = parse_message("arwn/temperature/FrontYard", {"temp": 22.0, "units": "C"})
    assert device is not None
    assert device.readings[0].unit == CELSIUS


def test_temperature_with_humidity() -> None:
    device = parse_message(
        "arwn/temperature/BackYard", {"temp": 72.5, "humid": 55.0, "units": "F"}
    )
    assert device is not None
    assert len(device.readings) == 2
    keys = {r.sensor_key for r in device.readings}
    assert keys == {"temp", "humid"}
    humid = next(r for r in device.readings if r.sensor_key == "humid")
    assert humid.unit == PERCENTAGE
    assert humid.value == 55.0
    assert humid.sensor_name == "BackYard Humidity"


def test_temperature_no_humidity() -> None:
    device = parse_message("arwn/temperature/BackYard", {"temp": 72.5, "units": "F"})
    assert device is not None
    assert all(r.sensor_key != "humid" for r in device.readings)


def test_temperature_missing_location_returns_none() -> None:
    assert parse_message("arwn/temperature", {"temp": 72.5}) is None


# ---------------------------------------------------------------------------
# Moisture
# ---------------------------------------------------------------------------


def test_moisture() -> None:
    device = parse_message("arwn/moisture/FrontLawn", {"moisture": 45.2, "units": "%"})
    assert device is not None
    assert device.device_key == "frontlawn"
    assert device.device_name == "FrontLawn"
    assert len(device.readings) == 1
    r = device.readings[0]
    assert r.sensor_key == "moisture"
    assert r.value == 45.2
    assert r.sensor_name == "FrontLawn Moisture"


def test_moisture_missing_location_returns_none() -> None:
    assert parse_message("arwn/moisture", {"moisture": 45.2}) is None


# ---------------------------------------------------------------------------
# Wind
# ---------------------------------------------------------------------------


def test_wind() -> None:
    device = parse_message(
        "arwn/wind", {"speed": 12.3, "gust": 18.0, "direction": 270, "units": "mph"}
    )
    assert device is not None
    assert device.device_key == "station"
    assert device.device_name == "Weather Station"
    assert len(device.readings) == 3
    keys = {r.sensor_key for r in device.readings}
    assert keys == {"speed", "gust", "direction"}

    direction = next(r for r in device.readings if r.sensor_key == "direction")
    assert direction.unit == DEGREE
    assert direction.value == 270

    speed = next(r for r in device.readings if r.sensor_key == "speed")
    assert speed.unit == "mph"


# ---------------------------------------------------------------------------
# Rain
# ---------------------------------------------------------------------------


def test_rain() -> None:
    device = parse_message("arwn/rain", {"total": 1.2, "rate": 0.1, "units": "in"})
    assert device is not None
    assert device.device_key == "station"
    assert len(device.readings) == 2
    keys = {r.sensor_key for r in device.readings}
    assert keys == {"total", "rate"}


def test_rain_today() -> None:
    device = parse_message("arwn/rain/today", {"since_midnight": 0.5, "units": "in"})
    assert device is not None
    assert device.device_key == "station"
    assert len(device.readings) == 1
    r = device.readings[0]
    assert r.sensor_key == "since_midnight"
    assert r.unit == INCHES
    assert r.value == 0.5
    assert r.sensor_name == "Rain Since Midnight"


# ---------------------------------------------------------------------------
# Barometer
# ---------------------------------------------------------------------------


def test_barometer() -> None:
    device = parse_message("arwn/barometer", {"pressure": 1013.25, "units": "mb"})
    assert device is not None
    assert device.device_key == "station"
    assert len(device.readings) == 1
    r = device.readings[0]
    assert r.sensor_key == "pressure"
    assert r.value == 1013.25
    assert r.unit == "mb"
    assert r.sensor_name == "Barometer"


# ---------------------------------------------------------------------------
# Device grouping
# ---------------------------------------------------------------------------


def test_temperature_and_moisture_same_location_same_device_key() -> None:
    temp = parse_message("arwn/temperature/BackYard", {"temp": 72.5, "units": "F"})
    moisture = parse_message("arwn/moisture/BackYard", {"moisture": 55.0, "units": "%"})
    assert temp is not None
    assert moisture is not None
    assert temp.device_key == moisture.device_key
    assert temp.device_name == moisture.device_name


def test_wind_rain_barometer_share_station_device_key() -> None:
    wind = parse_message(
        "arwn/wind", {"speed": 5.0, "gust": 8.0, "direction": 90, "units": "mph"}
    )
    rain = parse_message("arwn/rain", {"total": 0.5, "rate": 0.0, "units": "in"})
    baro = parse_message("arwn/barometer", {"pressure": 1013.0, "units": "mb"})
    assert wind is not None
    assert rain is not None
    assert baro is not None
    assert wind.device_key == rain.device_key == baro.device_key == "station"


def test_different_locations_have_different_device_keys() -> None:
    backyard = parse_message("arwn/temperature/BackYard", {"temp": 72.5, "units": "F"})
    frontyard = parse_message(
        "arwn/temperature/FrontYard", {"temp": 68.0, "units": "F"}
    )
    assert backyard is not None
    assert frontyard is not None
    assert backyard.device_key != frontyard.device_key


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_unknown_domain_returns_none() -> None:
    assert parse_message("arwn/unknown_sensor", {"value": 1.0}) is None


def test_too_short_topic_returns_none() -> None:
    assert parse_message("arwn", {"temp": 72.5}) is None


def test_timestamp_in_payload_is_ignored() -> None:
    device = parse_message(
        "arwn/temperature/BackYard",
        {"temp": 72.5, "units": "F", "timestamp": "2026-04-26T12:00:00"},
    )
    assert device is not None
    assert device.readings[0].value == 72.5


@pytest.mark.parametrize(
    ("topic", "payload"),
    [
        ("arwn/temperature/BackYard", {"temp": 72.5, "units": "F"}),
        ("arwn/moisture/FrontLawn", {"moisture": 45.2, "units": "%"}),
        ("arwn/wind", {"speed": 12.3, "gust": 18.0, "direction": 270, "units": "mph"}),
        ("arwn/rain", {"total": 1.2, "rate": 0.1, "units": "in"}),
        ("arwn/rain/today", {"since_midnight": 0.5, "units": "in"}),
        ("arwn/barometer", {"pressure": 1013.25, "units": "mb"}),
    ],
)
def test_all_sensor_types_return_device(topic: str, payload: dict) -> None:
    device = parse_message(topic, payload)
    assert device is not None
    assert isinstance(device, ArwnDevice)
    assert len(device.readings) >= 1


@pytest.mark.parametrize(
    ("topic", "payload"),
    [
        ("arwn/temperature/BackYard", {"temp": 72.5, "units": "F"}),
        ("arwn/moisture/FrontLawn", {"moisture": 45.2, "units": "%"}),
        ("arwn/wind", {"speed": 12.3, "gust": 18.0, "direction": 270, "units": "mph"}),
        ("arwn/rain", {"total": 1.2, "rate": 0.1, "units": "in"}),
        ("arwn/rain/today", {"since_midnight": 0.5, "units": "in"}),
        ("arwn/barometer", {"pressure": 1013.25, "units": "mb"}),
    ],
)
def test_all_readings_are_arwnreading_instances(topic: str, payload: dict) -> None:
    device = parse_message(topic, payload)
    assert device is not None
    for r in device.readings:
        assert isinstance(r, ArwnReading)


# ---------------------------------------------------------------------------
# Metadata correctness
# ---------------------------------------------------------------------------


def test_temperature_metadata() -> None:
    device = parse_message("arwn/temperature/BackYard", {"temp": 72.5, "units": "F"})
    assert device is not None
    r = device.readings[0]
    assert r.device_class == "temperature"
    assert r.state_class == "measurement"
    assert r.icon is None
    assert r.expose is True
    assert r.unique_id_parts == ("temperature", "BackYard", "temp")


def test_humidity_metadata() -> None:
    device = parse_message(
        "arwn/temperature/BackYard", {"temp": 72.5, "humid": 65.0, "units": "F"}
    )
    assert device is not None
    humid = next(r for r in device.readings if r.sensor_key == "humid")
    assert humid.device_class == "humidity"
    assert humid.state_class == "measurement"
    assert humid.icon is None
    assert humid.expose is True
    assert humid.unique_id_parts == ("temperature", "BackYard", "humid")


def test_moisture_metadata() -> None:
    device = parse_message("arwn/moisture/FrontLawn", {"moisture": 45.2, "units": "%"})
    assert device is not None
    r = device.readings[0]
    assert r.device_class is None
    assert r.state_class == "measurement"
    assert r.icon == "mdi:water-percent"
    assert r.expose is True
    assert r.unique_id_parts == ("moisture", "FrontLawn", "moisture")


def test_wind_speed_metadata() -> None:
    device = parse_message(
        "arwn/wind", {"speed": 12.3, "gust": 18.0, "direction": 270, "units": "mph"}
    )
    assert device is not None
    speed = next(r for r in device.readings if r.sensor_key == "speed")
    assert speed.device_class == "wind_speed"
    assert speed.state_class == "measurement"
    assert speed.icon is None
    assert speed.expose is True
    assert speed.unique_id_parts == ("wind", "speed")


def test_wind_direction_metadata() -> None:
    device = parse_message(
        "arwn/wind", {"speed": 12.3, "gust": 18.0, "direction": 270, "units": "mph"}
    )
    assert device is not None
    direction = next(r for r in device.readings if r.sensor_key == "direction")
    assert direction.device_class == "wind_direction"
    assert direction.state_class == "measurement_angle"
    assert direction.icon == "mdi:compass"
    assert direction.expose is True
    assert direction.unique_id_parts == ("wind", "direction")


def test_rain_total_not_exposed() -> None:
    device = parse_message("arwn/rain", {"total": 1.2, "rate": 0.1, "units": "in"})
    assert device is not None
    total = next(r for r in device.readings if r.sensor_key == "total")
    assert total.expose is False
    assert total.device_class == "precipitation"
    assert total.state_class == "measurement"
    assert total.unique_id_parts == ("rain", "total")


def test_rain_rate_metadata() -> None:
    device = parse_message("arwn/rain", {"total": 1.2, "rate": 0.1, "units": "in"})
    assert device is not None
    rate = next(r for r in device.readings if r.sensor_key == "rate")
    assert rate.expose is True
    assert rate.device_class == "precipitation"
    assert rate.state_class == "measurement"
    assert rate.unique_id_parts == ("rain", "rate")


def test_rain_since_midnight_metadata() -> None:
    device = parse_message("arwn/rain/today", {"since_midnight": 0.5, "units": "in"})
    assert device is not None
    r = device.readings[0]
    assert r.expose is True
    assert r.device_class == "precipitation"
    assert r.state_class == "measurement"
    assert r.unique_id_parts == ("rain", "since_midnight")


def test_barometer_metadata() -> None:
    device = parse_message("arwn/barometer", {"pressure": 1013.25, "units": "mb"})
    assert device is not None
    r = device.readings[0]
    assert r.device_class is None
    assert r.state_class == "measurement"
    assert r.icon == "mdi:thermometer-lines"
    assert r.expose is True
    assert r.unique_id_parts == ("barometer", "pressure")


def test_all_exposed_readings_have_state_class() -> None:
    """Every exposed reading must have a non-empty state_class."""
    messages = [
        ("arwn/temperature/BackYard", {"temp": 72.5, "humid": 65.0, "units": "F"}),
        ("arwn/moisture/FrontLawn", {"moisture": 45.2, "units": "%"}),
        ("arwn/wind", {"speed": 12.3, "gust": 18.0, "direction": 270, "units": "mph"}),
        ("arwn/rain", {"total": 1.2, "rate": 0.1, "units": "in"}),
        ("arwn/rain/today", {"since_midnight": 0.5, "units": "in"}),
        ("arwn/barometer", {"pressure": 1013.25, "units": "mb"}),
    ]
    for topic, payload in messages:
        device = parse_message(topic, payload)
        assert device is not None
        for r in device.readings:
            if r.expose:
                assert r.state_class, f"{r.sensor_key} missing state_class"
```

- [ ] **Step 2: Run tests — all should pass**

```bash
uv run pytest tests/test_parser.py -v
```

Expected: all tests pass (29 original + ~10 new metadata tests).

- [ ] **Step 3: Run linting**

```bash
uv run ruff check . && uv run ruff format --check .
```

Expected: `All checks passed!`

- [ ] **Step 4: Commit tests**

```bash
git add tests/test_parser.py
git commit -m "test: add metadata field assertions for all sensor types"
```

---

## Task 4: Bump version to 0.2.0

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update version in `pyproject.toml`**

Change line:
```toml
version = "0.1.0"
```
to:
```toml
version = "0.2.0"
```

- [ ] **Step 2: Run full test suite**

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 3: Commit and push**

```bash
git add pyproject.toml
git commit -m "chore: bump version to 0.2.0"
git push
```

---

## Task 5: Update HA component — `manifest.json`

**Files:**
- Modify: `homeassistant/components/arwn/manifest.json`

Working directory for all HA tasks: `/home/sdague/code/homeassistant-core/`

- [ ] **Step 1: Add `arwn-client` to requirements**

The current `manifest.json` has no `requirements` key. Add it:

```json
{
  "domain": "arwn",
  "name": "Ambient Radio Weather Network",
  "codeowners": [],
  "config_flow": true,
  "dependencies": ["mqtt"],
  "documentation": "https://www.home-assistant.io/integrations/arwn",
  "integration_type": "hub",
  "iot_class": "local_push",
  "mqtt": ["arwn/#"],
  "quality_scale": "legacy",
  "requirements": ["arwn-client==0.2.0"]
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/sdague/code/homeassistant-core
git add homeassistant/components/arwn/manifest.json
git commit -m "feat(arwn): add arwn-client dependency"
```

---

## Task 6: Rewrite HA `sensor.py`

**Files:**
- Modify: `homeassistant/components/arwn/sensor.py`

- [ ] **Step 1: Replace `sensor.py` with the new implementation**

```python
"""Support for collecting data from the ARWN project."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from arwn_client import ArwnReading, parse_message

from homeassistant.components import mqtt
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import slugify
from homeassistant.util.json import json_loads_object

from .const import DOMAIN

if TYPE_CHECKING:
    from . import ArwnConfigEntry

_LOGGER = logging.getLogger(__name__)

TOPIC = "arwn/#"


def _unique_id(entry_id: str, *parts: str) -> str:
    """Build a stable unique ID scoped to the config entry."""
    return f"{entry_id}_{slugify('_'.join(parts))}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArwnConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the ARWN sensor platform."""

    @callback
    def async_sensor_event_received(msg: mqtt.ReceiveMessage) -> None:
        """Process MQTT events as sensors."""
        try:
            event = json_loads_object(msg.payload)
        except ValueError:
            _LOGGER.warning(
                "Invalid JSON in MQTT message on %s: %s", msg.topic, msg.payload
            )
            return

        device = parse_message(msg.topic, event)
        if device is None:
            return

        store = entry.runtime_data
        event_clean = {k: v for k, v in event.items() if k != "timestamp"}

        for reading in device.readings:
            if not reading.expose:
                continue

            unique_id = _unique_id(entry.entry_id, *reading.unique_id_parts)

            if unique_id not in store:
                device_info = DeviceInfo(
                    identifiers={(DOMAIN, _unique_id(entry.entry_id, device.device_key))},
                    name=device.device_name,
                )
                sensor = ArwnSensor(reading, unique_id, device_info)
                sensor.set_initial_event(event_clean)
                store[unique_id] = sensor
                _LOGGER.debug(
                    "Registering sensor %(name)s => %(event)s",
                    {"name": reading.sensor_name, "event": event_clean},
                )
                async_add_entities((sensor,), False)
            else:
                _LOGGER.debug(
                    "Recording sensor %(name)s => %(event)s",
                    {"name": reading.sensor_name, "event": event_clean},
                )
                store[unique_id].set_event(event_clean)

    entry.async_on_unload(
        await mqtt.async_subscribe(hass, TOPIC, async_sensor_event_received, 0)
    )


class ArwnSensor(SensorEntity):
    """Representation of an ARWN sensor."""

    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(
        self,
        reading: ArwnReading,
        unique_id: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        self._attr_name = reading.sensor_name
        self._attr_unique_id = unique_id
        self._state_key = reading.sensor_key
        self._attr_native_unit_of_measurement = reading.unit
        self._attr_device_info = device_info
        self._attr_icon = reading.icon
        self._attr_device_class = (
            SensorDeviceClass(reading.device_class) if reading.device_class else None
        )
        self._attr_state_class = SensorStateClass(reading.state_class)

    def set_initial_event(self, event: dict[str, Any]) -> None:
        """Set the initial state before the entity is registered."""
        ev: dict[str, Any] = dict(event)
        self._attr_extra_state_attributes = ev
        self._attr_native_value = ev.get(self._state_key)

    def set_event(self, event: dict[str, Any]) -> None:
        """Update the sensor with the most recent event."""
        ev: dict[str, Any] = dict(event)
        self._attr_extra_state_attributes = ev
        self._attr_native_value = ev.get(self._state_key)
        self.async_write_ha_state()
```

- [ ] **Step 2: Run the HA arwn tests**

```bash
cd /home/sdague/code/homeassistant-core
.venv/bin/python -m pytest tests/components/arwn/ -v
```

Expected: most tests pass. The `test_rain_sensor_discovery` test currently asserts `"TEST_ENTRY_ID_rain_total"` is present — it should now be absent (the `total` sensor is not exposed). Check that test next.

- [ ] **Step 3: Commit**

```bash
git add homeassistant/components/arwn/sensor.py
git commit -m "feat(arwn): replace discover_sensors with arwn-client parse_message"
```

---

## Task 7: Update HA tests for `expose=False` on `total`

**Files:**
- Modify: `tests/components/arwn/test_sensor.py`

- [ ] **Step 1: Update `test_rain_sensor_discovery`**

The current test asserts both `total` and `rate` are present. Replace it with a test that asserts `rate` is present and `total` is absent:

```python
async def test_rain_sensor_discovery(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
) -> None:
    """Test rain message creates rate sensor but not total (total is not exposed)."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    async_fire_mqtt_message(
        hass,
        "arwn/rain",
        '{"total": 1.2, "rate": 0.1, "units": "in"}',
    )
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    unique_ids = {
        e.unique_id
        for e in entity_registry.entities.values()
        if e.config_entry_id == config_entry.entry_id
    }
    assert "TEST_ENTRY_ID_rain_rate" in unique_ids
    assert "TEST_ENTRY_ID_rain_total" not in unique_ids
```

- [ ] **Step 2: Update `test_station_sensors_share_device` — entity count changes**

`total` is no longer exposed, so the station device now has 5 entities (speed, gust, direction, rate, pressure) instead of 6. Replace the full test:

```python
async def test_station_sensors_share_device(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
) -> None:
    """Test that wind, rain, and barometer share the Weather Station device."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    async_fire_mqtt_message(
        hass,
        "arwn/wind",
        '{"speed": 5.0, "gust": 8.0, "direction": 90, "units": "mph"}',
    )
    async_fire_mqtt_message(
        hass, "arwn/rain", '{"total": 0.5, "rate": 0.0, "units": "in"}'
    )
    async_fire_mqtt_message(
        hass, "arwn/barometer", '{"pressure": 1013.0, "units": "mb"}'
    )
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, "TEST_ENTRY_ID_station")}
    )
    assert device is not None
    assert device.name == "Weather Station"

    entity_registry = er.async_get(hass)
    entities = [
        e
        for e in entity_registry.entities.values()
        if e.config_entry_id == config_entry.entry_id and e.device_id == device.id
    ]
    assert len(entities) == 5  # speed, gust, direction, rate, pressure (total not exposed)
```

- [ ] **Step 3: Run all arwn tests**

```bash
cd /home/sdague/code/homeassistant-core
.venv/bin/python -m pytest tests/components/arwn/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Run ruff on the component**

```bash
.venv/bin/python -m ruff check homeassistant/components/arwn/ tests/components/arwn/
```

Expected: no issues.

- [ ] **Step 5: Commit**

```bash
git add tests/components/arwn/test_sensor.py
git commit -m "test(arwn): update rain tests to reflect total sensor not exposed"
```

---

## Verification

- [ ] **arwn-client: full test suite**

```bash
cd /home/sdague/code/arwn-client
uv run pytest -v
```

Expected: all tests pass (39+ tests).

- [ ] **arwn-client: lint**

```bash
uv run ruff check . && uv run ruff format --check .
```

Expected: `All checks passed!`

- [ ] **HA: full arwn test suite**

```bash
cd /home/sdague/code/homeassistant-core
.venv/bin/python -m pytest tests/components/arwn/ -v
```

Expected: all tests pass.

- [ ] **Push arwn-client**

```bash
cd /home/sdague/code/arwn-client && git push
```

- [ ] **Push homeassistant-core**

```bash
cd /home/sdague/code/homeassistant-core && git push
```
