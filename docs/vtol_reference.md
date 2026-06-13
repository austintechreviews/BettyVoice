# VTOL VR Knowledge Reference For Betty

This file documents the local knowledge that Betty can use for VTOL VR
questions. The machine-readable version lives in
`src/betty_voice/data/vtol_reference.json`.

Betty treats this as game-helper reference data, not flight-critical truth. Exact
engagement decisions should still follow the in-game DLZ, seeker, radar, fuel,
and warning cues.

## Sources

- VTOL VR Steam page: https://store.steampowered.com/app/667970/VTOL_VR/
- VTOL VR DLC page: https://store.steampowered.com/dlc/667970/VTOL_VR/
- VTOL VR community wiki: https://vtolvr.wiki.gg/
- Flight manuals: https://vtolvr.wiki.gg/wiki/Flight_Manuals
- Weapon guidance: https://vtolvr.wiki.gg/wiki/Weapon_Guidance
- Missile evasion: https://vtolvr.wiki.gg/wiki/Missile_Evasion
- Tips and tricks: https://vtolvr.wiki.gg/wiki/Tips_%26_Tricks

## Aircraft Reference

| Aircraft | Role | Key Betty Use |
|---|---|---|
| F/A-26B | Air superiority, strike, SEAD | Default heavy A2A and multirole recommendation platform. 13 weapon hardpoints and 2 utility hardpoints. |
| F-45A | Stealth multirole STOVL | Recommend when stealth and sensor fusion matter more than payload. External stores trade stealth for capacity. |
| AV-42C | Tilt-jet VTOL/STOL/CTOL attack/transport | Recommend for VTOL transport/attack and austere landing tasks. |
| T-55 Tyro | Two-seat trainer/combat jet | Recommend for training, instruction, and mixed crew practice. |
| AH-94 | Two-seat attack helicopter | Recommend for hovering, close attack, and sensor/co-pilot coordination training. |
| EF-24G Mischief | Electronic warfare | Recommend for EW, emitter hunting, jamming, and two-seat tactical support. |

## Weapon Reference

| Weapon | Role | Betty Guidance |
|---|---|---|
| AIM-120C/D | Active radar A2A, medium range | Primary BVR pressure missile. Remind pilot to check DLZ/no-escape cues. |
| AIM-7 | Semi-active radar A2A | Lower-tech radar missile; requires support compared with active homing missiles. |
| AIM-9 / AIM-9+ | IR A2A, short range | Close-range self-defense and merge weapon. |
| AIRS-T | IR all-aspect A2A, short-medium range | Strong close/merge missile and preferred high-off-boresight option. |
| AIM-54 | Heavy active radar A2A, medium-long range | Long-range heavy missile; lower close-range usefulness. |
| AGM-65 | Optical fire-and-forget A/G | Useful tactical A/G missile. |
| AGM-88 | Passive radar homing A/G | SEAD/DEAD against emitting radars. |
| GBU-38 / GBU-39 | GPS guided bombs | Precision A/G against fixed points. |
| Mk-82 | Unguided bomb | Cheap ballistic bomb; requires manual delivery discipline. |

## F/A-26B Loadout Recommendations

### Balanced A2A CAP

Use this when the pilot asks for “recommended A2A loadout for FA-26B”.

- 6 AIM-120C or AIM-120D for BVR shots and pressure.
- 2 AIRS-T or AIM-9+ for close-in all-aspect/self-defense shots.
- External tank or conformal fuel tanks if the sortie is long.
- Gun as last-ditch close combat.

Tradeoff: good default PvE CAP/intercept setup. Tanks/CFT improve endurance but
hurt acceleration and turn performance.

### Light Fighter Sweep

- 4 AIM-120C/D.
- 4 AIRS-T.
- No tanks unless range demands it.

Tradeoff: better acceleration and agility, less BVR magazine depth.

### Self-Escort SEAD

- 4 AIM-120C.
- 2 AIRS-T or AIM-9+.
- 2 AGM-88.
- TGP if target ID or sensor work matters.

Tradeoff: useful when fighting through air threats before attacking SAM radars.

## Solver-Readable Performance Graphs

The JSON includes heuristic curves under `performance_graphs`. These are arrays
of `[x, y]` points intended for linear interpolation by a solver or local model.
Betty also has a live-context solver in `performance_solver.py` that reads the
current telemetry packet before answering questions like “optimal speed for
turning”.

### `fa26b_stores_drag_heuristic`

X axis is normalized drag/load:

- `0`: clean
- `1`: light A2A
- `2`: balanced A2A
- `3`: heavy multirole

Series:

- `acceleration_score`
- `sustained_turn_score`
- `endurance_score_with_tanks`

### `a2a_range_employment_heuristic`

X axis is range band:

- `0`: merge
- `1`: short
- `2`: medium
- `3`: medium-long

Series:

- `AIRS-T employment_score`
- `AIM-9 employment_score`
- `AIM-120C employment_score`
- `AIM-54 employment_score`

Use this to choose broad weapon classes. Do not present it as a real
probability-of-kill table.

## Context-Aware Turn Solver

When asked about turn speed, corner speed, rate fighting, dogfighting, or flap
configuration, Betty:

1. Identifies the aircraft from the question or current telemetry.
2. Reads current indicated airspeed from telemetry.
3. Estimates fuel/stores weight from `systems.fuel_percent`,
   `weapons.selected_weapon`, and `weapons.selected_weapon_count`.
4. Applies the aircraft turn profile and returns a target speed band.
5. Adds flap and technique advice for that aircraft.

Example answer shape:

```text
F/A-26B turn solver: aim for about 350 knots, usable band 315 to 385 knots.
Current speed is about 420 knots. Estimated weight 25000 kilograms. For
sustained rate, keep flaps up or auto...
```

The estimate is intentionally labeled as a heuristic because current telemetry
does not expose total stores weight, exact aircraft mass, or full drag state.

## Local Lesson Briefs

Betty should teach from local condensed lessons, not merely point to tutorials.
The JSON includes rephraseable lesson briefs for:

- Radar missile evasion.
- BVR air-to-air.
- F/A-26B turning.
- Case I carrier recovery.

The local model may rephrase these, but the deterministic lesson text is the
source of truth.

## Local LLM Routing

The local Qwen model is used only as a formatter. The deterministic
`VTOLKnowledgeBase` chooses facts and recommendations first. The formatter is
prompted to rewrite only the provided answer and is rejected if it invents new
numbers.

Recommended runtime:

```bash
betty-voice --llm --llm-base-url http://localhost:1234/v1 --llm-model qwen3.5-0.8b-optiq
```

Example questions:

- `recommend A2A loadout for FA-26B`
- `show FA-26B performance graph for solver`
- `what is AIM-120C`
- `how do I notch a radar missile`
- `where are tutorials`
