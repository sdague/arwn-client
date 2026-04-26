"""ARWN MQTT topic and payload parser."""

from __future__ import annotations

from typing import Any

from ._models import ArwnDeviceType, ArwnReading
from ._units import CELSIUS, DEGREE, FAHRENHEIT, INCHES, PERCENTAGE

STATION_NAME = "Weather Station"


def parse_message(topic: str, payload: dict[str, Any]) -> list[ArwnReading]:
    """Parse an ARWN MQTT message into a list of readings.

    Returns an empty list for unknown or malformed topics.
    """
    parts = topic.split("/")
    if len(parts) < 2:
        return []

    unit = payload.get("units", "")
    domain = parts[1]

    if domain == "temperature":
        if len(parts) < 3:
            return []
        name = parts[2]
        temp_unit = FAHRENHEIT if unit == "F" else CELSIUS
        readings: list[ArwnReading] = [
            ArwnReading(
                device_type=ArwnDeviceType.LOCATION,
                device_name=name,
                sensor_key="temp",
                sensor_name=f"{name} Temperature",
                value=payload["temp"],
                unit=temp_unit,
            )
        ]
        if "humid" in payload:
            readings.append(
                ArwnReading(
                    device_type=ArwnDeviceType.LOCATION,
                    device_name=name,
                    sensor_key="humid",
                    sensor_name=f"{name} Humidity",
                    value=payload["humid"],
                    unit=PERCENTAGE,
                )
            )
        return readings

    if domain == "moisture":
        if len(parts) < 3:
            return []
        name = parts[2]
        return [
            ArwnReading(
                device_type=ArwnDeviceType.LOCATION,
                device_name=name,
                sensor_key="moisture",
                sensor_name=f"{name} Moisture",
                value=payload["moisture"],
                unit=unit,
            )
        ]

    if domain == "rain":
        if len(parts) >= 3 and parts[2] == "today":
            return [
                ArwnReading(
                    device_type=ArwnDeviceType.STATION,
                    device_name=STATION_NAME,
                    sensor_key="since_midnight",
                    sensor_name="Rain Since Midnight",
                    value=payload["since_midnight"],
                    unit=INCHES,
                )
            ]
        return [
            ArwnReading(
                device_type=ArwnDeviceType.STATION,
                device_name=STATION_NAME,
                sensor_key="total",
                sensor_name="Total Rainfall",
                value=payload["total"],
                unit=unit,
            ),
            ArwnReading(
                device_type=ArwnDeviceType.STATION,
                device_name=STATION_NAME,
                sensor_key="rate",
                sensor_name="Rainfall Rate",
                value=payload["rate"],
                unit=unit,
            ),
        ]

    if domain == "barometer":
        return [
            ArwnReading(
                device_type=ArwnDeviceType.STATION,
                device_name=STATION_NAME,
                sensor_key="pressure",
                sensor_name="Barometer",
                value=payload["pressure"],
                unit=unit,
            )
        ]

    if domain == "wind":
        return [
            ArwnReading(
                device_type=ArwnDeviceType.STATION,
                device_name=STATION_NAME,
                sensor_key="speed",
                sensor_name="Wind Speed",
                value=payload["speed"],
                unit=unit,
            ),
            ArwnReading(
                device_type=ArwnDeviceType.STATION,
                device_name=STATION_NAME,
                sensor_key="gust",
                sensor_name="Wind Gust",
                value=payload["gust"],
                unit=unit,
            ),
            ArwnReading(
                device_type=ArwnDeviceType.STATION,
                device_name=STATION_NAME,
                sensor_key="direction",
                sensor_name="Wind Direction",
                value=payload["direction"],
                unit=DEGREE,
            ),
        ]

    return []
