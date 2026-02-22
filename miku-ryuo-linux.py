import hid
import time
import json
import psutil
from pynvml import *

import constants

VID = 0x0b05
PID = 0x1c76
REPORT_SIZE = 1024
MAGIC_BYTE = bytes([0x5A])

seq = 0

HANDSHAKE_COMMAND = bytes([0x00, 0x35])
CONFIG_COMMAND = bytes([0x02, 0xBF])
TELEMETRY_COMMAND = bytes([0x02, 0xED]) # This is also sometimes EE or EF, need to find out why

nvidia_gpu_detected = False
nvidia_gpu_handle = None

def pad_packet(packet):
    if len(packet) > REPORT_SIZE:
        raise ValueError("Packet exceeds 1024 bytes")
    return packet + b'\x00' * (REPORT_SIZE - len(packet))


def read_response(device, label=""):
    response = device.read(REPORT_SIZE, timeout=5000)
    # if response:
    #     print(f"{label} response:", bytes(response).hex())
    # else:
    #     print(f"{label} no response")


def calculate_checksum(data):
    return bytes([sum(data) & 0xFF])


def write_to_device(device, command, data):
    global seq

    packet_data = command + data
    checksum = calculate_checksum(packet_data)
    packet = MAGIC_BYTE + packet_data + checksum + MAGIC_BYTE
    packet = pad_packet(packet)

    device.write(packet)
    seq += 1


def send_handshake(device):
    global seq

    now = int(time.time() * 1000)

    header = (
        "POST conn 1\r\n"
        f"SeqNumber={seq}\r\n"
        f"Date={now}\r\n"
        "\r\n"
    )

    write_to_device(device, HANDSHAKE_COMMAND, header.encode())
    print("Handshake sent")
    read_response(device, "Handshake")


def send_config(device):
    global seq, nvidia_gpu_detected, nvidia_gpu_handle

    now = int(time.time() * 1000)

    payload = {
        "temperature": "Celsius",
        "waterBlockScreen": {
            "enable": True,
            "displayInSleep": True,
            "brightness": 100,
            "id": {
                "id": "Customization",
                "screenMode": "Full Screen",
                "playMode": "Single",
                "media": [
                    "Ryuo_IV_MIKU_WW_03.mp4",
                    "Ryuo_IV_MIKU_WW_01.mp4",
                    "Ryuo_IV_MIKU_WW_02.mp4",
                    "Ryuo_IV_MIKU_WW_04.mp4"
                ],
                "settings": {
                    "titleColor": "#00C5F7",
                    "contentColor": "#FFFFFF",
                    "filter": {
                        "value": None,
                        "opacity": 100
                    },
                    "badges": []
                },
                "sysinfoDisplay": [
                    constants.TELEMETRY_CPU_USAGE,
                    constants.TELEMETRY_GPU_USAGE,
                    constants.TELEMETRY_CPU_TEMPERATURE,
                    constants.TELEMETRY_DATE_TIME,
                    constants.TELEMETRY_GPU_TEMPERATURE,
                    constants.TELEMETRY_MOTHERBOARD_TEMPERATURE
                ],
                "timezone": "Europe/Amsterdam"
            }
        },
        "spec": {
            "cpu": "AMD Ryzen 7 7800X3D",
            "gpu": nvmlDeviceGetName(nvidia_gpu_handle) if nvidia_gpu_detected else "No GPU"
        }
    }

    json_data = json.dumps(payload, separators=(',', ':'))

    header = (
        "POST config 1\r\n"
        f"SeqNumber={seq}\r\n"
        f"Date={now}\r\n"
        "ContentType=json\r\n"
        f"ContentLength={len(json_data)}\r\n"
        "\r\n"
    )

    write_to_device(device, CONFIG_COMMAND, header.encode()  + json_data.encode())
    print("Config sent")
    read_response(device, "Config")


