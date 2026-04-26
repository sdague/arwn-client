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
