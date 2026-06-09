#!/usr/bin/env python3
"""Send fake telemetry packets for testing BettyVoice.

Supports built-in scenarios and field overrides.

Usage:
    python tools/send_fake_packet.py
    python tools/send_fake_packet.py --scenario degraded --count 5 --rate 2
    python tools/send_fake_packet.py --speed 300 --altitude 5000 --fuel 50
"""

import argparse
import json
import socket
import time

HOST = "127.0.0.1"
PORT = 47777

SCENARIOS = {
    "default": {
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
    "degraded": {
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
    "helicopter": {
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
}


def apply_overrides(packet: dict, args: argparse.Namespace) -> dict:
    o = packet.setdefault("ownship", {})
    s = packet.setdefault("systems", {})
    w = packet.setdefault("weapons", {})

    if args.speed is not None:
        o["indicated_airspeed_ms"] = args.speed
    if args.altitude is not None:
        o["altitude_asl_m"] = args.altitude
        o["radar_altitude_m"] = args.altitude
    if args.fuel is not None:
        s["fuel_percent"] = args.fuel
    if args.weapon is not None:
        w["selected_weapon"] = args.weapon
    if args.chaff is not None:
        w["chaff"] = args.chaff
    if args.flares is not None:
        w["flares"] = args.flares
    if args.gear is not None:
        s["gear_state"] = args.gear
    if args.heading is not None:
        o["heading_deg"] = args.heading
    if args.master_arm is not None:
        w["master_arm"] = args.master_arm

    return packet


def main():
    parser = argparse.ArgumentParser(
        description="Send fake telemetry packets for BettyVoice"
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS),
        default="default",
        help="Built-in scenario to send (default: default)",
    )
    parser.add_argument(
        "--count", type=int, default=0, help="Number of packets to send (0 = infinite)"
    )
    parser.add_argument(
        "--rate", type=float, default=2.0, help="Send rate in Hz (default: 2.0)"
    )
    parser.add_argument("--speed", type=float, help="Override indicated airspeed (m/s)")
    parser.add_argument("--altitude", type=float, help="Override altitude ASL (m)")
    parser.add_argument("--fuel", type=float, help="Override fuel percent (0-100)")
    parser.add_argument("--weapon", type=str, help="Override selected weapon name")
    parser.add_argument("--chaff", type=int, help="Override chaff count")
    parser.add_argument("--flares", type=int, help="Override flare count")
    parser.add_argument("--gear", type=str, help="Override gear state")
    parser.add_argument("--heading", type=float, help="Override heading (degrees)")
    parser.add_argument(
        "--master-arm",
        dest="master_arm",
        type=lambda x: x.lower() in ("true", "1", "yes"),
        help="Override master arm (true/false)",
    )
    args = parser.parse_args()

    packet = SCENARIOS[args.scenario].copy()
    packet = apply_overrides(packet, args)

    interval = 1.0 / args.rate if args.rate > 0 else 0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    count = 0

    alt = packet["ownship"]["altitude_asl_m"]
    spd = packet["ownship"]["indicated_airspeed_ms"]
    hdg = packet["ownship"]["heading_deg"]
    print(f"Sending scenario '{args.scenario}' to {HOST}:{PORT}")
    print(f"  alt={alt:.0f}m  spd={spd:.0f}m/s  hdg={hdg}")
    print(f"  rate={args.rate} Hz  count={'unlimited' if args.count == 0 else args.count}")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            packet["timestamp_unix_ms"] = int(time.time() * 1000)
            data = json.dumps(packet).encode("utf-8")
            sock.sendto(data, (HOST, PORT))
            count += 1
            print(
                f"Sent packet {count} - "
                f"alt={packet['ownship']['altitude_asl_m']:.0f}m "
                f"spd={packet['ownship']['indicated_airspeed_ms']:.0f}m/s "
                f"hdg={packet['ownship']['heading_deg']:.0f}"
            )
            if 0 < args.count <= count:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print()
    finally:
        sock.close()
        print(f"Sent {count} packet(s).")


if __name__ == "__main__":
    main()
