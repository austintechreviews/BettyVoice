# BettyVoice

External voice assistant for VTOL VR. Receives telemetry from the BettyTelemetry mod, keeps the latest aircraft state, and answers queries via typed commands (voice input coming later).

## Quick Start

```bash
# Run the app
python -m betty_voice.main

# In another terminal, send test packets
python tools/send_fake_packet.py
```

## Commands

| Command | Description |
|---|---|
| `altitude` | Altitude and radar altitude |
| `speed` | Indicated airspeed in knots |
| `heading` | Current heading |
| `engines` | Engine 1 and 2 status |
| `apu` | APU status |
| `gear` | Landing gear state |
| `weapon` | Selected weapon, count, master arm |
| `countermeasures` | Flare and chaff counts |
| `fuel` | Fuel percentage |
| `status` | Full aircraft summary |
| `help` | List commands |
| `quit` | Exit |

## Telemetry

Listens on UDP `127.0.0.1:47777` for JSON packets matching the `betty.telemetry.v1` schema.

Connection status is shown in the prompt: `[online]`, `[stale]`, or `[offline]`.

## Testing Without VTOL VR

Run the fake packet sender:

```bash
python tools/send_fake_packet.py
```

It cycles through two sample packets showing different aircraft states (healthy flight and degraded/emergency).

## Project Structure

```
BettyVoice/
  pyproject.toml
  src/betty_voice/
    __init__.py
    main.py
    config.py
    telemetry_receiver.py
    state_store.py
    unit_conversions.py
    intent_router.py
    rule_engine.py
    tts.py
  tools/
    send_fake_packet.py
  tests/
```

## Running Tests

```bash
python -m pytest tests/
```
