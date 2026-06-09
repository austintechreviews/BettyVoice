# BettyVoice

External voice assistant for VTOL VR. Receives telemetry from the BettyTelemetry mod, keeps the latest aircraft state, and answers queries via typed or optional voice commands.

## Quick Start

```bash
# Run the app (typed commands only)
python -m betty_voice.main

# Or with voice input enabled
python -m betty_voice.main --voice

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
| `v` | Record voice command (when `--voice` is active) |
| `quit` | Exit |

## Voice Input (v0.2)

BettyVoice supports optional push-to-talk-style voice recognition using
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) (offline, no internet required).

### Install voice dependencies

```bash
pip install "betty-voice[voice]"
```

Or manually:

```bash
pip install sounddevice soundfile faster-whisper
```

### Usage

```bash
betty-voice --voice
```

While running, type `v` and press Enter to start a 3-second recording. Say
something like "Betty speed" or "what's my altitude". The app transcribes the
clip, normalizes the phrase, and routes it through the same command system as
typed input.

Optional flags:

| Flag | Default | Description |
|---|---|---|
| `--voice` | off | Enable voice input |
| `--voice-record-seconds` | 3.0 | Recording duration in seconds |

### Phrase normalization

Voice input strips the leading wake word "Betty" and maps common questions to
simple commands:

- "Betty speed" / "what's my speed" → `speed`
- "what's my altitude" / "altitude" → `altitude`
- "how much fuel" / "fuel" → `fuel`
- "what weapon" → `weapon`
- etc.

### Graceful fallback

If voice dependencies are not installed, BettyVoice prints an install message
and continues in typed-command mode.

## Telemetry

Listens on UDP `127.0.0.1:47777` for JSON packets matching the `betty.telemetry.v1` schema.

Connection status is shown in the prompt: `[online]`, `[stale]`, or `[offline]`.

## Testing Without VTOL VR

Run the fake packet sender:

```bash
python tools/send_fake_packet.py
```

It cycles through three sample packets showing different aircraft states (FA-26B healthy, FA-26B degraded, AH-94).

## Project Structure

```
BettyVoice/
  pyproject.toml
  src/betty_voice/
    __init__.py
    main.py
    config.py
    speech_input.py
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
