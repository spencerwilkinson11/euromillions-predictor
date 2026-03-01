from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.models import Draw, Ticket


@dataclass(frozen=True)
class JackpotMeta:
    ok: bool
    source: str
    jackpot_amount: str | None
    next_draw_date: str | None
    next_draw_day: str | None
    raw: str | None
    error: str | None


class DrawsProvider(Protocol):
    def fetch_draws(self) -> list[Draw]:
        ...


class JackpotProvider(Protocol):
    def get_jackpot(self) -> JackpotMeta:
        ...


class TicketStore(Protocol):
    def load(self) -> list[Ticket]:
        ...

    def save(self, tickets: list[Ticket]) -> None:
        ...
