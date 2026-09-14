"""
app_enforcer.py — Application Rule Enforcement Engine.

Monitors running processes, enforces banned application blocks, and tracks usage
time against daily limit thresholds.

SAFETY (Task 6): process matching is hardened so a loose substring rule can never
kill the OS or the agent itself:
  1. HARD_WHITELIST — OS-critical + agent processes are never matched/killed.
  2. Smart folder match — the exe path is split into path segments and matched
     segment-by-segment, so "pro" cannot hit "program files" but "minecraft" still
     matches "...\AppData\Roaming\.minecraft\runtime\java.exe".
  3. Min-length guard — a bare target shorter than 3 chars is ignored unless it
     ends in ".exe" (explicit exact file).
"""
import datetime
import os
import subprocess
import time

import psutil


# Tier 1 — processes that must never be killed, regardless of any rule.
HARD_WHITELIST = {
    "svchost.exe", "csrss.exe", "winlogon.exe", "wininit.exe", "smss.exe",
    "lsass.exe", "services.exe", "explorer.exe", "taskhost.exe",
    "taskhostw.exe", "dwm.exe", "conhost.exe", "fontdrvhost.exe",
    "sihost.exe", "ctfmon.exe", "registry", "system", "system idle process",
    "parentalcontrolagent.exe", "parentalcontrolwatchdog.exe", "updater.exe",
    "agent_check_good.exe",
}

# Minimum length for a fuzzy (substring) target unless it carries a ".exe" suffix.
MIN_TARGET_LEN = 3


def _split_path_segments(path: str) -> list[str]:
    """Split an absolute path into normalized lowercase segments (folders + file)."""
    segments = []
    for part in path.replace("/", "\\").split("\\"):
        part = part.strip()
        if part:
            segments.append(part.lower())
    return segments


def _is_system_protected(p_name: str, p_exe: str) -> bool:
    """True if the process is OS/agent core and must never be killed."""
    base = os.path.basename(p_name or "").lower()
    if base in HARD_WHITELIST:
        return True
    exe_base = os.path.basename(p_exe or "").lower()
    if exe_base in HARD_WHITELIST:
        return True
    # Fallback: any exe under System32 / Windows dirs that isn't a known app.
    if p_exe:
        segs = _split_path_segments(p_exe)
        if segs and segs[0] in ("c:", "c$"):
            # protect core OS binaries in case whitelist misses one
            if any(s in ("windows", "system32", "syswow64") for s in segs[:4]):
                return True
    return False


def _target_is_actionable(target_lower: str) -> bool:
    """Tier 3 guard: ignore overly short fuzzy targets unless it's an explicit file."""
    if target_lower.endswith(".exe"):
        return True
    return len(target_lower) >= MIN_TARGET_LEN


def _matches_target(target_lower: str, p_name_lower: str, p_exe_lower: str) -> bool:
    """
    Tier 2 matching:
      - exact process name (chrome.exe) OR
      - substring in process name (a short name) OR
      - segment-wise match in exe path (so "minecraft" matches
        "...\AppData\Roaming\.minecraft\runtime\java.exe" but "pro" does NOT match
        "c:\program files\...").
    """
    # Exact name match always allowed.
    if p_name_lower == target_lower:
        return True
    # Substring in process name (e.g. "minecraft" matching some exe named "minecraftlauncher.exe").
    if p_name_lower and target_lower in p_name_lower:
        return True
    # Smart folder match on the exe path segments.
    if p_exe_lower:
        segments = _split_path_segments(p_exe_lower)
        # Folders that must never be fuzzy-matched (system / program roots).
        _NO_FUZZ_FOLDERS = {
            "c:", "windows", "system32", "syswow64", "program files",
            "program files (x86)", "programdata", "users", "appdata",
            "local", "locallow", "roaming", "microsoft", "microsoft shared",
        }
        for i, seg in enumerate(segments):
            # Exact segment match: "minecraft" matches a folder/file literally
            # named "minecraft", "pro" does NOT match "program files".
            if seg == target_lower:
                return True
            # Fuzzy match inside the final file segment (name.exe) — e.g.
            # "minecraft" matches "minecraft.jar.exe".
            is_file_segment = (i == len(segments) - 1)
            if is_file_segment and len(seg) >= len(target_lower) and target_lower in seg:
                return True
            # Fuzzy match inside a NON-system folder segment too — e.g. a game
            # installed in "AppData\Roaming\.minecraft" still needs to match
            # "minecraft". Skip reserved system/program folders so "pro" can't hit
            # "program files" and "win" can't hit "windows".
            if not is_file_segment and seg not in _NO_FUZZ_FOLDERS:
                if len(seg) >= len(target_lower) and target_lower in seg:
                    return True
    return False


