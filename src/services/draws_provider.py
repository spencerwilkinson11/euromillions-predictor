from __future__ import annotations

import requests

DRAWS_API_URL = "https://euromillions.api.pedromealha.dev/v1/draws"


def fetch_draws() -> list[dict]:
    """Fetch draw history from public provider."""
    response = requests.get(DRAWS_API_URL, timeout=10)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []
