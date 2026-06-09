# BettyVoice Implementation Plan

Project: **BettyVoice**  
Role: External voice assistant for VTOL VR  
Input: Telemetry from BettyTelemetry  
Output: Voice responses and callouts  
Principle: **smart outside the game, passive by default**

## 1. Purpose

BettyVoice is the external assistant. It receives telemetry from BettyTelemetry, keeps the latest aircraft state, answers voice queries, and provides callouts.

It does not run inside VTOL VR.

```text
BettyTelemetry UDP JSON
    ↓
BettyVoice TelemetryReceiver
    ↓
StateStore
    ↓
IntentRouter + RuleEngine
    ↓
TTS
```

## 2. Hard boundaries

BettyVoice must:

- Receive telemetry passively.
- Never write to game memory.
- Never control VTOL VR in the first design.
- Never fire weapons.
- Never move aircraft controls.
- Respect telemetry mode.
- Avoid PvP tactical recommendations in MP-safe mode.
- Keep callouts rate-limited.

BettyVoice may:

- Answer user questions.
- Summarise ownship/cockpit state.
- Repeat warnings.
- Provide workload-reduction callouts.
- Log telemetry locally if enabled.
- Provide more tactical help only in explicit training/PvE mode.

## 3. Main services

Suggested app layout:

```text
BettyVoice/
  src/
    main.py
    config.py
    telemetry_receiver.py
    state_store.py
    schema.py
    unit_conversions.py
    rule_engine.py
    intent_router.py
    speech_input.py
    tts_output.py
    packet_viewer.py
```

## 4. Service responsibilities

## 4.1 `TelemetryReceiver`

Responsibilities:

```text
bind UDP port 47777
receive JSON packets
parse schema
validate required fields
discard malformed packets
update StateStore
track packet age
```

Initial transport:

```text
UDP localhost 127.0.0.1:47777
```

## 4.2 `StateStore`

Responsibilities:

```text
hold latest telemetry packet
hold derived state
track stale/offline state
expose safe getters for intents/rules
```

Staleness rules:

```text
< 1 second old: online
1–5 seconds old: stale
> 5 seconds old: offline
```

## 4.3 `UnitConversions`

Responsibilities:

```text
m/s to knots
metres to feet
fuel fraction to percent
heading formatting
weapon count formatting
```

Conversions:

```text
knots = m/s * 1.94384
feet = metres * 3.28084
percent = fraction * 100
```

## 4.4 `IntentRouter`

Responsibilities:

```text
map voice/text intents to responses
pull current state
format concise pilot-friendly answers
```

Example intents:

```text
altitude
speed
heading
fuel
engines
apu
gear
weapon
stores
countermeasures
master arm
status
warnings
```

## 4.5 `RuleEngine`

Responsibilities:

```text
detect state changes
generate passive callouts
enforce cooldowns
respect mode
avoid spam
```

Callout categories:

```text
critical warnings
state changes
low resources
query responses
debug/status
```

## 4.6 `SpeechInput`

Responsibilities:

```text
wake word or push-to-talk
speech-to-text
intent text dispatch
```

Initial recommendation:

```text
push-to-talk or keyboard trigger first
wake word later
```

This avoids burning time on unreliable wake-word work before telemetry is useful.

## 4.7 `TTSOutput`

Responsibilities:

```text
speak responses
queue or interrupt messages
respect priority levels
avoid overlapping speech
```

Priority levels:

```text
critical: missile warning, engine failure
high: low fuel, gear warning
normal: query answer
low: debug/status
```

## 5. Operating modes

BettyVoice should mirror the telemetry mode.

## 5.1 `strict_stockish`

Voice can discuss:

```text
altitude
speed
heading
fuel
gear
engines
APU
master arm
selected weapon
weapon stocks
chaff/flares
own warnings
```

Voice must not discuss:

```text
enemy position
radar target list
nav target list
threat ranking
tactical suggestions
```

## 5.2 `mp_safe`

Voice can also discuss:

```text
missile warning
RWR spike state
friendly positions if exported
```

Voice should avoid:

```text
enemy tactical callouts
target prioritisation
BVR advice
fire/evasion recommendations
```

## 5.3 `training_pve`

Voice may discuss wider tactical state if telemetry provides it.

Possible:

```text
enemy radar contacts
locked target range/bearing
RWR emitter detail
training callouts
```

Still avoid initially:

```text
auto-fire logic
aim assist
hard tactical solver
```

## 6. Query response examples

### Altitude

Input:

```text
Betty, altitude.
```

Response:

```text
Altitude twelve thousand feet. Radar altitude three thousand.
```

### Speed

Input:

```text
Betty, speed.
```

Response:

```text
Speed four hundred twenty knots.
```

### Heading

Input:

```text
Betty, heading.
```

Response:

```text
Heading two seven zero.
```

### Fuel

Input:

```text
Betty, fuel.
```

Response:

```text
Fuel forty-two percent.
```

### Engines

Input:

```text
Betty, engines.
```

Response:

```text
Engine one online, engine two online. APU off.
```

### Weapon

Input:

```text
Betty, weapon.
```

Response:

```text
Selected AMRAAM. Two remaining. Master arm on.
```

### Countermeasures

Input:

```text
Betty, countermeasures.
```

Response:

```text
Flares twelve. Chaff twenty.
```

### Status

Input:

```text
Betty, status.
```

Response:

```text
Fuel forty-two percent. Engines online. Gear up. Master arm on. Selected AMRAAM, two remaining.
```

