from datetime import date

from src.core.draw_dates import upcoming_draw_dates
from src.core.draws import prepare_draws
from src.core.models import Line
from src.core.tickets import count_line_matches


def test_draw_date_parsing_and_sorting() -> None:
    draws = [
        {"date": "2026-03-03", "numbers": [1, "2", 3], "stars": [1, "2"]},
        {"drawDate": "01/03/2026", "numbers": [5, 6, 7], "stars": [3, 4]},
        {"draw_date": "2026-03-07T00:00:00Z", "numbers": [8, 9, 10], "stars": [5, 6]},
    ]

    prepared = prepare_draws(draws, history_n=3)

    assert [item.get("numbers") for item in prepared] == [
        [8, 9, 10],
        [1, 2, 3],
        [5, 6, 7],
    ]


def test_ticket_match_count() -> None:
    line = Line(main=[3, 11, 19, 27, 45], stars=[2, 9])

    matches = count_line_matches(line, winning_mains={11, 27, 42}, winning_stars={9, 12})

    assert matches == 3


def test_upcoming_draw_dates() -> None:
    draws = upcoming_draw_dates(date(2026, 3, 2), weeks=2)

    assert len(draws) == 4
    assert all(draw.weekday() in {1, 4} for draw in draws)
    assert draws[0] == date(2026, 3, 3)
