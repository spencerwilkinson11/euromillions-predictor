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
    main_gap = {n: len(draws) + 1 for n in MAIN_RANGE}
    star_gap = {s: len(draws) + 1 for s in STAR_RANGE}

    for idx, draw in enumerate(draws):
        for n in draw.get("numbers", []):
            if main_gap[n] > len(draws):
                main_gap[n] = idx
        for s in draw.get("stars", []):
            if star_gap[s] > len(draws):
                star_gap[s] = idx

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
