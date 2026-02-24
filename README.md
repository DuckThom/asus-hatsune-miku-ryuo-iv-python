# asus-hatsune-miku-ryuo-iv-python

Note: This script is very rough around the edges. It does not send all the telemetry data yet and it's very much built for my system only. However, the basics of setting up the connection, handshakes, checksums and data transmission are in place and working.

Requires the following packages:
- pynvml
- hid
- psutil

To run:
1. Set up a venv
2. Install the dependencies
3. Run `sudo bin/python3 miku-ryuo-linux.py` (Sudo is needed to open the hid device)

## What works?
- Initiating a connection to the device
- Sending metrics to the device (NOTE: The configuration command cannot be used as-is unless your device is using the exact same layout as my setup)
  - NVIDIA GPU's are supported, AMD GPU's are not atm.

## What does not work yet?
- Updating the device configuration, such as the location of the metrics and which metrics are displayed
  - Note: changing the order of `sysinfoDisplay` or changing it's values (Ie. changing `Motherboard Temperature` to `Memory Load`) does remove the "Motherboard" label on the device screen, but the metric it's displaying does not change.
- Uploading custom files to use as background

## Metrics

| Metric | Support | Note |
|--------|---------|------|
| Network | 🚫 | |
| Memory | ⚠️ | Total, Used and Load are available. Temperature and Speed are not |
| CPU | ⚠️ | Load, Temps, Speed and Usage are available. Power and Voltage are not |
| AMD GPU | 🚫 | |
| NVIDIA GPU | ⚠️ | Load, Temps, Fan speed, Speed and Power are available. Voltage is not. |
| Disk | 🚫 | |
| Fans | 🚫 | |
| Motherboard | 🚫 | |
