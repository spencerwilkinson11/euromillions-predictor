from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Optional
import xml.etree.ElementTree as ET

import requests


NATIONAL_LOTTERY_XML_URL = "https://www.national-lottery.co.uk/results/euromillions/draw-history/xml"
NATIONAL_LOTTERY_RESULTS_URL = "https://www.national-lottery.co.uk/results/euromillions"
PEDRO_DRAWS_URL = "https://euromillions.api.pedromealha.dev/v1/draws"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    "Referer": NATIONAL_LOTTERY_RESULTS_URL,
}


@dataclass
class JackpotInfo:
    ok: bool
    source: str
    jackpot_amount: Optional[str]
    next_draw_date: Optional[str]
    next_draw_day: Optional[str]
    raw: Optional[str]
    error: Optional[str]


def _format_gbp(amount: int) -> str:
    return f"£{amount:,}"


def _try_int(s: str) -> Optional[int]:
    cleaned = re.sub(r"[^\d]", "", s or "")
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except (TypeError, ValueError):
        return None


def _safe_get(url: str, headers: dict | None = None, timeout: int = 10) -> tuple[bool, str, Optional[str]]:
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return True, "", response.text
    except requests.RequestException as exc:
        return False, str(exc), None


def fetch_from_national_lottery_xml() -> JackpotInfo:
    ok, error, body = _safe_get(NATIONAL_LOTTERY_XML_URL, headers=_BROWSER_HEADERS, timeout=10)
    if not ok or body is None:
        return JackpotInfo(False, "national_lottery_xml", None, None, None, None, error or "XML request failed")

    try:
        root = ET.fromstring(body)

        jackpot_text = (
            root.findtext(".//next-estimated-jackpot")
            or root.findtext(".//jackpot-amount")
            or root.findtext(".//jackpotAmount")
        )
        amount = _try_int(jackpot_text or "")
        if amount is None:
            return JackpotInfo(
                False,
                "national_lottery_xml",
                None,
                (root.findtext(".//next-draw-date") or "").strip() or None,
                (root.findtext(".//next-draw-day") or "").strip().title() or None,
                jackpot_text,
                "No parseable jackpot in XML",
            )

        return JackpotInfo(
            True,
            "national_lottery_xml",
            _format_gbp(amount),
            (root.findtext(".//next-draw-date") or "").strip() or None,
            (root.findtext(".//next-draw-day") or "").strip().title() or None,
            jackpot_text,
            None,
        )
    except Exception as exc:
        return JackpotInfo(False, "national_lottery_xml", None, None, None, body[:500], str(exc))


def fetch_from_national_lottery_html() -> JackpotInfo:
    headers = dict(_BROWSER_HEADERS)
    headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    ok, error, body = _safe_get(NATIONAL_LOTTERY_RESULTS_URL, headers=headers, timeout=10)
    if not ok or body is None:
        return JackpotInfo(False, "national_lottery_html", None, None, None, None, error or "HTML request failed")

    try:
        patterns = [
            r"£\s*(\d{1,3}(?:,\d{3})+)",
            r"£\s*(\d+(?:\.\d+)?)\s*(million|m)\b",
            r"jackpot[^£\d]{0,40}£\s*(\d+(?:,\d{3})*)",
        ]

        amount: Optional[int] = None
        raw_match: Optional[str] = None

        for pattern in patterns:
            match = re.search(pattern, body, flags=re.IGNORECASE)
            if not match:
                continue

            raw_match = match.group(0)
            if len(match.groups()) >= 2 and (match.group(2) or "").lower() in {"million", "m"}:
                try:
                    amount = int(float(match.group(1).replace(",", "")) * 1_000_000)
                except ValueError:
                    amount = None
            else:
                amount = _try_int(match.group(1))

            if amount:
                break

        if not amount:
            return JackpotInfo(False, "national_lottery_html", None, None, None, None, "No parseable jackpot in HTML")

        return JackpotInfo(True, "national_lottery_html", _format_gbp(amount), None, None, raw_match, None)
    except Exception as exc:
        return JackpotInfo(False, "national_lottery_html", None, None, None, body[:500], str(exc))


def fetch_from_pedro_api() -> JackpotInfo:
    ok, error, body = _safe_get(PEDRO_DRAWS_URL, timeout=10)
    if not ok or body is None:
        return JackpotInfo(False, "pedro_api", None, None, None, None, error or "Draw API request failed")

    try:
        payload = json.loads(body)
        latest = payload[0] if isinstance(payload, list) and payload else payload if isinstance(payload, dict) else {}

        jackpot_raw = None
        for key in ("nextEstimatedJackpot", "next_estimated_jackpot", "estimatedJackpot", "jackpot"):
            value = latest.get(key) if isinstance(latest, dict) else None
            if value not in (None, ""):
                jackpot_raw = str(value)
                break

        amount = _try_int(jackpot_raw or "")
        if amount is None:
            return JackpotInfo(False, "pedro_api", None, None, None, jackpot_raw, "No parseable jackpot in fallback API")

        return JackpotInfo(True, "pedro_api", _format_gbp(amount), None, None, jackpot_raw, None)
    except Exception as exc:
        return JackpotInfo(False, "pedro_api", None, None, None, body[:500], str(exc))


def get_live_jackpot() -> JackpotInfo:
    errors: list[str] = []

    for fetcher in (fetch_from_national_lottery_xml, fetch_from_national_lottery_html, fetch_from_pedro_api):
        result = fetcher()
        if result.ok:
            return result
        errors.append(f"{result.source}: {result.error or 'unknown error'}")

    return JackpotInfo(
        ok=False,
        source="none",
        jackpot_amount=None,
        next_draw_date=None,
        next_draw_day=None,
        raw=None,
        error=" | ".join(errors) if errors else "No jackpot source available",
    )
