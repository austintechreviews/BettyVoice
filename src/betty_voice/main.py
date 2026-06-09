"""BettyVoice main entry point - terminal dashboard + command loop."""

import sys

from .config import Config
from .state_store import StateStore
from .telemetry_receiver import TelemetryReceiver
from .intent_router import IntentRouter
from .rule_engine import RuleEngine
from .tts import get_tts


def main(config: Config = None) -> None:
    if config is None:
        config = Config()

    state = StateStore(
        stale_seconds=config.telemetry.stale_seconds,
        offline_seconds=config.telemetry.offline_seconds,
    )
    receiver = TelemetryReceiver(
        state_store=state,
        host=config.telemetry.host,
        port=config.telemetry.port,
    )
    router = IntentRouter(state_store=state)
    rules = RuleEngine(state_store=state)
    tts = get_tts(enabled=False)

    receiver.start()

    print("BettyVoice v0.1")
    print(f"Listening on {config.telemetry.host}:{config.telemetry.port}")
    print("Type help for commands.\n")

    try:
        while True:
            callouts = rules.check()
            for c in callouts:
                print(c)
                tts.speak(c)

            status = state.get_status_label()
            prompt = f"[{status}] > "

            try:
                cmd = input(prompt)
            except EOFError:
                break

            if not cmd.strip():
                continue

            result = router.handle(cmd)
            if result == "__QUIT__":
                break

            print(result)
            if result:
                tts.speak(result)

    except KeyboardInterrupt:
        print()
    finally:
        receiver.stop()
        print("BettyVoice stopped.")


if __name__ == "__main__":
    main()
