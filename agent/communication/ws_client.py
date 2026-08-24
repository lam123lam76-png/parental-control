"""
ws_client.py - WebSocket Client for Luồng 1 (Tuyến Sinh Tử).

Target URL: {WS_URL}/ws/device/{device_id}?token={secret_token}
Maintains a daemon thread connection with exponential backoff (1s -> 2s -> 4s ... max 60s).
Heartbeat thread sending {"type": "heartbeat"} every HEARTBEAT_INTERVAL (15s).
Listens for server commands: {"type": "command", "command": "...", "payload": {...}}.
Allows registering command callbacks via register_command_callback(fn).
"""

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from enum import Enum

import websocket
from utils.backoff import ExponentialBackoff
from utils.logger import log_debug

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    ONLINE = 2
    BACKOFF = 3

class WebSocketClient:
    """
    Luồng 1 (Tuyến Sinh Tử) WebSocket Client.
    Manages a persistent, auto-reconnecting WebSocket connection to the backend server.
    """

    HEARTBEAT_INTERVAL = 15.0  # seconds (MUST BE < 30s for Cloudflare)

    def __init__(
        self,
        ws_url: str | None = None,
        device_id: str | None = None,
        secret_token: str | None = None,
        heartbeat_interval: float = HEARTBEAT_INTERVAL,
    ):
        from utils.config import WS_URL
        base_ws = (ws_url or WS_URL).strip()
        if base_ws.startswith("http://"):
            base_ws = "ws://" + base_ws[7:]
        elif base_ws.startswith("https://"):
            base_ws = "wss://" + base_ws[8:]

        self.ws_url = base_ws.strip().rstrip("/")
        self.device_id = (str(device_id or os.getenv("DEVICE_ID") or os.getenv("DEVICE_NAME", "May_Em_Trai"))).strip()
        self.secret_token = (str(secret_token or os.getenv("SECRET_TOKEN") or os.getenv("API_KEY") or "")).strip()
        self.heartbeat_interval = heartbeat_interval

        self._ws: websocket.WebSocketApp | None = None
        self._ws_thread: threading.Thread | None = None
        self._heartbeat_thread: threading.Thread | None = None

        self._running = False
        self._state = ConnectionState.DISCONNECTED
        self._backoff_strategy = ExponentialBackoff(initial_delay=2.0, max_delay=60.0, jitter=0.2)
        self._command_callbacks: list[Callable] = []
        self._lock = threading.Lock()

    def _build_url(self) -> str:
        url = f"{self.ws_url}/ws/device/{self.device_id}"
        if self.secret_token:
            url += f"?token={self.secret_token}"
        return url

    def register_command_callback(self, fn: Callable) -> None:
        """Register a callback function to handle server commands."""
        with self._lock:
            if fn not in self._command_callbacks:
                self._command_callbacks.append(fn)

    def is_connected(self) -> bool:
        """Return current WebSocket connection status."""
        return self._state == ConnectionState.ONLINE and self._running

    def start(self) -> None:
        """Start the WebSocket connection and heartbeat loops in daemon threads."""
        if self._running:
            return

        self._running = True
        self._ws_thread = threading.Thread(
            target=self._run_reconnect_loop,
            daemon=True,
            name="WSClient-ReconnectLoop"
        )
        self._ws_thread.start()
        log_debug("[WS_CLIENT] Engine started.")

    def stop(self) -> None:
        """Stop WebSocket client and cleanup connection."""
        log_debug("[WS_CLIENT] Stopping engine...")
        self._running = False
        self._state = ConnectionState.DISCONNECTED
        if self._ws:
            try:
                self._ws.close()
            except Exception as e:
                log_debug(f"[WS_CLIENT] Exception on ws close: {e}")
        log_debug("[WS_CLIENT] Engine stopped.")

    def _run_reconnect_loop(self) -> None:
        while self._running:
            url = self._build_url()
            self._state = ConnectionState.CONNECTING
            log_debug(f"[WS_CLIENT] Connecting to {url}...")

            try:
                self._ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )

                # run_forever blocks until connection closes or fails
                # Added ping_interval and ping_timeout to prevent half-open connections hanging forever
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                log_debug(f"[WS_CLIENT] Unexpected error in WebSocketApp: {e}")

            if not self._running:
                break

            self._state = ConnectionState.BACKOFF
            # Use exponential backoff with jitter
            self._backoff_strategy.wait()

    def _on_open(self, ws):
        log_debug("[WS_CLIENT] WebSocket connection established.")
        self._state = ConnectionState.ONLINE
        self._backoff_strategy.reset()  # Reset backoff on successful connection
        # Start heartbeat thread if not alive
        if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True,
                name="WSClient-Heartbeat"
            )
            self._heartbeat_thread.start()

    def _on_message(self, ws, message):
        log_debug(f"[WS_CLIENT] Message received: {message}")
        try:
            data = json.loads(message)
        except Exception as e:
            log_debug(f"[WS_CLIENT] Invalid JSON message: {e}")
            return

        msg_type = data.get("type")
        if msg_type == "command" or "command" in data:
            command = data.get("command", "")
            payload = data.get("payload", {})
            self._dispatch_command(command, payload, data)

    def _dispatch_command(self, command: str, payload: dict, full_msg: dict) -> None:
        with self._lock:
            callbacks = list(self._command_callbacks)

        for callback in callbacks:
            try:
                try:
                    callback(command, payload)
                except TypeError:
                    callback(full_msg)
            except Exception as e:
                log_debug(f"[WS_CLIENT] Error executing callback {callback}: {e}")

    def _on_error(self, ws, error):
        log_debug(f"[WS_CLIENT] WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        log_debug(f"[WS_CLIENT] WebSocket closed (code: {close_status_code}, msg: {close_msg}).")
        self._state = ConnectionState.DISCONNECTED

    def _heartbeat_loop(self) -> None:
        log_debug("[WS_CLIENT] Heartbeat loop started.")
        while self._running and self._state == ConnectionState.ONLINE:
            try:
                heartbeat_data = json.dumps({"type": "heartbeat"})
                if self._ws and self._state == ConnectionState.ONLINE:
                    self._ws.send(heartbeat_data)
                    log_debug("[WS_CLIENT] Heartbeat sent.")
            except Exception as e:
                log_debug(f"[WS_CLIENT] Failed to send heartbeat: {e}")
                self._state = ConnectionState.DISCONNECTED
                break

            # Sleep interruptible
            ticks = int(self.heartbeat_interval * 2)
            for _ in range(ticks):
                if not self._running or self._state != ConnectionState.ONLINE:
                    break
                time.sleep(0.5)
        log_debug("[WS_CLIENT] Heartbeat loop ended.")
