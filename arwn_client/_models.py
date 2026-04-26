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


@dataclass
class ArwnDevice:
    """A physical device that owns one or more sensor readings."""

    device_key: str
    device_name: str
    readings: list[ArwnReading] = field(default_factory=list)
