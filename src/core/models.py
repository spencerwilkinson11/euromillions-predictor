from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Draw:
    draw_date: date
    numbers: list[int]
    stars: list[int]
    jackpot: int | None = None
    source: str | None = None
    source_draw_id: str | None = None


@dataclass(frozen=True)
class Line:
    main: list[int]
    stars: list[int]


@dataclass(frozen=True)
class Ticket:
    id: str
    created_at: str
    draw_date: str
    draw_label: str
    strategy: str
    lines: list[Line] = field(default_factory=list)
    status: str = "Pending"
    notes: str = ""
