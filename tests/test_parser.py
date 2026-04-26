"""Tests for the ARWN MQTT message parser."""

from __future__ import annotations

import pytest

from pyarwn import ArwnDeviceType, ArwnReading, parse_message
from pyarwn._units import CELSIUS, DEGREE, FAHRENHEIT, INCHES, PERCENTAGE

# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------


def test_temperature_fahrenheit() -> None:
    readings = parse_message("arwn/temperature/BackYard", {"temp": 72.5, "units": "F"})
    assert len(readings) == 1
    r = readings[0]
    assert r.sensor_key == "temp"
    assert r.value == 72.5
    assert r.unit == FAHRENHEIT
    assert r.device_type == ArwnDeviceType.LOCATION
    assert r.device_name == "BackYard"
    assert r.sensor_name == "BackYard Temperature"


def test_temperature_celsius() -> None:
    readings = parse_message("arwn/temperature/FrontYard", {"temp": 22.0, "units": "C"})
    assert len(readings) == 1
    assert readings[0].unit == CELSIUS


def test_temperature_with_humidity() -> None:
    readings = parse_message(
        "arwn/temperature/BackYard", {"temp": 72.5, "humid": 55.0, "units": "F"}
    )
    assert len(readings) == 2
    keys = {r.sensor_key for r in readings}
    assert keys == {"temp", "humid"}
    humid = next(r for r in readings if r.sensor_key == "humid")
    assert humid.unit == PERCENTAGE
    assert humid.value == 55.0
    assert humid.sensor_name == "BackYard Humidity"
    assert humid.device_type == ArwnDeviceType.LOCATION


def test_temperature_no_humidity() -> None:
    readings = parse_message("arwn/temperature/BackYard", {"temp": 72.5, "units": "F"})
    assert all(r.sensor_key != "humid" for r in readings)


def test_temperature_missing_location_returns_empty() -> None:
    assert parse_message("arwn/temperature", {"temp": 72.5}) == []


# ---------------------------------------------------------------------------
# Moisture
# ---------------------------------------------------------------------------


def test_moisture() -> None:
    readings = parse_message(
        "arwn/moisture/FrontLawn", {"moisture": 45.2, "units": "%"}
    )
    assert len(readings) == 1
    r = readings[0]
    assert r.sensor_key == "moisture"
    assert r.value == 45.2
    assert r.device_type == ArwnDeviceType.LOCATION
    assert r.device_name == "FrontLawn"
    assert r.sensor_name == "FrontLawn Moisture"


def test_moisture_missing_location_returns_empty() -> None:
    assert parse_message("arwn/moisture", {"moisture": 45.2}) == []


# ---------------------------------------------------------------------------
# Wind
# ---------------------------------------------------------------------------


def test_wind() -> None:
    readings = parse_message(
        "arwn/wind", {"speed": 12.3, "gust": 18.0, "direction": 270, "units": "mph"}
    )
    assert len(readings) == 3
    keys = {r.sensor_key for r in readings}
    assert keys == {"speed", "gust", "direction"}
    for r in readings:
        assert r.device_type == ArwnDeviceType.STATION
        assert r.device_name == "Weather Station"

    direction = next(r for r in readings if r.sensor_key == "direction")
    assert direction.unit == DEGREE
    assert direction.value == 270

    speed = next(r for r in readings if r.sensor_key == "speed")
    assert speed.unit == "mph"


# ---------------------------------------------------------------------------
# Rain
# ---------------------------------------------------------------------------


def test_rain() -> None:
    readings = parse_message("arwn/rain", {"total": 1.2, "rate": 0.1, "units": "in"})
    assert len(readings) == 2
    keys = {r.sensor_key for r in readings}
    assert keys == {"total", "rate"}
    for r in readings:
        assert r.device_type == ArwnDeviceType.STATION


def test_rain_today() -> None:
    readings = parse_message("arwn/rain/today", {"since_midnight": 0.5, "units": "in"})
    assert len(readings) == 1
    r = readings[0]
    assert r.sensor_key == "since_midnight"
    assert r.unit == INCHES
    assert r.value == 0.5
    assert r.sensor_name == "Rain Since Midnight"
    assert r.device_type == ArwnDeviceType.STATION


# ---------------------------------------------------------------------------
# Barometer
# ---------------------------------------------------------------------------


def test_barometer() -> None:
    readings = parse_message("arwn/barometer", {"pressure": 1013.25, "units": "mb"})
    assert len(readings) == 1
    r = readings[0]
    assert r.sensor_key == "pressure"
    assert r.value == 1013.25
    assert r.unit == "mb"
    assert r.device_type == ArwnDeviceType.STATION
    assert r.sensor_name == "Barometer"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_unknown_domain_returns_empty() -> None:
    assert parse_message("arwn/unknown_sensor", {"value": 1.0}) == []


def test_too_short_topic_returns_empty() -> None:
    assert parse_message("arwn", {"temp": 72.5}) == []


def test_timestamp_in_payload_is_ignored() -> None:
    readings = parse_message(
        "arwn/temperature/BackYard",
        {"temp": 72.5, "units": "F", "timestamp": "2026-04-26T12:00:00"},
    )
    assert len(readings) == 1
    assert readings[0].value == 72.5


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
def test_all_sensor_types_return_readings(topic: str, payload: dict) -> None:
    assert len(parse_message(topic, payload)) >= 1


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
    for r in parse_message(topic, payload):
        assert isinstance(r, ArwnReading)