class AppEnforcer:
    """
    Enforces application rules against running processes on the host.
    """

    def __init__(self):
        # Tracker for cumulative usage: {(date_str, target): seconds}
        self._usage_tracker: dict[tuple[str, str], float] = {}
        self._last_check_time: float = time.time()

    def enforce_app_rules(
        self,
        running_processes: list[dict],
        rules: list[dict],
        alert_sender,
        device_id: str
    ) -> list[dict]:
        """
        Filters application rules, matches against running processes, kills prohibited
        processes, tracks usage against daily limits, and sends alerts.

        Args:
            running_processes (list[dict]): Running process dicts containing 'pid', 'name', 'exe'.
            rules (list[dict]): List of rule configurations.
            alert_sender: Alert sender object (with send_alert method) or callable.
            device_id (str): Unique device identifier for alert payload.

        Returns:
            list[dict]: List of enforcement actions taken.
        """
        actions_taken = []
        now = time.time()
        elapsed = now - self._last_check_time
        self._last_check_time = now

        # Normalize interval between 0 and 60 seconds
        if elapsed < 0 or elapsed > 60:
            elapsed = 5.0

        today_str = datetime.date.today().isoformat()

        if not running_processes or not rules:
            return actions_taken

        # Filter rules where rule_type == 'app'
        app_rules = [
            r for r in rules
            if str(r.get("rule_type") or r.get("type") or "").strip().lower() == "app"
        ]

        if not app_rules:
            return actions_taken

        for rule in app_rules:
            target = str(rule.get("target") or rule.get("process_name") or "").strip()
            if not target:
                continue

            target_lower = target.lower()

            # Tier 3: reject overly short fuzzy targets (unless explicit .exe).
            if not _target_is_actionable(target_lower):
                continue

            is_banned = bool(
                rule.get("is_banned")
                or rule.get("is_forbidden")
                or str(rule.get("category")).lower() == "forbidden"
            )

            daily_limit_minutes = rule.get("daily_limit_minutes") or rule.get("max_minutes_per_day") or 0
            try:
                daily_limit_minutes = float(daily_limit_minutes)
            except (ValueError, TypeError):
                daily_limit_minutes = 0.0

            # Match running processes with target (safe matching, see module docstring).
            matched_processes = []
            for proc in running_processes:
                p_name = str(proc.get("name") or "").strip()
                p_exe = str(proc.get("exe") or "").strip()

                p_name_lower = p_name.lower()
                p_exe_lower = p_exe.lower()

                # Tier 1: never touch OS/agent core processes.
                if _is_system_protected(p_name, p_exe):
                    continue

                if _matches_target(target_lower, p_name_lower, p_exe_lower):
                    matched_processes.append(proc)

            if not matched_processes:
                continue

            # Case 1: Application is banned
            if is_banned:
                for proc in matched_processes:
                    pid = proc.get("pid")
                    p_name = proc.get("name") or target
                    if self._kill_process(pid):
                        alert_msg = f"Blocked banned application: {p_name}"
                        self._send_alert(alert_sender, device_id, "banned_app_opened", alert_msg)
                        actions_taken.append({
                            "action": "killed_banned_app",
                            "pid": pid,
                            "process_name": p_name,
                            "target": target
                        })

            # Case 2: Daily usage limit set
            elif daily_limit_minutes > 0:
                key = (today_str, target_lower)
                accumulated_seconds = self._usage_tracker.get(key, 0.0) + elapsed
                self._usage_tracker[key] = accumulated_seconds

                used_minutes = accumulated_seconds / 60.0
                if used_minutes >= daily_limit_minutes:
                    for proc in matched_processes:
                        pid = proc.get("pid")
                        p_name = proc.get("name") or target
                        if self._kill_process(pid):
                            alert_msg = (
                                f"Blocked application exceeding daily limit ({daily_limit_minutes}m): {p_name}"
                            )
                            self._send_alert(alert_sender, device_id, "app_limit_exceeded", alert_msg)
                            actions_taken.append({
                                "action": "killed_limit_exceeded",
                                "pid": pid,
                                "process_name": p_name,
                                "target": target,
                                "used_minutes": round(used_minutes, 2),
                                "limit_minutes": daily_limit_minutes
                            })

        return actions_taken

    def _kill_process(self, pid: int) -> bool:
        """Kills process using psutil.Process(pid).kill() or taskkill /F /PID pid fallback."""
        if not pid:
            return False

        # Attempt 1: psutil
        try:
            p = psutil.Process(pid)
            p.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except Exception:
            pass

        # Attempt 2: taskkill command
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
            print(f"[AppEnforcer] Failed to send alert: {e}")


# Global default instance and function wrapper for simple functional calls
_default_app_enforcer = AppEnforcer()


def enforce_app_rules(
    running_processes: list[dict],
    rules: list[dict],
    alert_sender,
    device_id: str
) -> list[dict]:
    """
    Enforces application rules against running processes.

    Args:
        running_processes (list[dict]): Process dicts.
        rules (list[dict]): Rule dicts.
        alert_sender: Object or function to send alerts.
        device_id (str): Target device ID.

    Returns:
        list[dict]: List of enforcement actions taken.
    """
    return _default_app_enforcer.enforce_app_rules(running_processes, rules, alert_sender, device_id)
