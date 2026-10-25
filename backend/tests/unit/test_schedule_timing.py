"""spec 004：排程下次時間計算與頻率驗證。"""

from datetime import datetime, timezone

import pytest

from src.scheduling.timing import as_utc, compute_next_run, validate_frequency

TPE = "Asia/Taipei"  # UTC+8，無日光節約


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


class TestDaily:
    def test_later_today(self):
        # 台北 2026-10-25 09:00（UTC 01:00），排程台北 10:00 → 今天 UTC 02:00
        assert compute_next_run("daily", "10:00", None, None, utc(2026, 10, 25, 1, 0), TPE) == utc(2026, 10, 25, 2, 0)

    def test_already_passed_rolls_to_tomorrow(self):
        assert compute_next_run("daily", "02:00", None, None, utc(2026, 10, 25, 1, 0), TPE) == utc(2026, 10, 25, 18, 0)

    def test_exact_time_is_excluded(self):
        # 剛好在排程時間觸發後，下一次必須是隔天，否則會重複觸發
        assert compute_next_run("daily", "10:00", None, None, utc(2026, 10, 25, 2, 0), TPE) == utc(2026, 10, 26, 2, 0)

    def test_local_date_differs_from_utc_date(self):
        # UTC 10-25 20:00 已是台北 10-26 04:00；台北 02:00 已過 → 台北 10-27 02:00 = UTC 10-26 18:00
        assert compute_next_run("daily", "02:00", None, None, utc(2026, 10, 25, 20, 0), TPE) == utc(2026, 10, 26, 18, 0)

    def test_crosses_month_and_year(self):
        assert compute_next_run("daily", "08:00", None, None, utc(2026, 12, 31, 1, 0), TPE) == utc(2027, 1, 1, 0, 0)

    def test_utc_timezone(self):
        assert compute_next_run("daily", "02:00", None, None, utc(2026, 10, 25, 1, 0), "UTC") == utc(2026, 10, 25, 2, 0)


class TestWeekly:
    # 2026-10-25 是週日（weekday 6）
    def test_next_matching_weekday(self):
        # 週一、週三 09:00 → 台北 10-26（週一）09:00
        assert compute_next_run("weekly", "09:00", [0, 2], None, utc(2026, 10, 25, 4, 0), TPE) == utc(2026, 10, 26, 1, 0)

    def test_same_weekday_passed_waits_a_week(self):
        # 只排週日 09:00，台北現在週日 12:00 → 下週日
        assert compute_next_run("weekly", "09:00", [6], None, utc(2026, 10, 25, 4, 0), TPE) == utc(2026, 11, 1, 1, 0)

    def test_same_weekday_not_yet(self):
        assert compute_next_run("weekly", "18:00", [6], None, utc(2026, 10, 25, 4, 0), TPE) == utc(2026, 10, 25, 10, 0)


class TestInterval:
    def test_adds_minutes(self):
        assert compute_next_run("interval", None, None, 90, utc(2026, 10, 25, 1, 0), TPE) == utc(2026, 10, 25, 2, 30)

    def test_naive_after_is_treated_as_utc(self):
        assert compute_next_run("interval", None, None, 15, datetime(2026, 10, 25, 1, 0), TPE) == utc(2026, 10, 25, 1, 15)


class TestValidate:
    @pytest.mark.parametrize("args", [
        ("hourly", "10:00", None, None),
        ("daily", None, None, None),
        ("daily", "24:00", None, None),
        ("daily", "9:00", None, None),
        ("weekly", "09:00", [], None),
        ("weekly", "09:00", [7], None),
        ("interval", None, None, 14),
        ("interval", None, None, None),
    ])
    def test_invalid(self, args):
        with pytest.raises(ValueError):
            validate_frequency(*args)

    @pytest.mark.parametrize("args", [
        ("daily", "00:00", None, None),
        ("daily", "23:59", None, None),
        ("weekly", "09:30", [0, 6], None),
        ("interval", None, None, 15),
    ])
    def test_valid(self, args):
        validate_frequency(*args)


def test_as_utc_converts_aware_values():
    from zoneinfo import ZoneInfo
    assert as_utc(datetime(2026, 10, 25, 10, 0, tzinfo=ZoneInfo(TPE))) == utc(2026, 10, 25, 2, 0)
