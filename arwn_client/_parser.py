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
            )
        )
        if "humid" in payload:
            device.readings.append(
                ArwnReading(
                    sensor_key="humid",
                    sensor_name=f"{name} Humidity",
                    value=payload["humid"],
                    unit=PERCENTAGE,
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
                    ),
                    ArwnReading(
                        sensor_key="rate",
                        sensor_name="Rainfall Rate",
                        value=payload["rate"],
                        unit=unit,
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
                ),
                ArwnReading(
                    sensor_key="gust",
                    sensor_name="Wind Gust",
                    value=payload["gust"],
                    unit=unit,
                ),
                ArwnReading(
                    sensor_key="direction",
                    sensor_name="Wind Direction",
                    value=payload["direction"],
                    unit=DEGREE,
                ),
            ]
        )
        return device

    return None
