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

