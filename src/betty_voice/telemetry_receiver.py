"""TelemetryReceiver - listens for UDP JSON telemetry packets."""

import json
import socket
import threading
from typing import Callable, Optional

from .state_store import StateStore


class TelemetryReceiver:
    def __init__(
        self,
        state_store: StateStore,
        host: str = "0.0.0.0",
        port: int = 47777,
        source_host: str = "",
        on_packet: Optional[Callable[[dict], None]] = None,
    ):
        self._state = state_store
        self._host = host
        self._port = port
        self._source_host = source_host.strip()
        self._on_packet = on_packet
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.settimeout(0.5)
        self._sock.bind((self._host, self._port))
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._sock:
            self._sock.close()
        if self._thread:
            self._thread.join(timeout=2)

    def _listen(self) -> None:
        while self._running:
            try:
                data, addr = self._sock.recvfrom(65535)
                self._accept_packet(data, addr)
            except socket.timeout:
                continue
            except OSError:
                break

    def _accept_packet(self, data: bytes, addr: tuple[str, int]) -> None:
        if self._source_host and addr[0] != self._source_host:
            return
        self._handle_packet(data)

    def _handle_packet(self, data: bytes) -> None:
        try:
            packet = json.loads(data.decode("utf-8"))
            if isinstance(packet, dict):
                self._state.update(packet)
                if self._on_packet:
                    self._on_packet(packet)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
