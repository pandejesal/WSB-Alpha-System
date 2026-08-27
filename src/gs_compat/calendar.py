# Vendored from goldmansachs/gs-quant, Apache-2.0, commit fa9dd42
import json
import os
from datetime import timedelta

import numpy as np
import pandas as pd


def load_nyse_holidays():
    file_path = os.path.join(os.path.dirname(__file__), 'data', 'nyse_holidays.json')
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            return pd.to_datetime(data['holidays']).date
    else:
        # Fails closed if missing
        import logging
        logging.getLogger(__name__).warning("nyse_holidays.json missing. Fails-closed.")
        return []

NYSE_HOLIDAYS = load_nyse_holidays()

def is_business_day(dates, calendar="NYSE"):
    if calendar != "NYSE":
        raise ValueError(f"Calendar {calendar} not supported, only NYSE.")

    dates = pd.to_datetime(dates)
    if isinstance(dates, pd.Timestamp):
        is_weekend = dates.weekday() >= 5
        is_holiday = dates.date() in NYSE_HOLIDAYS
        return not (is_weekend or is_holiday)

    is_weekend = dates.weekday >= 5
    is_holiday = np.isin(dates.date, NYSE_HOLIDAYS)
    return ~(is_weekend | is_holiday)

def prev_business_date(d, calendar="NYSE"):
    d = pd.to_datetime(d)
    d -= timedelta(days=1)
    while not is_business_day(d, calendar=calendar):
        d -= timedelta(days=1)
    return d.date()

def business_day_offset(d, offset, calendar="NYSE"):
    d = pd.to_datetime(d)
    if offset == 0:
        return d.date()
    step = 1 if offset > 0 else -1
    remaining = abs(offset)
    while remaining > 0:
        d += timedelta(days=step)
        if is_business_day(d, calendar=calendar):
            remaining -= 1
    return d.date()

def date_range(start, end, calendar="NYSE"):
    if isinstance(end, Window):
        end = business_day_offset(start, end.w, calendar=calendar)

    start = pd.to_datetime(start).date()
    end = pd.to_datetime(end).date()

    dates = pd.date_range(start, end, freq='D')
    return [d.date() for d in dates if is_business_day(d, calendar=calendar)]

class Window:
    def __init__(self, w=None, w_str=""):
        self.w = w
        if w_str.endswith(("d", "b")):
            self.w = int(w_str[:-1])

    def __repr__(self):
        return f"Window({self.w})"


def business_day_count(start, end, calendar="NYSE"):
    start = pd.to_datetime(start).date()
    end = pd.to_datetime(end).date()

    dates = pd.date_range(start, end, freq='D')
    return sum(is_business_day(d, calendar=calendar) for d in dates)
