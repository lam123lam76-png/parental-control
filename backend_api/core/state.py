from typing import Dict

# Shared in-memory state
device_online_state: Dict[str, bool] = {}
device_graceful_shutdown: Dict[str, bool] = {}
version_replies: Dict[str, str] = {}
