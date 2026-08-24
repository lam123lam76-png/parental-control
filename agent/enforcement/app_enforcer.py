"""
app_enforcer.py — Application Rule Enforcement Engine.

Monitors running processes, enforces banned application blocks, and tracks usage
time against daily limit thresholds.
"""
import datetime
import subprocess
import time

import psutil


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

            # Match running processes with target (case-insensitive match or substring match)
            matched_processes = []
            for proc in running_processes:
                p_name = str(proc.get("name") or "").strip()
                p_exe = str(proc.get("exe") or "").strip()

                p_name_lower = p_name.lower()
                p_exe_lower = p_exe.lower()

                # Case-insensitive match or substring match
                if (
                    target_lower == p_name_lower
                    or target_lower in p_name_lower
                    or (p_exe_lower and target_lower in p_exe_lower)
                ):
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
