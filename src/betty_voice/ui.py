"""Dependency-free browser UI for BettyVoice settings and runtime control."""

from __future__ import annotations

import argparse
import json
import queue
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional

from .config import Config
from .runtime import BettyRuntime


class BettyUIState:
    def __init__(self):
        self.lock = threading.RLock()
        self.logs: list[str] = []
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.runtime: Optional[BettyRuntime] = None

    def log(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        line = f"[{stamp}] {message}"
        with self.lock:
            self.logs.append(line)
            self.logs = self.logs[-500:]
        self.log_queue.put(line)

    def is_running(self) -> bool:
        with self.lock:
            return bool(self.runtime and self.runtime.is_running)

    def status(self) -> dict[str, Any]:
        with self.lock:
            telemetry = self.runtime.status_label() if self.runtime else "offline"
            return {
                "running": bool(self.runtime and self.runtime.is_running),
                "telemetry": telemetry,
                "logs": list(self.logs[-200:]),
            }


class BettyUIHandler(BaseHTTPRequestHandler):
    state: BettyUIState

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self._send_html(_HTML)
        elif self.path == "/defaults":
            self._send_json(_config_to_payload(Config()))
        elif self.path == "/status":
            self._send_json(self.state.status())
        elif self.path == "/events":
            self._events()
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path == "/start":
            self._start()
        elif self.path == "/stop":
            self._stop()
        elif self.path == "/command":
            payload = self._read_json()
            command = str(payload.get("command", ""))
            self._run_async(lambda: self._runtime().handle_text(command))
            self._send_json({"ok": True})
        elif self.path == "/voice":
            self._run_async(lambda: self._runtime().trigger_voice())
            self._send_json({"ok": True})
        elif self.path == "/clear-logs":
            with self.state.lock:
                self.state.logs.clear()
            self._send_json({"ok": True})
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _start(self) -> None:
        payload = self._read_json()
        config = _payload_to_config(payload)
        with self.state.lock:
            if self.state.runtime and self.state.runtime.is_running:
                self._send_json({"ok": True, "already_running": True})
                return
            runtime = BettyRuntime(config, log=self.state.log)
            self.state.runtime = runtime
        try:
            runtime.start()
        except Exception as e:
            self.state.log(f"Failed to start Betty: {e}")
            with self.state.lock:
                self.state.runtime = None
            self._send_json({"ok": False, "error": str(e)}, status=500)
            return
        self._send_json({"ok": True})

    def _stop(self) -> None:
        runtime = None
        with self.state.lock:
            runtime = self.state.runtime
            self.state.runtime = None
        if runtime:
            runtime.stop()
        self._send_json({"ok": True})

    def _runtime(self) -> BettyRuntime:
        with self.state.lock:
            if not self.state.runtime or not self.state.runtime.is_running:
                raise RuntimeError("Betty is not running.")
            return self.state.runtime

    def _run_async(self, fn) -> None:
        def run() -> None:
            try:
                fn()
            except Exception as e:
                self.state.log(f"Action failed: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _events(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        for line in self.state.status()["logs"]:
            self._send_event(line)
        while True:
            try:
                line = self.state.log_queue.get(timeout=15)
                self._send_event(line)
            except queue.Empty:
                self._send_event("")
            except (BrokenPipeError, ConnectionResetError):
                return

    def _send_event(self, message: str) -> None:
        data = json.dumps(message)
        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
        self.wfile.flush()

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _config_to_payload(config: Config) -> dict[str, Any]:
    return {
        "telemetry_host": config.telemetry.host,
        "telemetry_port": config.telemetry.port,
        "telemetry_stale": config.telemetry.stale_seconds,
        "telemetry_offline": config.telemetry.offline_seconds,
        "voice_enabled": config.voice.enabled,
        "voice_record_seconds": config.voice.record_seconds,
        "voice_model": config.voice.model,
        "voice_device": config.voice.device,
        "voice_compute_type": config.voice.compute_type,
        "wake_word_enabled": config.wake_word.enabled,
        "wake_word_model": config.wake_word.model,
        "wake_word_threshold": config.wake_word.threshold,
        "wake_word_cooldown": config.wake_word.cooldown_seconds,
        "wake_phrase_enabled": config.wake_phrase.enabled,
        "wake_phrase": config.wake_phrase.phrase,
        "wake_phrase_chunk": config.wake_phrase.chunk_seconds,
        "tts_enabled": config.tts.enabled,
        "tts_voice": config.tts.voice_model_path or "",
        "tts_speed": config.tts.length_scale,
        "llm_enabled": config.llm.enabled,
        "llm_base_url": config.llm.base_url,
        "llm_model": config.llm.model,
        "llm_temperature": config.llm.temperature,
        "llm_max_tokens": config.llm.max_tokens,
        "callouts_enabled": config.callouts.enabled,
        "callout_missile": config.callouts.missile_warning,
        "callout_engine": config.callouts.engine_warning,
        "callout_countermeasures": config.callouts.low_countermeasures,
        "callout_telemetry": config.callouts.telemetry_status,
    }


def _payload_to_config(payload: dict[str, Any]) -> Config:
    config = Config()
    config.telemetry.host = str(payload.get("telemetry_host", config.telemetry.host))
    config.telemetry.port = int(payload.get("telemetry_port", config.telemetry.port))
    config.telemetry.stale_seconds = float(
        payload.get("telemetry_stale", config.telemetry.stale_seconds)
    )
    config.telemetry.offline_seconds = float(
        payload.get("telemetry_offline", config.telemetry.offline_seconds)
    )

    config.voice.enabled = bool(payload.get("voice_enabled", config.voice.enabled))
    config.voice.record_seconds = float(
        payload.get("voice_record_seconds", config.voice.record_seconds)
    )
    config.voice.model = str(payload.get("voice_model", config.voice.model))
    config.voice.device = str(payload.get("voice_device", config.voice.device))
    config.voice.compute_type = str(
        payload.get("voice_compute_type", config.voice.compute_type)
    )

    config.wake_word.enabled = bool(
        payload.get("wake_word_enabled", config.wake_word.enabled)
    )
    config.wake_word.model = str(payload.get("wake_word_model", config.wake_word.model))
    config.wake_word.threshold = float(
        payload.get("wake_word_threshold", config.wake_word.threshold)
    )
    config.wake_word.cooldown_seconds = float(
        payload.get("wake_word_cooldown", config.wake_word.cooldown_seconds)
    )

    config.wake_phrase.enabled = bool(
        payload.get("wake_phrase_enabled", config.wake_phrase.enabled)
    )
    config.wake_phrase.phrase = str(payload.get("wake_phrase", config.wake_phrase.phrase))
    config.wake_phrase.chunk_seconds = float(
        payload.get("wake_phrase_chunk", config.wake_phrase.chunk_seconds)
    )
    config.wake_phrase.cooldown_seconds = config.wake_word.cooldown_seconds

    config.tts.enabled = bool(payload.get("tts_enabled", config.tts.enabled))
    voice_path = str(payload.get("tts_voice", "")).strip()
    config.tts.voice_model_path = voice_path or None
    config.tts.length_scale = float(payload.get("tts_speed", config.tts.length_scale))

    config.llm.enabled = bool(payload.get("llm_enabled", config.llm.enabled))
    config.llm.base_url = str(payload.get("llm_base_url", config.llm.base_url))
    config.llm.model = str(payload.get("llm_model", config.llm.model))
    config.llm.temperature = float(
        payload.get("llm_temperature", config.llm.temperature)
    )
    config.llm.max_tokens = int(payload.get("llm_max_tokens", config.llm.max_tokens))

    config.callouts.enabled = bool(
        payload.get("callouts_enabled", config.callouts.enabled)
    )
    config.callouts.missile_warning = bool(
        payload.get("callout_missile", config.callouts.missile_warning)
    )
    config.callouts.engine_warning = bool(
        payload.get("callout_engine", config.callouts.engine_warning)
    )
    config.callouts.low_countermeasures = bool(
        payload.get("callout_countermeasures", config.callouts.low_countermeasures)
    )
    config.callouts.telemetry_status = bool(
        payload.get("callout_telemetry", config.callouts.telemetry_status)
    )
    return config


def run_server(host: str, port: int, open_browser: bool = True) -> ThreadingHTTPServer:
    state = BettyUIState()

    class Handler(BettyUIHandler):
        pass

    Handler.state = state
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{server.server_port}"
    state.log(f"BettyVoice UI available at {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        with state.lock:
            runtime = state.runtime
            state.runtime = None
        if runtime:
            runtime.stop()
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="BettyVoice browser control UI")
    parser.add_argument("--host", default="127.0.0.1", help="UI bind address")
    parser.add_argument("--port", type=int, default=8765, help="UI port")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser")
    args = parser.parse_args()
    try:
        run_server(args.host, args.port, open_browser=not args.no_browser)
    except KeyboardInterrupt:
        print()


_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BettyVoice Control</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f5f2;
      --panel: #ffffff;
      --line: #cfd4d2;
      --text: #1d2327;
      --muted: #66716f;
      --accent: #176b5c;
      --accent-dark: #0f4b41;
      --warn: #a13f2b;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); }
    header {
      height: 58px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 18px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfa;
    }
    h1 { margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0; }
    main {
      display: grid;
      grid-template-columns: minmax(340px, 420px) minmax(420px, 1fr);
      gap: 12px;
      padding: 12px;
      height: calc(100vh - 58px);
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      min-width: 0;
    }
    .settings { overflow: auto; padding: 12px; }
    .logPanel { display: grid; grid-template-rows: auto auto 1fr; min-height: 0; }
    .controls {
      display: grid;
      grid-template-columns: auto auto auto minmax(160px, 1fr) auto;
      gap: 8px;
      padding: 12px;
      border-bottom: 1px solid var(--line);
    }
    .statusbar {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      padding: 8px 12px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: 13px;
    }
    .log {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
      line-height: 1.45;
      overflow: auto;
      padding: 12px;
      white-space: pre-wrap;
      background: #101615;
      color: #dfe9e5;
      border-radius: 0 0 6px 6px;
    }
    details {
      border-top: 1px solid var(--line);
      padding: 10px 0;
    }
    details:first-child { border-top: 0; }
    summary { cursor: pointer; font-weight: 700; }
    .grid {
      display: grid;
      grid-template-columns: 150px minmax(0, 1fr);
      gap: 8px 10px;
      padding-top: 10px;
      align-items: center;
    }
    label { color: var(--muted); font-size: 13px; }
    input, select {
      width: 100%;
      min-width: 0;
      height: 34px;
      border: 1px solid var(--line);
      border-radius: 4px;
      padding: 6px 8px;
      background: #fff;
      color: var(--text);
    }
    input[type="checkbox"] { width: 18px; height: 18px; }
    .checkRow {
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 30px;
      color: var(--text);
    }
    button {
      height: 34px;
      border: 1px solid var(--accent);
      border-radius: 4px;
      padding: 0 12px;
      background: var(--accent);
      color: white;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: white; color: var(--accent-dark); }
    button.warn { background: var(--warn); border-color: var(--warn); }
    button:disabled { opacity: 0.55; cursor: default; }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; height: auto; }
      .logPanel { min-height: 520px; }
      .controls { grid-template-columns: 1fr 1fr; }
      .controls input { grid-column: 1 / -1; }
    }
  </style>
