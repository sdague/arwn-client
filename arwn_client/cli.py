"""CLI for reading ARWN MQTT messages and printing device readings."""

from __future__ import annotations

import json
import sys

import click
import paho.mqtt.client as mqtt

from . import parse_message
from ._models import ArwnDevice

_DEFAULT_HOST = "localhost"
_DEFAULT_PORT = 1883
_TOPIC = "arwn/#"


def _print_device(device: ArwnDevice) -> None:
    click.echo(f"Device: {device.device_name} [{device.device_key}]")
    for r in device.readings:
        click.echo(f"  {r.sensor_name}: {r.value} {r.unit}")


@click.group()
def main() -> None:
    """ARWN client — read weather station data from MQTT."""


@main.command()
@click.option(
    "--host", default=_DEFAULT_HOST, show_default=True, help="MQTT broker host"
)
@click.option(
    "--port", default=_DEFAULT_PORT, show_default=True, help="MQTT broker port"
)
@click.option(
    "--count",
    default=0,
    help="Stop after receiving this many messages (0 = run forever)",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def listen(host: str, port: int, count: int, as_json: bool) -> None:
    """Subscribe to arwn/# and print device readings as they arrive."""
    received = [0]

    def on_message(client: mqtt.Client, userdata: None, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload)
        except (ValueError, UnicodeDecodeError):
            click.echo(f"Warning: invalid JSON on {msg.topic}", err=True)
            return

        device = parse_message(msg.topic, payload)
        if device is None:
            return

        if as_json:
            click.echo(
                json.dumps(
                    {
                        "device_key": device.device_key,
                        "device_name": device.device_name,
                        "readings": [
                            {
                                "sensor_key": r.sensor_key,
                                "sensor_name": r.sensor_name,
                                "value": r.value,
                                "unit": r.unit,
                            }
                            for r in device.readings
                        ],
                    }
                )
            )
        else:
            _print_device(device)

        received[0] += 1
        if count and received[0] >= count:
            client.disconnect()

    def on_connect(
        client: mqtt.Client,
        userdata: None,
        flags: dict,
        rc: int,
        properties: object = None,
    ) -> None:
        if rc != 0:
            click.echo(f"Failed to connect to {host}:{port} (rc={rc})", err=True)
            sys.exit(1)
        client.subscribe(_TOPIC)
        if not as_json:
            click.echo(f"Listening on {host}:{port} (arwn/#) ...")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(host, port)
        client.loop_forever()
    except (ConnectionRefusedError, OSError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
