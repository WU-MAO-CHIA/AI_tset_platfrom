"""排程時間計算（spec 004）：純函式，不碰 DB。

排程的 time_of_day / weekdays 以 SCHEDULE_TIMEZONE 解讀，回傳值一律是 aware UTC。
"""

import re
from datetime import datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

FREQUENCIES = ("daily", "weekly", "interval")
MIN_INTERVAL_MINUTES = 15

_TIME_OF_DAY = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """SQLite 讀回的 DateTime 不帶時區；排程欄位寫入時一律是 UTC，視為 UTC。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validate_frequency(
    frequency: str,
    time_of_day: Optional[str],
    weekdays: Optional[list[int]],
    interval_minutes: Optional[int],
) -> None:
    """頻率設定不合法時拋 ValueError。"""
    if frequency not in FREQUENCIES:
        raise ValueError(f"frequency must be one of {', '.join(FREQUENCIES)}")
    if frequency in ("daily", "weekly"):
        if not time_of_day or not _TIME_OF_DAY.match(time_of_day):
            raise ValueError("time_of_day must be HH:MM")
    if frequency == "weekly":
        if not weekdays or any(not isinstance(d, int) or d < 0 or d > 6 for d in weekdays):
            raise ValueError("weekdays must be a non-empty list of 0 (Monday) .. 6 (Sunday)")
    if frequency == "interval":
        if not isinstance(interval_minutes, int) or interval_minutes < MIN_INTERVAL_MINUTES:
            raise ValueError(f"interval_minutes must be at least {MIN_INTERVAL_MINUTES}")


def compute_next_run(
    frequency: str,
    time_of_day: Optional[str],
    weekdays: Optional[list[int]],
    interval_minutes: Optional[int],
    after: datetime,
    tz_name: str,
) -> datetime:
    """回傳 after 之後（不含 after）的第一個排程時間（aware UTC）。"""
    validate_frequency(frequency, time_of_day, weekdays, interval_minutes)
    after = as_utc(after)

    if frequency == "interval":
        return after + timedelta(minutes=interval_minutes)

    tz = ZoneInfo(tz_name)
    hour, minute = (int(part) for part in time_of_day.split(":"))
    local_after = after.astimezone(tz)
    allowed = set(range(7)) if frequency == "daily" else set(weekdays)
    # 今天起往後 7 天內必有符合的日子（weekly 至少一天）；第 8 天涵蓋「今天已過、只排今天星期」的情況
    for offset in range(8):
        day = local_after.date() + timedelta(days=offset)
        if day.weekday() not in allowed:
            continue
        candidate = datetime.combine(day, time(hour, minute), tzinfo=tz).astimezone(timezone.utc)
        if candidate > after:
            return candidate
    raise AssertionError("unreachable: no schedule time within 8 days")