</head>
<body>
  <header>
    <h1>BettyVoice Control</h1>
    <div id="topStatus">Stopped</div>
  </header>
  <main>
    <section class="settings">
      <details open>
        <summary>Telemetry</summary>
        <div class="grid">
          <label>Address</label><input id="telemetry_host">
          <label>Port</label><input id="telemetry_port" type="number">
          <label>Stale seconds</label><input id="telemetry_stale" type="number" step="0.1">
          <label>Offline seconds</label><input id="telemetry_offline" type="number" step="0.1">
        </div>
      </details>
      <details open>
        <summary>Voice Input</summary>
        <div class="grid">
          <label>Push-to-talk</label><span class="checkRow"><input id="voice_enabled" type="checkbox"> Enabled</span>
          <label>Record seconds</label><input id="voice_record_seconds" type="number" step="0.1">
          <label>Whisper model</label><input id="voice_model">
          <label>Device</label><select id="voice_device"><option>auto</option><option>cpu</option><option>cuda</option></select>
          <label>Compute type</label><select id="voice_compute_type"><option>auto</option><option>float16</option><option>int8_float16</option><option>int8</option></select>
        </div>
      </details>
      <details open>
        <summary>Wake Modes</summary>
        <div class="grid">
          <label>Wake word</label><span class="checkRow"><input id="wake_word_enabled" type="checkbox"> Enabled</span>
          <label>Wake model</label><input id="wake_word_model">
          <label>Threshold</label><input id="wake_word_threshold" type="number" step="0.01">
          <label>Cooldown</label><input id="wake_word_cooldown" type="number" step="0.1">
          <label>Wake phrase</label><span class="checkRow"><input id="wake_phrase_enabled" type="checkbox"> Enabled</span>
          <label>Phrase</label><input id="wake_phrase">
          <label>Chunk seconds</label><input id="wake_phrase_chunk" type="number" step="0.1">
        </div>
      </details>
      <details open>
        <summary>Betty Voice</summary>
        <div class="grid">
          <label>Piper TTS</label><span class="checkRow"><input id="tts_enabled" type="checkbox"> Enabled</span>
          <label>Voice model</label><input id="tts_voice">
          <label>Speech speed</label><input id="tts_speed" type="number" step="0.05">
        </div>
      </details>
      <details open>
        <summary>Local AI Model</summary>
        <div class="grid">
          <label>Formatter/router</label><span class="checkRow"><input id="llm_enabled" type="checkbox"> Enabled</span>
          <label>Base URL</label><input id="llm_base_url">
          <label>Model</label><input id="llm_model">
          <label>Temperature</label><input id="llm_temperature" type="number" step="0.01">
          <label>Max tokens</label><input id="llm_max_tokens" type="number">
        </div>
      </details>
      <details>
        <summary>Callouts</summary>
        <div class="grid">
          <label>Passive callouts</label><span class="checkRow"><input id="callouts_enabled" type="checkbox"> Enabled</span>
          <label>Missile</label><input id="callout_missile" type="checkbox">
          <label>Engine</label><input id="callout_engine" type="checkbox">
          <label>Countermeasures</label><input id="callout_countermeasures" type="checkbox">
          <label>Telemetry</label><input id="callout_telemetry" type="checkbox">
        </div>
      </details>
    </section>
    <section class="logPanel">
      <div class="controls">
        <button id="start">Start Betty</button>
        <button id="stop" class="warn" disabled>Stop</button>
        <button id="voice" class="secondary">Voice</button>
        <input id="command" placeholder="Type a Betty command">
        <button id="send">Send</button>
      </div>
      <div class="statusbar">
        <span id="runtimeStatus">Runtime stopped</span>
        <button id="clear" class="secondary">Clear Log</button>
      </div>
      <div id="log" class="log"></div>
    </section>
  </main>
  <script>
    const fields = [
      "telemetry_host", "telemetry_port", "telemetry_stale", "telemetry_offline",
      "voice_enabled", "voice_record_seconds", "voice_model", "voice_device", "voice_compute_type",
      "wake_word_enabled", "wake_word_model", "wake_word_threshold", "wake_word_cooldown",
      "wake_phrase_enabled", "wake_phrase", "wake_phrase_chunk",
      "tts_enabled", "tts_voice", "tts_speed",
      "llm_enabled", "llm_base_url", "llm_model", "llm_temperature", "llm_max_tokens",
      "callouts_enabled", "callout_missile", "callout_engine", "callout_countermeasures", "callout_telemetry"
    ];
    const numeric = new Set([
      "telemetry_port", "telemetry_stale", "telemetry_offline", "voice_record_seconds",
      "wake_word_threshold", "wake_word_cooldown", "wake_phrase_chunk",
      "tts_speed", "llm_temperature", "llm_max_tokens"
    ]);
    const checks = new Set(fields.filter(id => document.getElementById(id)?.type === "checkbox"));
    const logEl = document.getElementById("log");

    function valueOf(id) {
      const el = document.getElementById(id);
      if (checks.has(id)) return el.checked;
      if (numeric.has(id)) return Number(el.value);
      return el.value;
    }
    function payload() {
      const out = {};
      for (const id of fields) out[id] = valueOf(id);
      return out;
    }
    function setDefaults(data) {
      for (const id of fields) {
        const el = document.getElementById(id);
        if (!el || !(id in data)) continue;
        if (checks.has(id)) el.checked = Boolean(data[id]);
        else el.value = data[id];
      }
    }
    function appendLog(line) {
      if (!line) return;
      logEl.textContent += line + "\n";
      logEl.scrollTop = logEl.scrollHeight;
    }
    async function post(path, body = {}) {
      const res = await fetch(path, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (!res.ok || data.ok === false) appendLog("[ui] " + (data.error || "request failed"));
      return data;
    }
    async function refreshStatus() {
      const data = await (await fetch("/status")).json();
      document.getElementById("start").disabled = data.running;
      document.getElementById("stop").disabled = !data.running;
      const text = data.running ? `Running - telemetry ${data.telemetry}` : "Stopped";
      document.getElementById("topStatus").textContent = text;
      document.getElementById("runtimeStatus").textContent = text;
    }
    document.getElementById("start").onclick = async () => { await post("/start", payload()); refreshStatus(); };
    document.getElementById("stop").onclick = async () => { await post("/stop"); refreshStatus(); };
    document.getElementById("voice").onclick = () => post("/voice");
    document.getElementById("send").onclick = () => {
      const input = document.getElementById("command");
      const command = input.value.trim();
      if (!command) return;
      input.value = "";
      post("/command", {command});
    };
    document.getElementById("command").addEventListener("keydown", event => {
      if (event.key === "Enter") document.getElementById("send").click();
    });
    document.getElementById("clear").onclick = async () => {
      logEl.textContent = "";
      await post("/clear-logs");
    };
    fetch("/defaults").then(r => r.json()).then(setDefaults);
    const events = new EventSource("/events");
    events.onmessage = event => appendLog(JSON.parse(event.data));
    refreshStatus();
    setInterval(refreshStatus, 1000);
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
