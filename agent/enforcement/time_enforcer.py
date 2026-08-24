"""
time_enforcer.py — Schedule and Operating Hours Time Rule Enforcement.

Evaluates system operating schedule rules based on day of week and allowed start/end time windows.
"""
import datetime


class TimeEnforcer:
    """
    Evaluates system time rules to enforce allowed operating schedules.
    """

    def check_time_rules(self, rules: list[dict]) -> tuple[bool, str]:
        """
        Evaluates time rules against current day of week and current time.

        Args:
            rules (list[dict]): List of rule dicts.

        Returns:
            tuple[bool, str]: (is_allowed, reason)
                (True, "Within allowed operating hours") if permitted.
                (False, "Outside allowed operating hours (theo lịch)") if restricted.
        """
        if not rules:
            return (True, "Within allowed operating hours")

        # Filter rules where rule_type == 'time'
        time_rules = [
            r for r in rules
            if str(r.get("rule_type") or r.get("type") or "").strip().lower() == "time"
        ]

        if not time_rules:
            return (True, "Within allowed operating hours")

        from utils.time_sync import SecureTime
        
        now = SecureTime.now()
        current_day = now.weekday()  # 0=Mon ... 6=Sun
        current_time = now.time()

        rules_for_today = False
        allowed_by_any = False

        for rule in time_rules:
            # Check day of week rule filter
            day_spec = rule.get("day_of_week")
            target_days = self._parse_days(day_spec)

            # If rule specifies target days and today is not included, skip this rule
            if target_days is not None and current_day not in target_days:
                continue

            allowed_start_raw = rule.get("allowed_start") or rule.get("start_time")
            allowed_end_raw = rule.get("allowed_end") or rule.get("end_time")

            if not allowed_start_raw or not allowed_end_raw:
                continue

            start_time = self._parse_time(allowed_start_raw)
            end_time = self._parse_time(allowed_end_raw)

            if start_time is None or end_time is None:
                continue

            rules_for_today = True

            # Check if current time is within allowed window
            if self._is_time_between(current_time, start_time, end_time):
                allowed_by_any = True
                break

        # If there are rules for today but none allow the current time, block it
        if rules_for_today and not allowed_by_any:
            return (False, "Outside allowed operating hours (theo lịch)")

        return (True, "Within allowed operating hours")

    def _parse_days(self, day_spec) -> set[int] | None:
        """Parses day specification into a set of integers (0=Mon..6=Sun)."""
        if day_spec is None or day_spec == "":
            return None

        day_map = {
            "mon": 0, "monday": 0,
            "tue": 1, "tuesday": 1,
            "wed": 2, "wednesday": 2,
            "thu": 3, "thursday": 3,
            "fri": 4, "friday": 4,
            "sat": 5, "saturday": 5,
            "sun": 6, "sunday": 6
        }

        days = set()
        if isinstance(day_spec, (list, tuple, set)):
            items = day_spec
        elif isinstance(day_spec, str) and "," in day_spec:
            items = day_spec.split(",")
        else:
            items = [day_spec]

        for item in items:
            if isinstance(item, int):
                if 0 <= item <= 6:
                    days.add(item)
            elif isinstance(item, str):
                cleaned = item.strip().lower()
                if cleaned.isdigit():
                    val = int(cleaned)
                    if 0 <= val <= 6:
                        days.add(val)
                elif cleaned in day_map:
                    days.add(day_map[cleaned])

        return days if days else None

    def _parse_time(self, time_val) -> datetime.time | None:
        """Parses HH:MM or HH:MM:SS string or datetime.time into datetime.time."""
        if isinstance(time_val, datetime.time):
            return time_val
        if not time_val or not isinstance(time_val, str):
            return None

        cleaned = time_val.strip()
        parts = cleaned.split(":")
        try:
            if len(parts) >= 2:
                hour = int(parts[0])
                minute = int(parts[1])
                second = int(parts[2]) if len(parts) > 2 else 0
                return datetime.time(hour, minute, second)
        except (ValueError, IndexError):
            pass
        return None

    def _is_time_between(
        self, current: datetime.time, start: datetime.time, end: datetime.time
    ) -> bool:
        """Determines if current time falls within start and end, accounting for overnight spans."""
        if start <= end:
            return start <= current <= end
        else:
            # Overnight interval (e.g. 22:00 to 06:00)
            return current >= start or current <= end


# Global default instance and function wrapper for simple functional calls
_default_time_enforcer = TimeEnforcer()


def check_time_rules(rules: list[dict]) -> tuple[bool, str]:
    """
    Evaluates time rules against current day and time.

    Args:
        rules (list[dict]): List of rule dicts.

    Returns:
        tuple[bool, str]: (is_allowed, reason)
    """
    return _default_time_enforcer.check_time_rules(rules)
