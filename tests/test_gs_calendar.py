from datetime import date

from src.gs_compat.calendar import (
    Window,
    business_day_count,
    business_day_offset,
    date_range,
    is_business_day,
    prev_business_date,
)


def test_is_business_day():
    assert not is_business_day(date(2024, 7, 4)) # Independence Day
    assert not is_business_day(date(2024, 7, 6)) # Saturday
    assert is_business_day(date(2024, 7, 5)) # Friday

def test_prev_business_date():
    assert prev_business_date(date(2024, 7, 5)) == date(2024, 7, 3)
    assert prev_business_date(date(2024, 7, 8)) == date(2024, 7, 5)

def test_business_day_offset():
    assert business_day_offset(date(2024, 7, 3), 1) == date(2024, 7, 5)
    assert business_day_offset(date(2024, 7, 8), -1) == date(2024, 7, 5)
    assert business_day_offset(date(2024, 7, 3), 0) == date(2024, 7, 3)

def test_date_range():
    dr = date_range(date(2024, 7, 3), date(2024, 7, 8))
    assert dr == [date(2024, 7, 3), date(2024, 7, 5), date(2024, 7, 8)]

def test_window():
    w = Window(90)
    assert w.w == 90

def test_business_day_count():
    assert business_day_count(date(2024, 7, 3), date(2024, 7, 8)) == 3

def test_date_range_window():
    dr = date_range(date(2024, 7, 3), Window(2))
    assert dr == [date(2024, 7, 3), date(2024, 7, 5), date(2024, 7, 8)]
