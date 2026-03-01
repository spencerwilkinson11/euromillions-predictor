from __future__ import annotations

from datetime import date, datetime, timezone

from src.core.models import Draw


DRAW_DATE_KEYS = ("date", "drawDate", "draw_date")
JACKPOT_KEYS = ("estimatedJackpot", "jackpot", "jackpotAmount", "topPrize", "jackpot_amount")


def parse_date_like(value: object) -> date | None:
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue

    return None


def draw_date_text(draw: dict) -> str:
    for key in DRAW_DATE_KEYS:
        value = draw.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def parse_draw_timestamp(draw: dict) -> float:
    for key in DRAW_DATE_KEYS:
        value = draw.get(key)
        parsed = parse_date_like(value)
        if parsed is None:
            continue
        return datetime(parsed.year, parsed.month, parsed.day, tzinfo=timezone.utc).timestamp()
    return float("-inf")


def normalize_int_list(values: list | None) -> list[int]:
    normalized: list[int] = []
    for value in values or []:
        try:
            normalized.append(int(value))
        except (TypeError, ValueError):
            continue
    return normalized


def normalize_draw_dict(draw: dict) -> dict:
    normalized = dict(draw)
    normalized["numbers"] = normalize_int_list(draw.get("numbers"))
    normalized["stars"] = normalize_int_list(draw.get("stars"))
    return normalized


def prepare_draws(draws: list[dict] | None, history_n: int) -> list[dict]:
    normalized = [normalize_draw_dict(draw) for draw in (draws or [])]
    ordered = sorted(normalized, key=parse_draw_timestamp, reverse=True)
    return ordered[:history_n]


def parse_optional_jackpot(draw: dict) -> int | None:
    for key in JACKPOT_KEYS:
        raw = draw.get(key)
        if raw in (None, ""):
            continue
        cleaned = "".join(ch for ch in str(raw) if ch.isdigit())
        if cleaned:
            return int(cleaned)
    return None


def draw_from_payload(payload: dict, *, source: str | None = None) -> Draw | None:
    draw_date = parse_date_like(draw_date_text(payload))
    if draw_date is None:
        return None

    return Draw(
        draw_date=draw_date,
        numbers=sorted(normalize_int_list(payload.get("numbers"))),
        stars=sorted(normalize_int_list(payload.get("stars"))),
        jackpot=parse_optional_jackpot(payload),
        source=source,
        source_draw_id=str(payload.get("drawNo") or payload.get("drawNumber") or "") or None,
    )


def draw_to_payload(draw: Draw) -> dict:
    return {
        "date": draw.draw_date.isoformat(),
        "numbers": list(draw.numbers),
        "stars": list(draw.stars),
        "jackpot": draw.jackpot,
        "source": draw.source,
        "drawNo": draw.source_draw_id,
    }
