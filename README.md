# BettyVoice

External voice assistant for VTOL VR. Receives telemetry from the BettyTelemetry mod, keeps the latest aircraft state, and answers queries via typed or optional voice commands.

## Quick Start

```bash
# Run the app (typed commands only)
python -m betty_voice.main

# Or with voice input enabled
python -m betty_voice.main --voice
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
| `warnings` | Active warnings (missile, RWR, engine, fuel) |
| `status` | Full aircraft summary |
| `help` | List commands |
| `v` | Record voice command (when `--voice` is active) |
| `quit` | Exit |

## Testing Without VTOL VR

### Option 1: Send fake packets

```bash
# Send default FA-26B packet
python tools/send_fake_packet.py

# Select a scenario with overrides
python tools/send_fake_packet.py --scenario degraded --count 5 --rate 2
python tools/send_fake_packet.py --scenario helicopter --rate 1

# Override specific fields
python tools/send_fake_packet.py --speed 300 --altitude 5000 --fuel 50
python tools/send_fake_packet.py --gear extended --heading 180 --master-arm true
```

### Option 2: Replay a scenario

```bash
# Replay a takeoff sequence at 4 Hz
python tools/replay_packets.py scenarios/takeoff.jsonl

# Replay and loop a combat scenario faster
python tools/replay_packets.py scenarios/combat_warning.jsonl --rate 10 --loop

