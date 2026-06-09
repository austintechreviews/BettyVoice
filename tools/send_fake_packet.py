#!/usr/bin/env python3
"""Send fake telemetry packets for testing BettyVoice."""

import json
import socket
import time

HOST = "127.0.0.1"
PORT = 47777

PACKETS = [
    {
        "schema": "betty.telemetry.v1",
        "timestamp_unix_ms": 0,
        "mode": "mp_safe",
        "aircraft": {"name": "FA-26B", "scene": "Practice Range"},
        "ownship": {
            "altitude_asl_m": 3048.0,
            "radar_altitude_m": 914.4,
            "indicated_airspeed_ms": 216.0,
            "airspeed_ms": 220.0,
            "vertical_speed_ms": 10.0,
            "heading_deg": 270.0,
            "pitch_deg": 2.0,
            "roll_deg": 0.0,
            "aoa_deg": 3.0,
            "player_gs": 1.0,
        },
        "systems": {
            "gear_state": "retracted",
            "apu_available": True,
            "apu_enabled": False,
            "apu_rpm": 0.0,
            "engine_1_available": True,
            "engine_1_enabled": True,
            "engine_1_failed": False,
            "engine_1_starting": False,
            "engine_1_started": True,
            "engine_1_rpm": 95.0,
            "engine_2_available": True,
            "engine_2_enabled": True,
            "engine_2_failed": False,
            "engine_2_starting": False,
            "engine_2_started": True,
            "engine_2_rpm": 94.0,
            "fuel_percent": 85.0,
        },
        "weapons": {
            "master_arm": True,
            "selected_weapon": "AIM-120C",
            "selected_weapon_count": 2,
            "chaff": 20,
            "flares": 12,
        },
        "warnings": {
            "missile_warning": False,
            "rwr_spike": False,
            "engine_warning": False,
            "fuel_warning": False,
        },
    },
    {
        "schema": "betty.telemetry.v1",
        "timestamp_unix_ms": 0,
        "mode": "mp_safe",
        "aircraft": {"name": "FA-26B", "scene": "Practice Range"},
        "ownship": {
            "altitude_asl_m": 1524.0,
            "radar_altitude_m": 1524.0,
            "indicated_airspeed_ms": 180.0,
            "airspeed_ms": 185.0,
            "vertical_speed_ms": -15.0,
            "heading_deg": 180.0,
            "pitch_deg": -3.0,
            "roll_deg": 10.0,
            "aoa_deg": 5.0,
            "player_gs": 1.2,
        },
        "systems": {
            "gear_state": "extended",
            "apu_available": True,
            "apu_enabled": True,
            "apu_rpm": 100.0,
            "engine_1_available": True,
            "engine_1_enabled": True,
            "engine_1_failed": False,
            "engine_1_starting": False,
            "engine_1_started": True,
            "engine_1_rpm": 88.0,
            "engine_2_available": True,
            "engine_2_enabled": False,
            "engine_2_failed": True,
            "engine_2_starting": False,
            "engine_2_started": False,
            "engine_2_rpm": 0.0,
            "fuel_percent": 42.0,
        },
        "weapons": {
            "master_arm": False,
            "selected_weapon": "AIM-9X",
            "selected_weapon_count": 1,
            "chaff": 3,
            "flares": 1,
        },
        "warnings": {
            "missile_warning": True,
            "rwr_spike": True,
            "engine_warning": True,
            "fuel_warning": False,
        },
    },
    {
        "schema": "betty.telemetry.v1",
        "timestamp_unix_ms": 0,
        "mode": "mp_safe",
        "aircraft": {"name": "AH-94", "scene": "Gulf of Aqaba"},
        "ownship": {
            "altitude_asl_m": 457.2,
            "radar_altitude_m": 457.2,
            "indicated_airspeed_ms": 120.0,
            "airspeed_ms": 122.0,
            "vertical_speed_ms": -5.0,
            "heading_deg": 45.0,
            "pitch_deg": -1.0,
            "roll_deg": 0.0,
            "aoa_deg": 4.0,
            "player_gs": 1.0,
        },
        "systems": {
            "gear_state": "extended",
            "apu_available": True,
            "apu_enabled": False,
            "apu_rpm": 0.0,
            "engine_1_available": True,
            "engine_1_enabled": True,
            "engine_1_failed": False,
            "engine_1_starting": False,
            "engine_1_started": True,
            "engine_1_rpm": 92.0,
            "engine_2_available": False,
            "engine_2_enabled": False,
            "engine_2_failed": False,
            "engine_2_starting": False,
            "engine_2_started": False,
            "engine_2_rpm": 0.0,
            "fuel_percent": 12.0,
        },
        "weapons": {
            "master_arm": False,
            "selected_weapon": "AGM-65",
            "selected_weapon_count": 4,
            "chaff": 0,
            "flares": 30,
        },
        "warnings": {
            "missile_warning": False,
            "rwr_spike": False,
            "engine_warning": False,
            "fuel_warning": True,
        },
    },
]


def main():
    interval = 0.5
    count = 0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"Sending fake packets to {HOST}:{PORT}")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            packet = PACKETS[count % len(PACKETS)]
            packet["timestamp_unix_ms"] = int(time.time() * 1000)
            data = json.dumps(packet).encode("utf-8")
            sock.sendto(data, (HOST, PORT))
            alt = packet["ownship"]["altitude_asl_m"]
            spd = packet["ownship"]["indicated_airspeed_ms"]
            hdg = packet["ownship"]["heading_deg"]
            print(f"Sent packet {count + 1} - alt={alt}m spd={spd}m/s hdg={hdg}")
            count += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
