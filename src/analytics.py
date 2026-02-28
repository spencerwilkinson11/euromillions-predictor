from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Iterable

MAIN_RANGE = list(range(1, 51))
STAR_RANGE = list(range(1, 13))


def parse_draw_date(draw: dict) -> str:
    """Return a user-friendly date string for a draw."""
    for key in ("date", "drawDate", "draw_date"):
        value = draw.get(key)
        if value:
            try:
                return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%Y-%m-%d")
            except ValueError:
                return str(value)
    return "Unknown date"


def flatten_draw_values(draws: Iterable[dict]) -> tuple[list[int], list[int]]:
    numbers, stars = [], []
    for draw in draws:
        numbers.extend(draw.get("numbers", []))
        stars.extend(draw.get("stars", []))
    return numbers, stars


def frequency_counter(draws: list[dict]) -> tuple[Counter, Counter]:
    numbers, stars = flatten_draw_values(draws)
    return Counter(numbers), Counter(stars)


def overdue_gaps(draws: list[dict]) -> tuple[dict[int, int], dict[int, int]]:
    """Gap is draw distance from most recent appearance (0 means in latest draw)."""
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

    def sort_key(draw: dict) -> tuple[int, str]:
        """Sort by draw date descending when available, otherwise preserve order."""
        for key in ("date", "drawDate", "draw_date"):
            value = draw.get(key)
            if value:
                return (1, str(value))
        return (0, "")

    ordered_draws = sorted(draws, key=sort_key, reverse=True)

    for idx, draw in enumerate(ordered_draws):
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
    return {
        "date": parse_draw_date(latest),
        "numbers": sorted(latest.get("numbers", [])),
        "stars": sorted(latest.get("stars", [])),
    }
