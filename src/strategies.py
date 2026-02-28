from __future__ import annotations

import random
from collections import Counter

from src.analytics import MAIN_RANGE, STAR_RANGE, overdue_gaps


STRATEGIES = [
    "AI Mode (Blend)",
    "Hot Numbers",
    "Cold Numbers",
    "Overdue (Longest gap)",
    "Balanced Picks",
]


def _safe_int_list(values: list) -> list[int]:
    safe_values: list[int] = []
    for value in values:
        try:
            safe_values.append(int(value))
        except (TypeError, ValueError):
            continue
    return safe_values


def _weighted_unique_pick(counter: Counter, k: int, invert: bool = False) -> list[int]:
    pool: dict[int, int] = {}
    for value, weight in dict(counter).items():
        try:
            value_int = int(value)
            weight_int = int(weight)
        except (TypeError, ValueError):
            continue
        pool[value_int] = max(1, weight_int)

    picked: list[int] = []

    for _ in range(min(k, len(pool))):
        choices = list(pool.keys())
        weights = [pool[c] for c in choices]
        if invert:
            max_weight = max(weights)
            weights = [max_weight - w + 1 for w in weights]

        selected = random.choices(choices, weights=weights, k=1)[0]
        picked.append(selected)
        pool.pop(selected)

    return sorted(picked)


def _balanced_main_pick() -> list[int]:
    decades = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 50)]
    picks = [random.randint(start, end) for start, end in decades]
    return sorted(picks)


def _balanced_star_pick() -> list[int]:
    return sorted([random.randint(1, 6), random.randint(7, 12)])


def build_line(strategy: str, main_counter: Counter, star_counter: Counter, draws: list[dict]) -> tuple[list[int], list[int]]:
    main_gap, star_gap = overdue_gaps(draws)

    if strategy == "Hot Numbers":
        main_nums = _weighted_unique_pick(main_counter, 5)
        stars = _weighted_unique_pick(star_counter, 2)
    elif strategy == "Cold Numbers":
        main_nums = _weighted_unique_pick(main_counter, 5, invert=True)
        stars = _weighted_unique_pick(star_counter, 2, invert=True)
    elif strategy == "Overdue (Longest gap)":
        main_nums = sorted([n for n, _ in sorted(main_gap.items(), key=lambda item: item[1], reverse=True)[:5]])
        stars = sorted([s for s, _ in sorted(star_gap.items(), key=lambda item: item[1], reverse=True)[:2]])
    elif strategy == "Balanced Picks":
        main_nums = _balanced_main_pick()
        stars = _balanced_star_pick()
    else:  # AI Mode (Blend)
        hot_main = _safe_int_list([n for n, _ in main_counter.most_common(12)])
        overdue_main = [n for n, _ in sorted(main_gap.items(), key=lambda item: item[1], reverse=True)[:12]]
        candidate_main = sorted(set(hot_main[:6] + overdue_main[:6] + MAIN_RANGE))
        main_nums = sorted(random.sample(candidate_main, k=5))

        hot_stars = _safe_int_list([s for s, _ in star_counter.most_common(6)])
        overdue_stars = [s for s, _ in sorted(star_gap.items(), key=lambda item: item[1], reverse=True)[:6]]
        candidate_stars = sorted(set(hot_stars[:3] + overdue_stars[:3] + STAR_RANGE))
        stars = sorted(random.sample(candidate_stars, k=2))

    return main_nums, stars


def explain_line(
    main_nums: list[int],
    stars: list[int],
    main_counter: Counter,
    star_counter: Counter,
    main_gap: dict[int, int],
    strategy: str,
) -> tuple[int, list[str]]:
    safe_main_nums = sorted(_safe_int_list(main_nums))
    safe_stars = sorted(_safe_int_list(stars))

    if len(safe_main_nums) < 2:
        return 0, ["Not enough valid numbers to explain this line."]

    hot_main = set(_safe_int_list([n for n, _ in main_counter.most_common(10)]))
    cold_main = set(_safe_int_list([n for n, _ in sorted(main_counter.items(), key=lambda item: item[1])[:10]]))
    overdue_main = set(_safe_int_list([n for n, _ in sorted(main_gap.items(), key=lambda item: item[1], reverse=True)[:10]]))

    hot_hits = len([n for n in safe_main_nums if n in hot_main])
    cold_hits = len([n for n in safe_main_nums if n in cold_main])
    overdue_hits = len([n for n in safe_main_nums if n in overdue_main])

    low_count = len([n for n in safe_main_nums if n <= 25])
    spread = max(safe_main_nums) - min(safe_main_nums)
    sequential_pairs = sum(1 for a, b in zip(safe_main_nums, safe_main_nums[1:]) if b - a == 1)

    score = 55
    if 2 <= low_count <= 3:
        score += 12
    if spread >= 25:
        score += 10
    if sequential_pairs == 0:
        score += 8
    if hot_hits >= 2:
        score += 8
    if cold_hits >= 1:
        score += 4
    if overdue_hits >= 1:
        score += 6

    score = min(100, max(0, score))

    explanations = [
        f"Includes {hot_hits} hot and {overdue_hits} overdue main numbers.",
        f"Range spread is {spread} with low/high split {low_count}/{5 - low_count}.",
    ]
    if sequential_pairs == 0:
        explanations.append("Avoids sequential clusters, a common human pick pattern.")
    else:
        explanations.append(f"Contains {sequential_pairs} sequential pair(s), keeping some natural adjacency.")

    if strategy == "Balanced Picks":
        explanations.insert(0, "Built to distribute picks across number decades.")
    elif strategy == "Overdue (Longest gap)":
        explanations.insert(0, "Prioritizes numbers with the longest gaps since last appearance.")
    elif strategy == "Cold Numbers":
        explanations.insert(0, "Leans into less frequent historical outcomes.")

    if safe_stars:
        hot_stars = set(_safe_int_list([s for s, _ in star_counter.most_common(4)]))
        star_hot_hits = len([s for s in safe_stars if s in hot_stars])
        explanations.append(f"Lucky stars include {star_hot_hits} from the recent high-frequency group.")

    return score, explanations[:4]
