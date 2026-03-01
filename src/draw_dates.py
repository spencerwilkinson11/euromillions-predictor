from __future__ import annotations

from datetime import date, timedelta


def is_draw_day(d: date) -> bool:
    """Return True when the date is a EuroMillions draw day (Tuesday or Friday)."""
    return d.weekday() in {1, 4}


def next_draw_date(from_date: date) -> date:
    """Return the next upcoming Tuesday/Friday draw date from the given date."""
    cursor = from_date
    while not is_draw_day(cursor):
        cursor += timedelta(days=1)
    return cursor


def upcoming_draw_dates(from_date: date, weeks: int = 12) -> list[date]:
    """Return all Tue/Fri draw dates across the requested upcoming week range."""
    total_draws = max(1, weeks) * 2
    cursor = next_draw_date(from_date)
    draws: list[date] = []

    while len(draws) < total_draws:
        if is_draw_day(cursor):
            draws.append(cursor)
        cursor += timedelta(days=1)

    return draws


def format_uk_draw_label(d: date) -> str:
    """Format draw date labels consistently for UI display."""
    return d.strftime("%a %d %b %Y")
