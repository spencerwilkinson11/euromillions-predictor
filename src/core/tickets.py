from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import uuid

from src.core.models import Line, Ticket
from src.core.draws import parse_date_like


def as_iso_date(value: object) -> str | None:
    parsed = parse_date_like(value)
    return parsed.isoformat() if parsed else None


def safe_ticket_lines(lines: list[dict] | None) -> list[Line]:
    validated: list[Line] = []
    for line in lines or []:
        if not isinstance(line, dict):
            continue

        main_numbers = line.get("main", [])
        stars = line.get("stars", [])
        if not isinstance(main_numbers, list) or not isinstance(stars, list):
            continue

        try:
            main = sorted(int(v) for v in main_numbers)
            star_vals = sorted(int(v) for v in stars)
        except (TypeError, ValueError):
            continue

        validated.append(Line(main=main, stars=star_vals))

    return validated


def new_ticket(lines: list[dict], strategy: str, draw_date_iso: str, draw_label: str) -> Ticket:
    return Ticket(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
        draw_date=draw_date_iso,
        draw_label=draw_label,
        strategy=strategy,
        lines=safe_ticket_lines(lines),
        status="Pending",
        notes="",
    )


def count_line_matches(line: Line, winning_mains: set[int], winning_stars: set[int]) -> int:
    return sum(1 for value in line.main if value in winning_mains) + sum(1 for value in line.stars if value in winning_stars)


def prepare_ticket_match_rows(
    ticket: Ticket,
    *,
    winning_mains: set[int],
    winning_stars: set[int],
    should_check_matches: bool,
    pending_label: str | None = None,
) -> list[dict]:
    rows: list[dict] = []
    for line in ticket.lines[:5]:
        matched_mains = set(line.main) & winning_mains if should_check_matches else set()
        matched_stars = set(line.stars) & winning_stars if should_check_matches else set()
        rows.append(
            {
                "main": list(line.main),
                "stars": list(line.stars),
                "matched_mains": matched_mains,
                "matched_stars": matched_stars,
                "matches": count_line_matches(line, winning_mains, winning_stars) if should_check_matches else "—",
                "pending_label": pending_label,
            }
        )
    return rows


def ticket_to_dict(ticket: Ticket) -> dict:
    payload = asdict(ticket)
    payload["lines"] = [asdict(line) for line in ticket.lines]
    return payload


def ticket_from_dict(payload: dict) -> Ticket | None:
    if not isinstance(payload, dict):
        return None

    lines = safe_ticket_lines(payload.get("lines", []))
    return Ticket(
        id=str(payload.get("id") or str(uuid.uuid4())),
        created_at=str(payload.get("created_at") or datetime.now(timezone.utc).isoformat()),
        draw_date=str(payload.get("draw_date") or ""),
        draw_label=str(payload.get("draw_label") or ""),
        strategy=str(payload.get("strategy") or "Unknown strategy"),
        lines=lines,
        status=str(payload.get("status") or "Pending"),
        notes=str(payload.get("notes") or ""),
    )
