"""Data models for ARWN sensor readings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ArwnDeviceType(StrEnum):
    """The type of physical device a reading belongs to."""

    LOCATION = "location"
    STATION = "station"


@dataclass
class ArwnReading:
    """A single sensor reading parsed from an ARWN MQTT message."""

    device_type: ArwnDeviceType
    device_name: str
    sensor_key: str
    sensor_name: str
    value: float | int
    unit: str
