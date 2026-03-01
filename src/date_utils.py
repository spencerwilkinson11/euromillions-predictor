from __future__ import annotations

from datetime import date, datetime


def _parse_date_like(value: object) -> date | datetime | None:
    if value in (None, ""):
        return None

    if isinstance(value, (datetime, date)):
        return value

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass

        for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(text, pattern)
            except ValueError:
                continue

    return None


def format_uk_date(d: object) -> str:
    """Format date values as UK short labels like 'Tue 03 Mar 2026'."""
    parsed = _parse_date_like(d)
    if parsed is None:
        return str(d)
    return parsed.strftime("%a %d %b %Y")
