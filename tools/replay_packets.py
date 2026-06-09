#!/usr/bin/env python3
"""Replay telemetry scenario JSONL files for testing BettyVoice.

Reads a .jsonl file and sends each line as a UDP JSON packet to BettyVoice.
Supports configurable rate, looping, and basic JSON validation.

Usage:
    python tools/replay_packets.py scenarios/takeoff.jsonl
    python tools/replay_packets.py scenarios/combat_warning.jsonl --rate 10 --loop
"""

import argparse
import json
import socket
import sys
import time

HOST = "127.0.0.1"
PORT = 47777


def validate_json(line: str, line_num: int) -> bool:
    try:
        obj = json.loads(line)
        if not isinstance(obj, dict):
            print(f"Line {line_num}: not a JSON object, skipping")
            return False
        return True
    except json.JSONDecodeError as e:
        print(f"Line {line_num}: invalid JSON - {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Replay telemetry scenario JSONL files"
    )
    parser.add_argument("file", help="Path to .jsonl scenario file")
    parser.add_argument(
        "--rate", type=float, default=4.0, help="Send rate in Hz (default: 4.0)"
    )
    parser.add_argument(
        "--loop", action="store_true", help="Loop the scenario indefinitely"
    )
    parser.add_argument(
        "--host", default=HOST, help=f"Target host (default: {HOST})"
    )
    parser.add_argument(
        "--port", type=int, default=PORT, help=f"Target port (default: {PORT})"
    )
    args = parser.parse_args()

    packets = []
    with open(args.file) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            if validate_json(line, i):
                packets.append(line)

    if not packets:
        print("No valid packets found.")
        sys.exit(1)

    print(f"Loaded {len(packets)} packet(s) from {args.file}")
    print(f"Sending to {args.host}:{args.port} at {args.rate} Hz")
    if args.loop:
        print("Looping enabled. Press Ctrl+C to stop.")

    interval = 1.0 / args.rate
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    total = 0

    try:
        while True:
            for i, line in enumerate(packets):
                try:
                    obj = json.loads(line)
                    obj["timestamp_unix_ms"] = int(time.time() * 1000)
                    data = json.dumps(obj).encode("utf-8")
                    sock.sendto(data, (args.host, args.port))
                    total += 1
                    print(f"Sent packet {total} (line {i + 1}/{len(packets)})")
                except (OSError, json.JSONDecodeError) as e:
                    print(f"Error sending packet {total + 1}: {e}")
                time.sleep(interval)
            if not args.loop:
                break
    except KeyboardInterrupt:
        print()
    finally:
        sock.close()
        print(f"Total: {total} packet(s) sent.")


if __name__ == "__main__":
    main()
