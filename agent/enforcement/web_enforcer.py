"""
web_enforcer.py — Web Access Rule Enforcement Engine.

Detects active web browser windows, checks window titles against banned domain/URL rules,
closes browser windows or processes, and dispatches alerts.
"""
import subprocess

import psutil

# Supported web browser process names (case-insensitive)
DEFAULT_BROWSER_PROCESSES = {
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
    "iexplore.exe",
    "safari.exe",
    "vivaldi.exe",
    "tor.exe",
    "arc.exe",
}


class WebEnforcer:
    """
    Enforces web access rules by inspecting foreground browser window titles.
    """

    def __init__(self, browser_executables: set[str] | None = None):
        self.browsers = (
            set(b.lower() for b in browser_executables)
            if browser_executables
            else DEFAULT_BROWSER_PROCESSES
        )

    def enforce_web_rules(
        self,
        active_window,
        rules: list[dict],
        alert_sender,
        device_id: str
    ) -> list[dict]:
        """
        Evaluates web access rules against browser windows.

        Args:
            active_window (dict | list[dict]): Single window dict OR list of window dicts.
                                               Now supports checking ALL open browser windows,
                                               not only the foreground one.
            rules (list[dict]): List of rule configurations.
            alert_sender: Alert sender object (with send_alert method) or callable.
            device_id (str): Unique device identifier for alert payload.

        Returns:
            list[dict]: List of enforcement actions taken.
        """
        actions_taken = []

        if not active_window or not rules:
            return actions_taken

        # Normalize: accept either a single window dict or a list of window dicts
        if isinstance(active_window, dict):
            windows_to_check = [active_window]
        elif isinstance(active_window, (list, tuple)):
            windows_to_check = list(active_window)
        else:
            return actions_taken

        # Filter rules where rule_type == 'web'
        web_rules = [
            r for r in rules
            if str(r.get("rule_type") or r.get("type") or "").strip().lower() == "web"
        ]

        if not web_rules:
            return actions_taken

        # Track killed PIDs to avoid double-killing
        killed_pids: set[int] = set()

        for window in windows_to_check:
            if not window:
                continue

            process_name = str(window.get("process_name") or "").strip()
            window_title = str(window.get("window_title") or "").strip()
            pid = window.get("pid")

            # Skip non-browser windows
            if not process_name or process_name.lower() not in self.browsers:
                continue

            if not window_title:
                continue

            window_title_lower = window_title.lower()

            for rule in web_rules:
                target = str(
                    rule.get("target") or rule.get("url") or rule.get("domain") or ""
                ).strip()

                if not target:
                    continue

                is_banned = bool(
                    rule.get("is_banned")
                    or rule.get("is_forbidden")
                    or str(rule.get("category")).lower() == "forbidden"
                    or rule.get("is_blocked")
                )

                if not is_banned:
                    continue

                # Match target against window title.
                # Strategy 1: Direct substring match (e.g. target="youtube")
                # Strategy 2: Domain name without TLD (e.g. "youtube.com" → "youtube")
                target_lower = target.lower()
                # Strip common TLD suffixes for title matching
                target_stem = target_lower
                for tld in (".com", ".net", ".org", ".vn", ".io", ".co", ".tv", ".gg", ".me"):
                    if target_stem.endswith(tld):
                        target_stem = target_stem[: -len(tld)]
                        break

                matched = (target_lower in window_title_lower) or (
                    target_stem and target_stem in window_title_lower
                )

                if matched and pid and pid not in killed_pids:
                    if self._kill_process(pid):
                        killed_pids.add(pid)
                        alert_msg = f"Blocked web access: {target} in window '{window_title}'"
                        self._send_alert(
                            alert_sender, device_id, "banned_website_opened", alert_msg
                        )
                        actions_taken.append({
                            "action": "killed_browser_window",
                            "pid": pid,
                            "process_name": process_name,
                            "window_title": window_title,
                            "target": target
                        })
                        break  # Stop checking further rules for this window

        return actions_taken


    def _kill_process(self, pid: int) -> bool:
        """Kills browser process using psutil or taskkill fallback."""
        if not pid:
            return False

        try:
            p = psutil.Process(pid)
            p.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except Exception:
            pass

        try:
            res = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                text=True
            )
            return res.returncode == 0
        except Exception:
            return False

    def _send_alert(self, alert_sender, device_id: str, alert_type: str, message: str) -> None:
        """Sends alert via alert_sender object or callable."""
        if not alert_sender:
            return
        try:
            if hasattr(alert_sender, "send_alert") and callable(alert_sender.send_alert):
                alert_sender.send_alert(device_id, alert_type, message)
            elif callable(alert_sender):
                alert_sender(device_id, alert_type, message)
        except Exception as e:
            print(f"[WebEnforcer] Failed to send alert: {e}")


# Global default instance and function wrapper for simple functional calls
_default_web_enforcer = WebEnforcer()


def enforce_web_rules(
    active_window: dict | list[dict],
    rules: list[dict],
    alert_sender,
    device_id: str
) -> list[dict]:
    """
    Enforces web access rules against active browser window or all open browser windows.

    Args:
        active_window (dict | list[dict]): Window dict or list of window dicts.
        rules (list[dict]): Rule dicts.
        alert_sender: Object or function to send alerts.
        device_id (str): Target device ID.

    Returns:
        list[dict]: List of enforcement actions taken.
    """
    return _default_web_enforcer.enforce_web_rules(active_window, rules, alert_sender, device_id)
