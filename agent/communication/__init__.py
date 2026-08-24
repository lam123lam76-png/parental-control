"""
Communication module for Parental Control Agent.
Contains the 3-Stream Communication Engine:
- ws_client: Luồng 1 (Tuyến Sinh Tử) WebSocket Client
- alert_sender: Luồng 2 (Tuyến Báo Động) HTTP Alert Sender
- log_uploader: Luồng 3 (Tuyến Xe Tải) Batch Log Uploader
"""

from communication.alert_sender import AlertSender
from communication.log_uploader import LogUploader
from communication.ws_client import WebSocketClient

__all__ = ["AlertSender", "LogUploader", "WebSocketClient"]