# Other scenarios:
#   scenarios/startup.jsonl        - Aircraft startup sequence
#   scenarios/takeoff.jsonl        - Takeoff and climb out
#   scenarios/engine_failure.jsonl - Engine failure events
#   scenarios/low_fuel.jsonl       - Decreasing fuel levels
#   scenarios/combat_warning.jsonl - RWR and missile warnings
#   scenarios/landing.jsonl        - Descent, gear down, touchdown
```

### Example test workflow

1. **Terminal 1**: Start BettyVoice
   ```bash
   python -m betty_voice.main
   ```

2. **Terminal 2**: Replay a scenario
   ```bash
   python tools/replay_packets.py scenarios/takeoff.jsonl --rate 4
   ```

3. Type commands in Terminal 1 to query aircraft state:
   ```
   [online] > speed
   Speed two hundred forty knots.
   [online] > altitude
   Altitude one thousand five hundred feet. Radar altitude one thousand five hundred feet.
   [online] > gear
   Gear down.
   [online] > warnings
   No warnings.
   ```

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

- "Betty speed" / "what's my speed" / "how fast am I going" → `speed`
- "what's my altitude" / "how high am I" → `altitude`
- "how much fuel" / "bingo fuel" → `fuel`
- "what weapon" / "what am I carrying" → `weapon`
- "flares" / "chaff" → `countermeasures`
- "engine status" → `engines`
- "warnings" / "any warnings" → `warnings`
- "how are we doing" / "what's my status" → `status`

### Graceful fallback

If voice dependencies are not installed, BettyVoice prints an install message
and continues in typed-command mode.

## Wake-Word Input (Experimental)

BettyVoice supports optional hands-free wake-word detection using
[openWakeWord](https://github.com/dscripka/openWakeWord) (on-device, no cloud).

When enabled, it continuously listens for a wake word. On detection it records
a short command, transcribes it, and routes it through the same command system.

### Install wake-word dependencies

All-in-one install (voice + wakeword):

```bash
pip install "betty-voice[voice,wakeword]"
```

Or manually:

```bash
pip install openwakeword sounddevice numpy faster-whisper soundfile
```

### Usage

```bash
betty-voice --wake-word
```

Behaviour:
1. BettyVoice starts telemetry receiver as normal.
2. Wake-word listener starts in a background thread.
3. Say the wake word (default: "hey jarvis").
4. App prints "Wake word detected." and records for 3 seconds.
5. Say a command like "speed" or "what's my altitude".
6. App transcribes, normalizes, and shows the response.
7. Typed commands and `v` (voice mode) still work alongside.

Optional flags:

| Flag | Default | Description |
|---|---|---|
| `--wake-word` | off | Enable wake-word detection |
| `--wake-word-threshold` | 0.5 | Detection sensitivity (lower = more sensitive) |
| `--wake-word-cooldown` | 2.0 | Seconds between detections |

### Graceful fallback

If openWakeWord or voice dependencies are missing, BettyVoice prints an install
message and continues in typed-command mode.

## Wake Phrase Input (Experimental — Whisper)

BettyVoice supports optional wake phrase spotting using the existing
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) pipeline (no
extra dependencies beyond the voice ones).

When enabled, it continuously records short audio chunks and transcribes
them.  If the transcript contains the wake phrase (default ``"betty"``),
it records a command clip, transcribes it, and routes it through the
same command system.

### Install dependencies

```bash
pip install "betty-voice[voice]"
```

### Usage

```bash
betty-voice --wake-word-mode whisper
```

Behaviour:
1. BettyVoice starts telemetry receiver as normal.
2. Wake phrase listener starts in a background thread.
3. Say "Betty" (or "hey Betty", "okay Betty").
4. App prints ``[wakephrase] Wake phrase detected: <transcript>``
   and records for 3 seconds.
5. Say a command like "speed" or "what's my altitude".
6. App prints ``[wakephrase] Recognized command: <text>``
7. The command is normalised and routed, and the response is shown.
8. Typed commands and ``v`` (voice mode) still work alongside.

Optional flags:

| Flag | Default | Description |
|---|---|---|
| ``--wake-word-mode`` | off | Set to ``whisper`` to enable |
| ``--wake-word-chunk-seconds`` | 2.0 | Length of each listening chunk |
| ``--wake-word-cooldown`` | 2.0 | Seconds between detections |

### Graceful fallback

If voice dependencies (sounddevice, faster-whisper) are missing,
BettyVoice prints an install message and continues in typed-command
mode.

### Performance note

Whisper ``tiny.en`` is used by default.  On most systems a 2-second
chunk transcribes in 0.5–2 seconds, so there is a small gap between
listening windows.  This is expected for an experimental feature.

## TTS Output (Experimental)

BettyVoice supports optional text-to-speech output using
[Piper](https://github.com/rhasspy/piper) (local, on-device, no cloud).

When enabled, responses are spoken aloud after being printed. Long responses
(e.g., help text) are spoken as a short summary.

### Install Piper

Download the `piper` executable and a voice model:

```bash
# Download piper for your platform from:
# https://github.com/rhasspy/piper/releases
#
# Download a voice model (.onnx + .json) from:
# https://huggingface.co/rhasspy/piper-voices
#
# Example (English US female voice):
# wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
# wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json
```

### Usage

```bash
betty-voice --tts --tts-voice /path/to/model.onnx
```

Optional flags:

| Flag | Default | Description |
|---|---|---|
| `--tts` | off | Enable TTS output |
| `--no-tts` | off | Explicitly disable TTS (overrides --tts) |
| `--tts-engine` | piper | TTS engine (only piper supported) |
| `--tts-voice` | None | Path to Piper voice model (.onnx) |

### Audio playback

PiperTTS tries these audio players in order:
1. `sounddevice` + `soundfile` (from `[voice]` deps) — best quality
2. `afplay` (macOS)
3. `paplay` / `aplay` (Linux)

If no player is found, TTS falls back to print-only mode.

### Graceful fallback

If the `piper` executable or voice model is missing, BettyVoice prints a setup
message and continues with printed-only responses.

## Telemetry

Listens on UDP `127.0.0.1:47777` for JSON packets matching the `betty.telemetry.v1` schema.

Connection status is shown in the prompt: `[online]`, `[stale]`, or `[offline]`.

## Number Formatting

Responses use full English words for readability:
- "Speed four hundred twenty knots."
- "Altitude twelve thousand feet."
- "Heading two seven zero." (digit-by-digit for headings)
- "Fuel forty-two percent."

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
    number_words.py
    intent_router.py
    rule_engine.py
    tts.py
    wake_word.py
    wake_phrase.py
  tools/
    send_fake_packet.py     # Send single test packets with overrides
    replay_packets.py       # Replay JSONL scenario files
  scenarios/
    startup.jsonl
    takeoff.jsonl
    engine_failure.jsonl
    low_fuel.jsonl
    combat_warning.jsonl
    landing.jsonl
  tests/
```

## Running Tests

```bash
python -m pytest tests/ -v
```
