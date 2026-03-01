from __future__ import annotations

from src.core.ports import JackpotMeta
from src.jackpot_service import get_live_jackpot


class LiveJackpotProvider:
    def get_jackpot(self) -> JackpotMeta:
        info = get_live_jackpot()
        return JackpotMeta(
            ok=info.ok,
            source=info.source,
            jackpot_amount=info.jackpot_amount,
            next_draw_date=info.next_draw_date,
            next_draw_day=info.next_draw_day,
            raw=info.raw,
            error=info.error,
        )
