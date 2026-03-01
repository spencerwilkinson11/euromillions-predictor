from __future__ import annotations

import json
from typing import Any

import streamlit as st

STORAGE_MODE = "local"  # future: "api"
LOCALSTORAGE_TICKETS_KEY = "wilkos_luckylogic_tickets_v1"


def serialize_tickets(tickets: list[dict]) -> str:
    try:
        return json.dumps(tickets)
    except (TypeError, ValueError):
        return "[]"


def deserialize_tickets(s: str) -> list[dict]:
    try:
        loaded = json.loads(s)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []

    if not isinstance(loaded, list):
        return []

    sanitized: list[dict] = []
    for ticket in loaded:
        if isinstance(ticket, dict):
            sanitized.append(ticket)

    return sanitized


def _warn_once(message: str) -> None:
    warnings = st.session_state.setdefault("ticket_storage_warnings", set())
    if message in warnings:
        return

    warnings.add(message)
    st.warning(message)


def _streamlit_js_eval(js_expression: str, *, key: str, want_output: bool = False) -> Any:
    try:
        from streamlit_js_eval import streamlit_js_eval

        return streamlit_js_eval(js_expressions=js_expression, key=key, want_output=want_output)
    except Exception:
        return None


def load_tickets_from_localstorage() -> list[dict]:
    if STORAGE_MODE != "local":
        return []

    response = _streamlit_js_eval(
        f'localStorage.getItem("{LOCALSTORAGE_TICKETS_KEY}")',
        key="tickets_localstorage_get",
        want_output=True,
    )

    if response in (None, "", "null"):
        return []

    if not isinstance(response, str):
        _warn_once("Ticket storage is unavailable in this browser session. Starting with empty tickets.")
        return []

    tickets = deserialize_tickets(response)
    if response.strip() and not tickets:
        _warn_once("Saved ticket data looks corrupted. Starting with empty tickets.")

    return tickets


def save_tickets_to_localstorage(tickets: list[dict]) -> None:
    if STORAGE_MODE != "local":
        return

    payload = serialize_tickets(tickets)
    escaped_payload = json.dumps(payload)
    result = _streamlit_js_eval(
        f'localStorage.setItem("{LOCALSTORAGE_TICKETS_KEY}", {escaped_payload})',
        key=f"tickets_localstorage_set_{abs(hash(payload))}",
        want_output=False,
    )

    if result is None:
        _warn_once("Could not save tickets to browser storage. They may reset after refresh.")