def get_cpu_stats():
    temps = psutil.sensors_temperatures()

    cpu_temp = 0
    cpu_pkg_temp = 0

    for sensor_name, sensor_data in temps.items():
        if sensor_name == 'k10temp':
            cpu_pkg_temp = sensor_data[0].current
            cpu_temp = sensor_data[1].current

    return (
        0, # TODO: round(psutil.getloadavg(), 0),
        round(psutil.cpu_percent(), 0),
        round(psutil.cpu_freq().current, 0),
        cpu_temp,
        cpu_pkg_temp,
    )


def get_gpu_stats():
    global nvidia_gpu_detected, nvidia_gpu_handle

    if not nvidia_gpu_detected:
        return None

    return (
        nvmlDeviceGetUtilizationRates(nvidia_gpu_handle),
        nvmlDeviceGetTemperature(nvidia_gpu_handle, NVML_TEMPERATURE_GPU),
        nvmlDeviceGetFanSpeed(nvidia_gpu_handle),
        nvmlDeviceGetClockInfo(nvidia_gpu_handle, NVML_CLOCK_GRAPHICS),
        round(nvmlDeviceGetPowerUsage(nvidia_gpu_handle) / 1024, 0)
    )

def send_telemetry(device):
    global seq

    now = int(time.time() * 1000)

    mem_stats = psutil.virtual_memory()
    cpu_stats = get_cpu_stats()
    gpu_stats = get_gpu_stats()

    payload = {
        "network": {
            "upload": 0,
            "download": 0
        },
        "memory": {
            "total": round(mem_stats.total / 1024 / 1024, 0),
            "used": round(mem_stats.used / 1024 / 1024, 0),
            "load": round(mem_stats.percent, 0),
            "temperature": 0,
            "speed": 0
        },
        "cpu": {
            "load": cpu_stats[0],
            "temperature": cpu_stats[3],
            "temperaturePackage": cpu_stats[4],
            "speedAverage": cpu_stats[2],
            "power": 0,
            "voltage": 0,
            "usage": cpu_stats[1]
        },
        "gpu": {
            "hasDedicated": True,
            "load": gpu_stats[0].gpu,
            "temperature": gpu_stats[1],
            "fan": gpu_stats[2],
            "speed": gpu_stats[3],
            "power": gpu_stats[4],
            "voltage": -1
        },
        "disk": {
            "total": 0,
            "used": 0,
            "load": 0,
            "activity": 0,
            "temperature": 0,
            "readSpeed": 0,
            "writeSpeed": 0
        },
        "fans": [],
        "motherboard": {
            "temperature": 0,
            "chipsetTemperature": 0
        },
        "timestamp": now
    }

    json_data = json.dumps(payload, separators=(',', ':'))

    header = (
        "STATE all 1\r\n"
        f"SeqNumber={seq}\r\n"
        f"Date={now}\r\n"
        "ContentType=json\r\n"
        f"ContentLength={len(json_data)}\r\n"
        "\r\n"
    )

    write_to_device(device, TELEMETRY_COMMAND, header.encode() + json_data.encode())
    print("Telemetry sent")
    read_response(device, "Telemetry")


def connect_to_device():
    device = hid.Device(vid=VID, pid=PID)
    device.nonblocking = False

    send_handshake(device)
    time.sleep(1)
    send_config(device)

    print("Connected to Hatsune Miku RYUO IV")

    return device


def detect_nvidia_gpu():
    global nvidia_gpu_detected, nvidia_gpu_handle

    try:
        nvmlInit()
        print(f"NVIDIA Driver Version: {nvmlSystemGetDriverVersion()}")
    except:
        return

    nvidia_gpu_detected = nvmlDeviceGetCount() > 0
    if nvidia_gpu_detected:
        nvidia_gpu_handle = nvmlDeviceGetHandleByIndex(0)
        print(f"NVIDIA GPU detected: {nvmlDeviceGetName(nvidia_gpu_handle)}")
    else:
        print("NVIDIA driver detected but no GPU was found")


def main():
    detect_nvidia_gpu()

    device = connect_to_device()
    time.sleep(1)

    print("Starting telemetry loop")

    while True:
        send_telemetry(device)
        time.sleep(1)


if __name__ == "__main__":
    main()