## 7. Passive callouts

## 7.1 State-change callouts

Examples:

```text
"Telemetry connected."
"Aircraft detected."
"Master arm on."
"Master arm safe."
"Gear down."
"Gear up."
"APU online."
"Engine one online."
"Engine two offline."
```

## 7.2 Warning callouts

Examples:

```text
"Missile warning."
"Engine one failure."
"Fuel low."
"Gear warning."
"Countermeasures low."
"Flares depleted."
```

## 7.3 Cooldowns

Recommended defaults:

| Callout | Cooldown |
|---|---:|
| missile warning | 5 s |
| RWR spike | 10 s |
| low fuel | 60 s |
| gear warning | 10 s |
| countermeasures low | 30 s |
| engine failure | 15 s |
| telemetry disconnected | 10 s |

## 8. Rule examples

### Low fuel

```text
if fuel_percent <= 30 and not announced_30:
    say "Fuel low, thirty percent."

if fuel_percent <= 15 and not announced_15:
    say "Fuel critical, fifteen percent."

if fuel_percent <= 5 and not announced_5:
    say "Fuel emergency, five percent."
```

### Gear warning

```text
if radar_altitude_ft < 500
and vertical_speed_fpm < -300
and gear_state != "extended":
    say "Gear warning."
```

### Countermeasures

```text
if flares == 0:
    say "Flares depleted."

if chaff == 0:
    say "Chaff depleted."

if flares <= low_threshold:
    say "Flares low."
```

### Engines

```text
if engine_1_enabled changed true -> false:
    say "Engine one offline."

if engine_1_rpm below expected while enabled:
    say "Engine one RPM low."
```

## 9. Config

Example `BettyVoice/config.json`:

```json
{
  "telemetry": {
    "host": "127.0.0.1",
    "port": 47777,
    "stale_seconds": 1.0,
    "offline_seconds": 5.0
  },
  "voice": {
    "input_mode": "push_to_talk",
    "wake_word": "Betty",
    "tts_voice": "default",
    "interruptible": true
  },
  "units": {
    "altitude": "feet",
    "speed": "knots",
    "vertical_speed": "feet_per_minute"
  },
  "callouts": {
    "enabled": true,
    "telemetry_status": true,
    "low_fuel": true,
    "gear_warning": true,
    "engine_warning": true,
    "countermeasure_warning": true,
    "missile_warning": true,
    "rwr_warning": true
  },
  "cooldowns_seconds": {
    "missile_warning": 5,
    "rwr_warning": 10,
    "low_fuel": 60,
    "gear_warning": 10,
    "countermeasures": 30,
    "engine_failure": 15
  }
}
```

## 10. Development phases

## Phase 1 — Packet viewer

Build:

```text
UDP receiver
JSON parser
terminal display
stale/offline indicator
```

No voice yet.

Acceptance:

```text
BettyTelemetry sends packets.
BettyVoice prints altitude/speed/heading.
```

## Phase 2 — Query system without speech

Build text command input:

```text
> altitude
> speed
> fuel
> weapon
> status
```

Acceptance:

```text
typed commands return correct responses
unit conversion works
offline/stale states handled
```

## Phase 3 — TTS

Add speech output.

Acceptance:

```text
typed command produces spoken response
callouts can speak
priority/cooldown works
```

## Phase 4 — Speech input

Add push-to-talk speech recognition.

Acceptance:

```text
spoken "Betty, speed" returns speed
spoken "Betty, status" returns status
```

## Phase 5 — Wake word

Optional.

Acceptance:

```text
wake word works without too many false positives
can disable wake word
push-to-talk remains available
```

## Phase 6 — Callout polish

Add:

```text
cooldowns
priority levels
interrupt rules
pilot-friendly wording
mode filtering
```

Acceptance:

```text
Betty is useful but not annoying
critical warnings interrupt
normal query answers do not spam
```

## 11. First build target

BettyVoice `v0.1` should not have speech recognition.

It should be:

```text
UDP receiver
terminal dashboard
typed command prompt
optional TTS
```

Minimum commands:

```text
altitude
speed
heading
status
```

Why:

```text
Telemetry correctness matters before voice.
Text commands are easier to debug.
TTS can be added before STT.
```

## 12. Recommended initial stack

Good simple stack:

```text
Python
asyncio
socket UDP receiver
pydantic or dataclasses for schema
pyttsx3 / system TTS / Piper for TTS
keyboard push-to-talk later
Whisper or local STT later
```

Alternative:

```text
Node.js
dgram UDP receiver
Web Speech or external STT
system TTS
```

Python is likely easier for quick hacking and later AI/LLM integration.

## 13. BettyVoice does not need to know VTOL internals

BettyVoice should only know the telemetry schema.

It should not care whether telemetry came from:

```text
VTOL VR mod
memory scanner
simulator replay
test fixture
```

That allows fake packet testing.

Test fixture:

```json
{
  "schema": "betty.telemetry.v1",
  "ownship": {
    "altitude_asl_m": 3048,
    "indicated_airspeed_ms": 216,
    "heading_deg": 270
  }
}
```

Expected response:

```text
Altitude ten thousand feet. Speed four hundred twenty knots. Heading two seven zero.
```

## 14. Definition of done

BettyVoice is acceptable when:

```text
It receives telemetry reliably.
It answers basic pilot queries.
It speaks useful callouts.
It respects telemetry mode.
It avoids tactical overreach in MP-safe mode.
It remains usable even if speech recognition is disabled.
```
