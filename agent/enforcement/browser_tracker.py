"""
browser_tracker.py — Active Web Browser History Tracking Engine.

Captures active browser titles and URLs from Windows foreground window info
and uploads them to the Backend API.
"""
import logging
import urllib.parse
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

# Known Web Browsers Mapping
BROWSER_MAP = {
    "chrome.exe": "Chrome",
    "msedge.exe": "Edge",
    "brave.exe": "Brave",
    "coccoc.exe": "Cốc Cốc",
    "firefox.exe": "Firefox",
    "opera.exe": "Opera",
    "iexplore.exe": "Internet Explorer"
}

class BrowserTracker:
    def __init__(self, device_id: str, backend_url: str):
        self.device_id = device_id
        self.backend_url = backend_url.rstrip("/")
        self.last_logged_title = ""

    def process_active_window(self, active_window: dict):
        """
        Processes current active foreground window dict {"process_name": ..., "window_title": ...}.
        If it's a browser, extracts page title & domain URL and uploads to backend.
        """
        if not active_window or not active_window.get("process_name"):
            return

        proc_name = active_window["process_name"].lower()
        if proc_name not in BROWSER_MAP:
            return

        browser_displayName = BROWSER_MAP[proc_name]
        raw_title = active_window.get("window_title") or ""
        if not raw_title or raw_title == self.last_logged_title:
            return

        self.last_logged_title = raw_title

        # Clean title by removing trailing browser suffixes
        clean_title = raw_title
        for suffix in [" - Google Chrome", " - Microsoft Edge", " - Brave", " - Cốc Cốc", " - Mozilla Firefox", " - Opera"]:
            if clean_title.endswith(suffix):
                clean_title = clean_title[:-len(suffix)].strip()
                break

        # Infer URL or Domain from page title
        inferred_url = self._infer_url_from_title(clean_title)

        payload = {
            "device_id": self.device_id,
            "items": [
                {
                    "browser_name": browser_displayName,
                    "url": inferred_url,
                    "page_title": clean_title,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
        }

        try:
            url = f"{self.backend_url}/api/v1/logs/browser-history"
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                logger.info(f"[BrowserTracker] Logged browser activity: {browser_displayName} -> '{clean_title}' ({inferred_url})")
            else:
                logger.warning(f"[BrowserTracker] Failed upload (HTTP {resp.status_code})")
        except Exception as e:
            logger.error(f"[BrowserTracker] Exception uploading history: {e}")

    def _infer_url_from_title(self, title: str) -> str:
        """Helper to convert window title into clean URL/domain representation."""
        t_lower = title.lower()
        if "youtube" in t_lower:
            return "https://www.youtube.com"
        elif "facebook" in t_lower or "fb" in t_lower:
            return "https://www.facebook.com"
        elif "google" in t_lower:
            return "https://www.google.com"
        elif "wikipedia" in t_lower:
            return "https://vi.wikipedia.org"
        elif "github" in t_lower:
            return "https://github.com"
        elif "chatgpt" in t_lower or "openai" in t_lower:
            return "https://chatgpt.com"
        elif "tiktok" in t_lower:
            return "https://www.tiktok.com"
        elif "roblox" in t_lower:
            return "https://www.roblox.com"
        elif "." in title and not " " in title:
            return f"https://{title}"
        else:
            # Fallback search query format
            return f"https://www.google.com/search?q={urllib.parse.quote(title[:50])}"
