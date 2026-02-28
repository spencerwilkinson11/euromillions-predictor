from __future__ import annotations

from collections import Counter
from typing import Iterable

from src.date_utils import format_uk_date

MAIN_RANGE = list(range(1, 51))
STAR_RANGE = list(range(1, 13))


def parse_draw_date(draw: dict) -> str:
    """Return a user-friendly date string for a draw."""
    for key in ("date", "drawDate", "draw_date"):
        value = draw.get(key)
        if value:
            return format_uk_date(value)
    return "Unknown date"


def flatten_draw_values(draws: Iterable[dict]) -> tuple[list[int], list[int]]:
    numbers, stars = [], []

    def _coerce_int(value: object) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    for draw in draws:
        for n in draw.get("numbers", []):
            n_int = _coerce_int(n)
            if n_int is not None:
                numbers.append(n_int)
        for s in draw.get("stars", []):
            s_int = _coerce_int(s)
            if s_int is not None:
                stars.append(s_int)
    return numbers, stars


def frequency_counter(draws: list[dict]) -> tuple[Counter, Counter]:
    numbers, stars = flatten_draw_values(draws)
    return Counter(numbers), Counter(stars)


def overdue_gaps(draws: list[dict]) -> tuple[dict[int, int], dict[int, int]]:
    """Gap is draw distance from most recent appearance (0 means in latest draw).

    Expects draws ordered newest-first.
    """
    default_gap = len(draws) + 1
    main_gap = {n: default_gap for n in MAIN_RANGE}
    star_gap = {s: default_gap for s in STAR_RANGE}

    def coerce_in_range(value: object, valid_range: range) -> int | None:
        if value is None:
            return None

        try:
            int_value = int(value)
        except (TypeError, ValueError):
            return None

        if int_value not in valid_range:
            return None
        return int_value

    for idx, draw in enumerate(draws):
        for n in draw.get("numbers", []):
            n_int = coerce_in_range(n, range(1, 51))
            if n_int is None:
                continue
            if main_gap.get(n_int, default_gap) == default_gap:
                main_gap[n_int] = idx
        for s in draw.get("stars", []):
            s_int = coerce_in_range(s, range(1, 13))
            if s_int is None:
                continue
            if star_gap.get(s_int, default_gap) == default_gap:
                star_gap[s_int] = idx

    return main_gap, star_gap


def top_n(counter: Counter, n: int, reverse: bool = True) -> list[int]:
    ordered = sorted(counter.items(), key=lambda item: item[1], reverse=reverse)
    return [value for value, _ in ordered[:n]]


def recent_draw_summary(draws: list[dict]) -> dict:
    if not draws:
        return {"date": "Unknown", "numbers": [], "stars": []}

    latest = draws[0]

    def _sorted_ints(values: list | None) -> list[int]:
        coerced: list[int] = []
        for value in values or []:
            try:
                coerced.append(int(value))
            except (TypeError, ValueError):
                continue
        return sorted(coerced)

    return {
        "date": parse_draw_date(latest),
        "numbers": _sorted_ints(latest.get("numbers")),
        "stars": _sorted_ints(latest.get("stars")),
    }
